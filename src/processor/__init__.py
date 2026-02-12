import base64
import socket
from typing import Final

import docker
import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from easymapping import HaproxyConfigGenerator
from functions import Consts, ContainerEnv, Functions, logger_easyhaproxy


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
            logger_easyhaproxy.fatal(f"Expected mode to be 'static', 'docker', 'swarm' or 'kubernetes'. I got '{mode}'")
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
            Functions.save(f"{path}/{cert}", self.get_certs(cert))


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
                hosts.append(f"{host}:{obj['port']}")
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
        except Exception:
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
    def __init__(self, filename=None, api_instance=None, v1=None):
        self.parsed_object = None

        # Only load config if API clients are not provided (allows dependency injection for testing)
        if api_instance is None or v1 is None:
            config.load_incluster_config()
            config.verify_ssl = False

        # Use injected clients or create new ones (dependency injection pattern)
        self.api_instance = api_instance or client.CoreV1Api()
        self.v1 = v1 or client.NetworkingV1Api()
        self.cert_cache = {}
        self.deployment_mode_cache = None
        self.ingress_addresses_cache = None
        self.addresses_cache_time = 0
        super().__init__()

    def _detect_deployment_mode(self):
        """
        Detect the deployment mode (daemonset, nodeport, clusterip).
        Returns: tuple (mode: str, service: V1Service or None)
        """
        import os

        # Return cached if available
        if self.deployment_mode_cache:
            return self.deployment_mode_cache

        env_config = ContainerEnv.read()

        # Check for manual override
        if env_config['deployment_mode'] != 'auto':
            logger_easyhaproxy.info(f"Using manual deployment mode: {env_config['deployment_mode']}")
            service = self._get_easyhaproxy_service() if env_config['deployment_mode'] in ['nodeport', 'clusterip'] else None
            self.deployment_mode_cache = (env_config['deployment_mode'], service)
            return self.deployment_mode_cache

        try:
            # Get current pod name from hostname
            pod_name = socket.gethostname()
            namespace = os.getenv('POD_NAMESPACE', 'easyhaproxy')

            # Read current pod
            pod = self.api_instance.read_namespaced_pod(pod_name, namespace)

            # Check owner references to determine if DaemonSet or Deployment
            if pod.metadata.owner_references:
                owner_kind = pod.metadata.owner_references[0].kind

                if owner_kind == 'DaemonSet':
                    logger_easyhaproxy.info("Detected deployment mode: daemonset")
                    self.deployment_mode_cache = ('daemonset', None)
                    return self.deployment_mode_cache
                elif owner_kind in ['ReplicaSet', 'Deployment']:
                    # Check if Service exists
                    service = self._get_easyhaproxy_service()
                    if service:
                        if service.spec.type == 'NodePort':
                            logger_easyhaproxy.info("Detected deployment mode: nodeport")
                            self.deployment_mode_cache = ('nodeport', service)
                            return self.deployment_mode_cache
                        else:
                            logger_easyhaproxy.info("Detected deployment mode: clusterip")
                            self.deployment_mode_cache = ('clusterip', service)
                            return self.deployment_mode_cache
        except Exception as e:
            logger_easyhaproxy.warn(f"Failed to detect deployment mode: {e}, defaulting to daemonset")

        self.deployment_mode_cache = ('daemonset', None)
        return self.deployment_mode_cache

    def _get_easyhaproxy_service(self):
        """Get the EasyHAProxy service if it exists."""
        import os

        try:
            namespace = os.getenv('POD_NAMESPACE', 'easyhaproxy')
            # Try common service names
            service_names = ['easyhaproxy', 'ingress-easyhaproxy']

            for service_name in service_names:
                try:
                    service = self.api_instance.read_namespaced_service(service_name, namespace)
                    return service
                except Exception:
                    continue
            return None
        except Exception as e:
            logger_easyhaproxy.warn(f"Failed to get EasyHAProxy service: {e}")
            return None

    def _get_ingress_addresses(self, mode, service):
        """
        Get IP addresses or hostnames to report in ingress status.

        Args:
            mode: Deployment mode (daemonset, nodeport, clusterip)
            service: V1Service object (for nodeport/clusterip modes)

        Returns:
            List of dicts: [{"ip": "..."}, {"hostname": "..."}]
        """
        import os
        import time

        env_config = ContainerEnv.read()
        cache_ttl = env_config.get('ingress_status_update_interval', 30)

        # Return cached if still valid
        if self.ingress_addresses_cache and (time.time() - self.addresses_cache_time) < cache_ttl:
            return self.ingress_addresses_cache

        addresses = []

        try:
            if mode == 'daemonset':
                # Get nodes where DaemonSet pods are running
                namespace = os.getenv('POD_NAMESPACE', 'easyhaproxy')
                label_selector = "app.kubernetes.io/name=easyhaproxy"

                pods = self.api_instance.list_namespaced_pod(namespace, label_selector=label_selector)
                node_names = set(pod.spec.node_name for pod in pods.items if pod.spec.node_name)

                # Get external IPs from these nodes
                for node_name in node_names:
                    node = self.api_instance.read_node(node_name)
                    for addr in node.status.addresses:
                        if addr.type == 'ExternalIP':
                            addresses.append({"ip": addr.address})
                            break
                    else:
                        # Fallback to InternalIP if no ExternalIP
                        for addr in node.status.addresses:
                            if addr.type == 'InternalIP':
                                addresses.append({"ip": addr.address})
                                break

            elif mode == 'nodeport':
                # Get all node IPs (traffic can reach any node via NodePort)
                nodes = self.api_instance.list_node()
                for node in nodes.items:
                    for addr in node.status.addresses:
                        if addr.type == 'ExternalIP':
                            addresses.append({"ip": addr.address})
                            break
                    else:
                        # Fallback to InternalIP
                        for addr in node.status.addresses:
                            if addr.type == 'InternalIP':
                                addresses.append({"ip": addr.address})
                                break

            elif mode == 'clusterip':
                # Check if LoadBalancer status is available
                if service and service.status and service.status.load_balancer:
                    lb_ingress = service.status.load_balancer.ingress or []
                    for ing in lb_ingress:
                        if ing.ip:
                            addresses.append({"ip": ing.ip})
                        if ing.hostname:
                            addresses.append({"hostname": ing.hostname})

                # If no LoadBalancer, check for external hostname override
                if not addresses and env_config['external_hostname']:
                    addresses.append({"hostname": env_config['external_hostname']})

                # Fallback to ClusterIP
                if not addresses and service:
                    addresses.append({"ip": service.spec.cluster_ip})

        except Exception as e:
            logger_easyhaproxy.warn(f"Failed to get ingress addresses: {e}")

        # Cache the result
        self.ingress_addresses_cache = addresses
        self.addresses_cache_time = time.time()

        return addresses

    def _update_ingress_status(self, ingress, addresses):
        """
        Update the status of an ingress resource.

        Args:
            ingress: V1Ingress object
            addresses: List of address dicts [{"ip": "..."}, {"hostname": "..."}]
        """
        if not addresses:
            return

        try:
            # Create status patch
            status_body = {
                "status": {
                    "loadBalancer": {
                        "ingress": addresses
                    }
                }
            }

            # Update status using patch (not replace)
            self.v1.patch_namespaced_ingress_status(
                name=ingress.metadata.name,
                namespace=ingress.metadata.namespace,
                body=status_body,
                field_manager="easyhaproxy"
            )

            logger_easyhaproxy.debug(
                f"Updated ingress {ingress.metadata.namespace}/{ingress.metadata.name} "
                f"status with {len(addresses)} address(es)"
            )

        except Exception as e:
            logger_easyhaproxy.warn(
                f"Failed to update status for ingress "
                f"{ingress.metadata.namespace}/{ingress.metadata.name}: {e}"
            )

    def _check_annotation(self, annotations, key, default=None):
        if key not in annotations:
            return default
        return annotations[key]

    def inspect_network(self):

        ret = self.v1.list_ingress_for_all_namespaces(watch=False)

        # Detect deployment mode once per cycle for ingress status updates
        env_config = ContainerEnv.read()
        if env_config['update_ingress_status']:
            deployment_mode, service = self._detect_deployment_mode()
            ingress_addresses = self._get_ingress_addresses(deployment_mode, service)
        else:
            ingress_addresses = []

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

            # Get ingress name for logging
            ingress_name = f"{ingress.metadata.namespace}/{ingress.metadata.name}"

            # Generic k8s_secret annotation processing
            # Pattern: easyhaproxy.plugin.X.k8s_secret.KEY: "secret_name" or "secret_name/key_name"
            # Result: easyhaproxy.plugin.X.KEY: "<base64-encoded-content>"
            k8s_secret_annotations = {}
            for annotation_key, secret_value in list(plugin_annotations.items()):
                # Check if this annotation contains k8s_secret pattern
                if ".k8s_secret." in annotation_key:
                    try:
                        # Parse the annotation key
                        # Example: "easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey" -> "pubkey"
                        parts = annotation_key.split(".k8s_secret.")
                        if len(parts) != 2:
                            logger_easyhaproxy.warn(
                                f"Ingress {ingress_name} - Malformed k8s_secret annotation: {annotation_key}"
                            )
                            continue

                        prefix = parts[0]  # "easyhaproxy.plugin.jwt_validator"
                        config_key = parts[1]  # "pubkey"
                        target_annotation = f"{prefix}.{config_key}"  # "easyhaproxy.plugin.jwt_validator.pubkey"

                        # Parse secret_value: can be "secret_name" or "secret_name/key_name"
                        if "/" in secret_value:
                            secret_name, explicit_key_name = secret_value.split("/", 1)
                            use_explicit_key = True
                        else:
                            secret_name = secret_value
                            explicit_key_name = None
                            use_explicit_key = False

                        # Read the secret
                        secret = self.api_instance.read_namespaced_secret(
                            secret_name,
                            ingress.metadata.namespace
                        )

                        # Try to find the key in the secret data
                        secret_data = None
                        tried_keys = []

                        if use_explicit_key:
                            # User specified exact key name - only try that one
                            tried_keys = [explicit_key_name]
                            if explicit_key_name in secret.data:
                                secret_data = secret.data[explicit_key_name]
                                logger_easyhaproxy.debug(
                                    f"Ingress {ingress_name} - Found explicit secret key '{explicit_key_name}' "
                                    f"in secret '{secret_name}'"
                                )
                        else:
                            # No explicit key - try config_key and common variations
                            tried_keys = [config_key]
                            if config_key in secret.data:
                                secret_data = secret.data[config_key]
                            else:
                                # Try common variations for the requested key
                                variations = []
                                if config_key == "pubkey":
                                    variations = ["public-key", "jwt.pub", "tls.crt"]
                                elif config_key == "password":
                                    variations = ["pass", "pwd"]
                                elif config_key == "api_key":
                                    variations = ["apikey", "api-key", "key"]

                                for variation in variations:
                                    tried_keys.append(variation)
                                    if variation in secret.data:
                                        secret_data = secret.data[variation]
                                        logger_easyhaproxy.debug(
                                            f"Ingress {ingress_name} - Found secret key '{variation}' "
                                            f"for requested key '{config_key}'"
                                        )
                                        break

                        if secret_data:
                            # Decode from base64 (Kubernetes secrets are base64-encoded)
                            # Then re-encode to base64 for plugin (plugin expects base64-encoded)
                            decoded = base64.b64decode(secret_data).decode('ascii')
                            reencoded = base64.b64encode(decoded.encode('ascii')).decode('ascii')

                            # Store the processed annotation
                            k8s_secret_annotations[target_annotation] = reencoded

                            logger_easyhaproxy.info(
                                f"Ingress {ingress_name} - Loaded '{config_key}' from secret "
                                f"'{secret_name}' for annotation '{target_annotation}'"
                            )
                        else:
                            logger_easyhaproxy.warn(
                                f"Ingress {ingress_name} - Secret '{secret_name}' found but "
                                f"no matching key (tried: {', '.join(tried_keys)})"
                            )

                    except Exception as e:
                        logger_easyhaproxy.warn(
                            f"Ingress {ingress_name} - Failed to process k8s_secret annotation "
                            f"'{annotation_key}' with value '{secret_value}': {e}"
                        )

            # Merge k8s_secret annotations into plugin_annotations
            # k8s_secret annotations will NOT override existing explicit annotations (lower priority)
            for key, value in k8s_secret_annotations.items():
                if key not in plugin_annotations:
                    plugin_annotations[key] = value
                else:
                    logger_easyhaproxy.debug(
                        f"Ingress {ingress_name} - Skipping k8s_secret annotation '{key}' "
                        f"because explicit annotation already exists"
                    )

            data = {"creation_timestamp": ingress.metadata.creation_timestamp.strftime("%x %X"),
                    "resource_version": ingress.metadata.resource_version, "namespace": ingress.metadata.namespace}

            if ingress.spec.tls is not None:
                for tls in ingress.spec.tls:
                    try:
                        secret = self.api_instance.read_namespaced_secret(tls.secret_name, ingress.metadata.namespace)
                        if "tls.crt" not in secret.data or "tls.key" not in secret.data:
                            continue

                        if tls.secret_name not in self.cert_cache or self.cert_cache[tls.secret_name] != secret.data:
                            self.cert_cache[tls.secret_name] = secret.data
                            Functions.save(
                                f"{Consts.certs_haproxy}/{tls.secret_name}.pem",
                                base64.b64decode(secret.data["tls.crt"]).decode('ascii') + "\n" + base64.b64decode(
                                    secret.data["tls.key"]).decode('ascii')
                            )

                        ssl_hosts.extend(tls.hosts)
                    except Exception as e:
                        logger_easyhaproxy.warn(f"Ingress {ingress_name} - Get secret failed: '{e}'")

            logger_easyhaproxy.debug(f"Ingress {ingress_name} - SSL Hosts found '{ssl_hosts}'")

            for rule in ingress.spec.rules:
                rule_data = {}
                port_number = rule.http.paths[0].backend.service.port.number
                definition = f"easyhaproxy.{rule.host.replace('.', '-')}_{port_number}"
                rule_data[f"{definition}.host"] = rule.host
                rule_data[f"{definition}.port"] = listen_port
                rule_data[f"{definition}.localport"] = port_number
                if rule.host in ssl_hosts:
                    rule_data[f"{definition}.clone_to_ssl"] = 'true'
                if redirect_ssl is not None:
                    rule_data[f"{definition}.redirect_ssl"] = redirect_ssl
                if certbot is not None:
                    rule_data[f"{definition}.certbot"] = certbot
                if redirect is not None:
                    rule_data[f"{definition}.redirect"] = redirect
                if mode is not None:
                    rule_data[f"{definition}.mode"] = mode
                rule_data[f"{definition}.balance"] = self._check_annotation(ingress.metadata.annotations, "easyhaproxy.balance", "roundrobin")

                # Add plugin configuration
                if plugins is not None:
                    rule_data[f"{definition}.plugins"] = plugins

                # Add plugin-specific configurations
                for plugin_key, plugin_value in plugin_annotations.items():
                    # Convert easyhaproxy.plugin.X.Y to easyhaproxy.{definition}.plugin.X.Y
                    plugin_config_key = plugin_key.replace("easyhaproxy.plugin.", f"{definition}.plugin.")
                    rule_data[plugin_config_key] = plugin_value

                service_name = rule.http.paths[0].backend.service.name
                try:
                    api_response = self.api_instance.read_namespaced_service(service_name, ingress.metadata.namespace)
                    cluster_ip = api_response.spec.cluster_ip
                except ApiException as e:
                    cluster_ip = None
                    logger_easyhaproxy.warn(f"Ingress {ingress_name} - Service {service_name} - Failed: '{e}'")

                if cluster_ip is not None:
                    if cluster_ip not in self.parsed_object.keys():
                        self.parsed_object[cluster_ip] = data
                    self.parsed_object[cluster_ip].update(rule_data)

            # Update ingress status if enabled
            if env_config['update_ingress_status'] and ingress_addresses:
                self._update_ingress_status(ingress, ingress_addresses)
