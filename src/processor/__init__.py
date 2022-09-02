from easymapping import HaproxyConfigGenerator
from functions import Functions, Consts
import yaml
import sys
import os
import json
import base64
import docker
from kubernetes import client, config
from kubernetes.client.rest import ApiException

class ContainerEnv:
    @staticmethod
    def read():
        env_vars = {
            "customerrors": True if os.getenv("HAPROXY_CUSTOMERRORS") == "true" else False,
            "ssl_mode": os.getenv("EASYHAPROXY_SSL_MODE").lower() if os.getenv("EASYHAPROXY_SSL_MODE") else 'default'
        }

        if os.getenv("HAPROXY_PASSWORD"):
            env_vars["stats"] = {
                "username": os.getenv("HAPROXY_USERNAME") if os.getenv("HAPROXY_USERNAME") else "admin",
                "password": os.getenv("HAPROXY_PASSWORD"),
                "port": os.getenv("HAPROXY_STATS_PORT") if os.getenv("HAPROXY_STATS_PORT") else "1936",
            }

        env_vars["lookup_label"] = os.getenv("EASYHAPROXY_LABEL_PREFIX") if os.getenv("EASYHAPROXY_LABEL_PREFIX") else "easyhaproxy"
        if (os.getenv("EASYHAPROXY_LETSENCRYPT_EMAIL")):
            env_vars["letsencrypt"] = {
                "email": os.getenv("EASYHAPROXY_LETSENCRYPT_EMAIL")
            }
        
        return env_vars


class ProcessorInterface:
    static_file = Consts.easyhaproxy_config

    def __init__(self, filename = None):
        self.filename = filename
        self.refresh()

    @staticmethod
    def factory(mode):
        if mode == "static":
            return Static(ProcessorInterface.static_file)
        elif mode == "docker":
            return Docker()
        elif mode == "swarm":
            return Swarm()
        elif mode == "kubernetes":
            return Kubernetes()
        else:
            Functions.log("EASYHAPROXY", Functions.FATAL, "Expected mode to be 'static', 'docker', 'swarm' or 'kubernetes'. I got '%s'" % (mode))
            return None

    def refresh(self):
        self.letsencrypt_hosts = None
        self.parsed_object = None
        self.cfg = None
        self.hosts = None
        self.inspect_network()
        self.parse()

    def inspect_network(self):
        #Abstract
        pass

    def parse(self):
        self.cfg = HaproxyConfigGenerator(ContainerEnv.read())

    def get_letsencrypt_hosts(self):
        return self.letsencrypt_hosts

    def get_hosts(self):
        return self.hosts

    def get_parsed_object(self):
        return self.parsed_object

    def get_certs(self, key = None):
        if key is None:
            return self.cfg.certs
        else:
            return None if key not in self.cfg.certs else self.cfg.certs[key]

    def get_haproxy_conf(self):
        conf = self.cfg.generate(self.parsed_object)
        self.letsencrypt_hosts = self.cfg.letsencrypt_hosts
        self.hosts = self.cfg.serving_hosts
        return conf

    def save_config(self, filename):
        Functions.save(filename, self.get_haproxy_conf())

    def save_certs(self, path):
        for cert in self.get_certs():
            Functions.save("{0}/{1}".format(path, cert), self.get_certs(cert))


class Static(ProcessorInterface):
    def inspect_network(self):
        self.parsed_object = {}
        self.static_content = None
    
    def get_parsed_object(self):
        return self.static_content["easymapping"] if "easymapping" in self.static_content else []

    def get_hosts(self):
        hosts = []
        for object in self.get_parsed_object():
            if "hosts" not in object:
                continue
            for host in object["hosts"].keys():
                hosts.append("%s:%s" % (host, object["port"]))
        return hosts

    def parse(self):
        self.static_content = yaml.load(Functions.load(self.filename), Loader=yaml.FullLoader)
        self.cfg = HaproxyConfigGenerator(self.static_content)


class Docker(ProcessorInterface):
    def __init__(self, filename = None):
        self.client = docker.from_env()
        super().__init__()
    
    def inspect_network(self):
        self.parsed_object = {}
        for container in self.client.containers.list():
            self.parsed_object[container.name] = container.labels


