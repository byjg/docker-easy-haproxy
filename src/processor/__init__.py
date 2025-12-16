import base64
import socket
from typing import Final

import docker
import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from easymapping import HaproxyConfigGenerator
from functions import Functions, Consts, ContainerEnv
from functions import loggerEasyHaproxy


class ProcessorInterface:
    STATIC: Final[str] = "static"
    DOCKER: Final[str] = "docker"
    SWARM: Final[str] = "swarm"
    KUBERNETES: Final[str] = "kubernetes"

    static_file = Consts.easyhaproxy_config

    def __init__(self, filename=None):
        self.certbot_hosts = None
        self.parsed_object = None
        self.cfg = None
        self.hosts = None
        self.cfg = None
        self.certbot_hosts = None
        self.hosts = None
        self.filename = filename
        self.label = ContainerEnv.read()['lookup_label']
        self.refresh()

    @staticmethod
    def factory(mode):
        if mode == ProcessorInterface.STATIC:
            return Static(ProcessorInterface.static_file)
        elif mode == ProcessorInterface.DOCKER:
            return Docker()
        elif mode == ProcessorInterface.SWARM:
            return Swarm()
        elif mode == ProcessorInterface.KUBERNETES:
            return Kubernetes()
        else:
            loggerEasyHaproxy.fatal("Expected mode to be 'static', 'docker', 'swarm' or 'kubernetes'. I got '%s'" % mode)
            return None

    def refresh(self):
        self.certbot_hosts = None
        self.parsed_object = None
        self.cfg = None
        self.hosts = None
        self.inspect_network()
        self.parse()

    def inspect_network(self):
        # Abstract
        pass

    def parse(self):
        self.cfg = HaproxyConfigGenerator(ContainerEnv.read())

    def get_certbot_hosts(self):
        return self.certbot_hosts

    def get_hosts(self):
        return self.hosts

    def get_parsed_object(self):
        return self.parsed_object

    def get_certs(self, key=None):
        if key is None:
            return self.cfg.certs
        else:
            return None if key not in self.cfg.certs else self.cfg.certs[key]

    def get_haproxy_conf(self):
        conf = self.cfg.generate(self.parsed_object)
        self.certbot_hosts = self.cfg.certbot_hosts
        self.hosts = self.cfg.serving_hosts
        return conf

    def save_config(self, filename):
        Functions.save(filename, self.get_haproxy_conf())

    def save_certs(self, path):
        for cert in self.get_certs():
            Functions.save("{0}/{1}".format(path, cert), self.get_certs(cert))


class Static(ProcessorInterface):
    def __init__(self, filename=None):
        self.parsed_object = None
        self.static_content = None
        self.static_content = None
        self.cfg = None
        super().__init__(filename)

    def inspect_network(self):
        self.parsed_object = {}
        self.static_content = None

    def get_parsed_object(self):
        return self.static_content["easymapping"] if "easymapping" in self.static_content else []

    def get_hosts(self):
        hosts = []
        for obj in self.get_parsed_object():
            if "hosts" not in obj:
                continue
            for host in obj["hosts"].keys():
                hosts.append("%s:%s" % (host, obj["port"]))
        return hosts

    def parse(self):
        self.static_content = yaml.load(Functions.load(self.filename), Loader=yaml.FullLoader)

        # Merge plugin config from YAML with env vars
        if "plugins" in self.static_content:
            # Get env var config
            container_env = ContainerEnv.read()

            # Merge YAML plugins config with env config
            # YAML config takes precedence over env vars
            if "plugins" not in self.static_content:
                self.static_content["plugins"] = container_env.get("plugins", {})
            else:
                # Merge configs - YAML overrides env vars
                yaml_plugins = self.static_content["plugins"]
                env_plugins = container_env.get("plugins", {})

                # Merge individual plugin configs
                for plugin_name, plugin_config in env_plugins.get("config", {}).items():
                    if plugin_name not in yaml_plugins:
                        yaml_plugins[plugin_name] = {}
                    # Env vars fill in missing keys, YAML takes precedence
                    for key, value in plugin_config.items():
                        if key not in yaml_plugins[plugin_name]:
                            yaml_plugins[plugin_name][key] = value

        self.cfg = HaproxyConfigGenerator(self.static_content)


