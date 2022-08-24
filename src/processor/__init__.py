from easymapping import HaproxyConfigGenerator
from functions import Functions
import yaml
import sys
import os
import json
import docker
from kubernetes import client, config
from kubernetes.client.rest import ApiException

class ContainerEnv:
    @staticmethod
    def read():
        env_vars = {
            "customerrors": True if os.getenv("HAPROXY_CUSTOMERRORS") == "true" else False,
            "ssl_mode": os.getenv("EASYHAPROXY_SSL_MODE", "default")
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
    def __init__(self, filename = None):
        self.filename = filename
        self.refresh()

    @staticmethod
    def factory(mode):
        if mode == "static":
            return Static("/etc/haproxy/easyconfig.yml")
        elif mode == "docker":
            return Docker()
        elif mode == "swarm":
            return Swarm()
        elif mode == "kubernetes":
            return Kubernetes()
        else:
            Functions.log("FACTORY", "error", "Expected mode to be 'static', 'docker', 'swarm' or 'kubernetes'. I got '%s'" % (mode))
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
        # Abstract
        pass

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
        
    def parse(self):
        static_content = yaml.load(Functions.load(self.filename), Loader=yaml.FullLoader)
        self.cfg = HaproxyConfigGenerator(static_content)


class Docker(ProcessorInterface):
    def __init__(self, filename = None):
        self.client = docker.from_env()
        super().__init__()
    
    def inspect_network(self):
        self.parsed_object = {}
        for container in self.client.containers.list():
            self.parsed_object[container.name] = container.labels

    def parse(self):
        self.cfg = HaproxyConfigGenerator(ContainerEnv.read())


class Swarm(ProcessorInterface):
    def __init__(self, filename = None):
        self.client = docker.from_env()
        super().__init__()

    def inspect_network(self):
        self.parsed_object = {}
        for container in self.client.services.list():
            self.parsed_object[container.attrs["Spec"]["Name"]] = container.attrs["Spec"]["Labels"]

    def parse(self):
        self.cfg = HaproxyConfigGenerator(ContainerEnv.read())


class Kubernetes(ProcessorInterface):
    def __init__(self, filename = None):
        config.load_incluster_config()
        self.api_instance = client.CoreV1Api()
        self.v1 = client.NetworkingV1Api()
        super().__init__()
        
    def inspect_network(self):
        
        ret = self.v1.list_ingress_for_all_namespaces(watch=False)

        self.parsed_object = {}
        for i in ret.items:
            if i.metadata.annotations['kubernetes.io/ingress.class'] != "easyhaproxy-ingress":
                continue

            data = {}
            #ingress_name = i.metadata.name
            data["creation_timestamp"] = i.metadata.creation_timestamp.strftime("%x %X")
            data["resource_version"] = i.metadata.resource_version
            data["namespace"] = i.metadata.namespace
            for rule in i.spec.rules:
                rule_data = {}
                port_number = rule.http.paths[0].backend.service.port.number
                definition = rule.host.replace(".", "-")
                rule_data["easyhaproxy.%s_%s.host" % (definition, port_number)] = rule.host
                rule_data["easyhaproxy.%s_%s.port" % (definition, port_number)] = "80"
                rule_data["easyhaproxy.%s_%s.localport" % (definition, port_number)] = port_number
                service_name = rule.http.paths[0].backend.service.name
                try:
                    api_response = self.api_instance.read_namespaced_service(service_name, i.metadata.namespace)
                    cluster_ip = api_response.spec.cluster_ip
                except ApiException as e:
                    cluster_ip = None
                    # print("Exception when calling CoreV1Api->read_namespaced_service: %s\n" % e)
                
                if cluster_ip is not None:
                    if cluster_ip not in self.parsed_object.keys():
                        self.parsed_object[cluster_ip] = data
                    self.parsed_object[cluster_ip].update(rule_data)

    def parse(self):
        self.cfg = HaproxyConfigGenerator(ContainerEnv.read())