class Swarm(ProcessorInterface):
    def __init__(self, filename = None):
        self.client = docker.from_env()
        super().__init__()

    def inspect_network(self):
        self.parsed_object = {}
        for container in self.client.services.list():
            self.parsed_object[container.attrs["Spec"]["Name"]] = container.attrs["Spec"]["Labels"]


class Kubernetes(ProcessorInterface):
    def __init__(self, filename = None):
        config.load_incluster_config()
        config.verify_ssl = False
        self.api_instance = client.CoreV1Api()
        self.v1 = client.NetworkingV1Api()
        self.cert_cache = {}
        super().__init__()

    def _check_annotation(self, annotations, key):
        if key not in annotations:
            return None
        return annotations[key]

    def inspect_network(self):
        
        ret = self.v1.list_ingress_for_all_namespaces(watch=False)

        self.parsed_object = {}
        for ingress in ret.items:
            if ingress.metadata.annotations['kubernetes.io/ingress.class'] != "easyhaproxy-ingress":
                continue

            ssl_hosts = []

            letsencrypt = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.letsencrypt")
            redirect_ssl = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.redirect_ssl")
            redirect = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.redirect")
            mode = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.mode")
            listen_port = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.listen_port")
            if listen_port is None:
                listen_port = 80

            data = {}
            data["creation_timestamp"] = ingress.metadata.creation_timestamp.strftime("%x %X")
            data["resource_version"] = ingress.metadata.resource_version
            data["namespace"] = ingress.metadata.namespace

            ingress_name = ingress.metadata.namespace

            if ingress.spec.tls is not None:
                for tls in ingress.spec.tls:
                    try:
                        secret = self.api_instance.read_namespaced_secret(tls.secret_name, ingress.metadata.namespace)
                        if "tls.crt" not in secret.data or "tls.key" not in secret.data:
                            continue

                        if tls.secret_name not in self.cert_cache or self.cert_cache[tls.secret_name] != secret.data:
                            self.cert_cache[tls.secret_name] = secret.data
                            Functions.save(
                                "{0}/{1}.pem".format(Consts.certs_haproxy, tls.secret_name), 
                                base64.b64decode(secret.data["tls.crt"]).decode('ascii') + "\n" + base64.b64decode(secret.data["tls.key"]).decode('ascii')
                            )

                        ssl_hosts.extend(tls.hosts)
                    except Exception as e:
                        Functions.log("EASYHAPROXY", Functions.WARN, "Ingress %s - Get secret failed: '%s'" % (ingress_name, e))

            Functions.log("EASYHAPROXY", Functions.TRACE, "Ingress %s - SSL Hosts found '%s'" % (ingress_name, ssl_hosts))

            for rule in ingress.spec.rules:
                rule_data = {}
                port_number = rule.http.paths[0].backend.service.port.number
                definition = "easyhaproxy.%s_%s" % (rule.host.replace(".", "-"), port_number)
                rule_data["%s.host" % (definition)] = rule.host
                rule_data["%s.port" % (definition)] = listen_port
                rule_data["%s.localport" % (definition)] = port_number
                if rule.host in ssl_hosts:
                    rule_data["%s.clone_to_ssl" % (definition)] = 'true'
                if redirect_ssl is not None:
                    rule_data["%s.redirect_ssl" % (definition)] = redirect_ssl
                if letsencrypt is not None:
                    rule_data["%s.letsencrypt" % (definition)] = letsencrypt
                if redirect is not None:
                    rule_data["%s.redirect" % (definition)] = redirect
                if mode is not None:
                    rule_data["%s.mode" % (definition)] = mode

                service_name = rule.http.paths[0].backend.service.name
                try:
                    api_response = self.api_instance.read_namespaced_service(service_name, ingress.metadata.namespace)
                    cluster_ip = api_response.spec.cluster_ip
                except ApiException as e:
                    cluster_ip = None
                    Functions.log("EASYHAPROXY", Functions.WARN, "Ingress %s - Service %s - Failed: '%s'" % (ingress_name, service_name, e))
                
                if cluster_ip is not None:
                    if cluster_ip not in self.parsed_object.keys():
                        self.parsed_object[cluster_ip] = data
                    self.parsed_object[cluster_ip].update(rule_data)