class Docker(ProcessorInterface):
    def __init__(self, filename=None):
        self.parsed_object = None
        self.client = docker.from_env()
        super().__init__()

    def inspect_network(self):
        try:
            ha_proxy_network_name = next(
                iter(self.client.containers.get(socket.gethostname()).attrs["NetworkSettings"]["Networks"]))
        except:
            # HAProxy is not running in a container, get first container network
            if len(self.client.containers.list()) == 0:
                return
            ha_proxy_network_name = next(iter(
                self.client.containers.get(self.client.containers.list()[0].name).attrs["NetworkSettings"]["Networks"]))

        ha_proxy_network = self.client.networks.get(ha_proxy_network_name)

        self.parsed_object = {}
        for container in self.client.containers.list():
            # Issue 32 - Docker container cannot connect to containers in different network.
            if ha_proxy_network_name not in container.attrs["NetworkSettings"]["Networks"].keys():
                ha_proxy_network.connect(container.name)
                container = self.client.containers.get(container.name)  # refresh object

            ip_address = container.attrs["NetworkSettings"]["Networks"][ha_proxy_network_name]["IPAddress"]
            self.parsed_object[ip_address] = container.labels


class Swarm(ProcessorInterface):
    def __init__(self, filename=None):
        self.parsed_object = None
        self.client = docker.from_env()
        super().__init__()

    def inspect_network(self):
        ha_proxy_service_name = self.client.containers.get(socket.gethostname()).name.split('.')[0]
        ha_proxy_network_id = None
        swarm_ingress_id = None

        # Get the HAProxy network and the ingress network
        for endpoint in self.client.services.get(ha_proxy_service_name).attrs['Endpoint']["VirtualIPs"]:
            network_name = self.client.networks.get(endpoint["NetworkID"]).name
            if swarm_ingress_id is None and network_name == 'ingress':
                swarm_ingress_id = endpoint["NetworkID"]
            if ha_proxy_network_id is None and network_name != 'ingress':
                ha_proxy_network_id = endpoint["NetworkID"]
            if ha_proxy_network_id is not None and swarm_ingress_id is not None:
                break

        # Check if the service is attached to the HAProxy network
        self.parsed_object = {}
        for service in self.client.services.list():
            if not any(self.label in key for key in service.attrs["Spec"]["Labels"]):
                continue

            ip_address = None
            network_list = []
            for endpoint in service.attrs["Endpoint"]["VirtualIPs"]:
                if ha_proxy_network_id == endpoint["NetworkID"]:
                    ip_address = endpoint["Addr"].split("/")[0]
                    break
                elif swarm_ingress_id != endpoint["NetworkID"]:
                    network_list.append(endpoint["NetworkID"])

            # Attach the service to the HAProxy network
            if ip_address is None:
                network_list.append(ha_proxy_network_id)
                service.update(networks = network_list)
                continue # skip to the next service to give time to update the network

            self.parsed_object[ip_address] = service.attrs["Spec"]["Labels"]


class Kubernetes(ProcessorInterface):
    def __init__(self, filename=None):
        self.parsed_object = None
        config.load_incluster_config()
        config.verify_ssl = False
        self.api_instance = client.CoreV1Api()
        self.v1 = client.NetworkingV1Api()
        self.cert_cache = {}
        super().__init__()

    def _check_annotation(self, annotations, key, default=None):
        if key not in annotations:
            return default
        return annotations[key]

    def inspect_network(self):

        ret = self.v1.list_ingress_for_all_namespaces(watch=False)

        self.parsed_object = {}
        for ingress in ret.items:
            # Support both new spec.ingressClassName and deprecated annotation for backward compatibility
            ingress_class = None
            is_match = False

            # Check new spec.ingressClassName first (preferred)
            if hasattr(ingress.spec, 'ingress_class_name') and ingress.spec.ingress_class_name is not None:
                ingress_class = ingress.spec.ingress_class_name
                # Modern spec uses 'easyhaproxy'
                is_match = (ingress_class == "easyhaproxy")
            # Fall back to deprecated annotation
            elif ingress.metadata.annotations and 'kubernetes.io/ingress.class' in ingress.metadata.annotations:
                ingress_class = ingress.metadata.annotations['kubernetes.io/ingress.class']
                # Deprecated annotation uses 'easyhaproxy-ingress' for backward compatibility
                is_match = (ingress_class == "easyhaproxy-ingress")

            # Skip if no ingress class is defined or it doesn't match
            if not is_match:
                continue

            ssl_hosts = []

            certbot = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.certbot")
            redirect_ssl = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.redirect_ssl")
            redirect = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.redirect")
            mode = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.mode")
            listen_port = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.listen_port", 80)
            plugins = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.plugins")

            # Extract plugin-specific configurations
            plugin_annotations = {}
            for annotation_key, annotation_value in ingress.metadata.annotations.items():
                if annotation_key.startswith("easyhaproxy.plugin."):
                    plugin_annotations[annotation_key] = annotation_value

            data = {"creation_timestamp": ingress.metadata.creation_timestamp.strftime("%x %X"),
                    "resource_version": ingress.metadata.resource_version, "namespace": ingress.metadata.namespace}

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
                                base64.b64decode(secret.data["tls.crt"]).decode('ascii') + "\n" + base64.b64decode(
                                    secret.data["tls.key"]).decode('ascii')
                            )

                        ssl_hosts.extend(tls.hosts)
                    except Exception as e:
                        loggerEasyHaproxy.warn("Ingress %s - Get secret failed: '%s'" % (ingress_name, e))

            loggerEasyHaproxy.debug("Ingress %s - SSL Hosts found '%s'" % (ingress_name, ssl_hosts))

            for rule in ingress.spec.rules:
                rule_data = {}
                port_number = rule.http.paths[0].backend.service.port.number
                definition = "easyhaproxy.%s_%s" % (rule.host.replace(".", "-"), port_number)
                rule_data["%s.host" % definition] = rule.host
                rule_data["%s.port" % definition] = listen_port
                rule_data["%s.localport" % definition] = port_number
                if rule.host in ssl_hosts:
                    rule_data["%s.clone_to_ssl" % definition] = 'true'
                if redirect_ssl is not None:
                    rule_data["%s.redirect_ssl" % definition] = redirect_ssl
                if certbot is not None:
                    rule_data["%s.certbot" % definition] = certbot
                if redirect is not None:
                    rule_data["%s.redirect" % definition] = redirect
                if mode is not None:
                    rule_data["%s.mode" % definition] = mode
                rule_data["%s.balance" % definition] = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.balance", "roundrobin")

                # Add plugin configuration
                if plugins is not None:
                    rule_data["%s.plugins" % definition] = plugins

                # Add plugin-specific configurations
                for plugin_key, plugin_value in plugin_annotations.items():
                    # Convert easyhaproxy.plugin.X.Y to easyhaproxy.{definition}.plugin.X.Y
                    plugin_config_key = plugin_key.replace("easyhaproxy.plugin.", "%s.plugin." % definition)
                    rule_data[plugin_config_key] = plugin_value

                service_name = rule.http.paths[0].backend.service.name
                try:
                    api_response = self.api_instance.read_namespaced_service(service_name, ingress.metadata.namespace)
                    cluster_ip = api_response.spec.cluster_ip
                except ApiException as e:
                    cluster_ip = None
                    loggerEasyHaproxy.warn("Ingress %s - Service %s - Failed: '%s'" % (ingress_name, service_name, e))

                if cluster_ip is not None:
                    if cluster_ip not in self.parsed_object.keys():
                        self.parsed_object[cluster_ip] = data
                    self.parsed_object[cluster_ip].update(rule_data)
