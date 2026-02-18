import json

import yaml

from easymapping import HaproxyConfigGenerator
from functions import ContainerEnv, Functions

from .interface import ProcessorInterface


class Static(ProcessorInterface):
    def __init__(self, filename=None):
        self.parsed_object = None
        self.static_content = None
        self.static_content = None
        self.cfg = None
        super().__init__(filename)

    def inspect_network(self):
        """Load YAML and convert containers to Docker-style container metadata"""
        # Load YAML
        self.static_content = yaml.load(Functions.load(self.filename), Loader=yaml.FullLoader)

        # Convert containers to label format
        self.parsed_object = self._convert_yaml_to_labels()

    def _convert_yaml_to_labels(self):
        """
        Convert static YAML containers to Docker label format.
        Returns: {IP: {labels}} structure that parse() can process
        """
        container_metadata = {}

        # Get global plugin configuration
        global_plugins = self.static_content.get("plugins", {})
        global_enabled = global_plugins.get("enabled", [])
        global_plugin_config = global_plugins.get("config", {})

        for host_port, config in self.static_content.get("containers", {}).items():
            # Parse hostname:port from key
            if ":" in host_port:
                hostname, port = host_port.rsplit(":", 1)
            else:
                hostname = host_port
                port = "80"

            # Create definition: hostname_port (e.g., host1_com_br_80)
            definition = hostname.replace(".", "_") + f"_{port}"

            # Handle redirect-only entries (no backend)
            if "redirect" in config and "ip" not in config:
                # Create metadata with redirect but mark as redirect-only to skip backend creation
                fake_ip = f"redirect-{hostname}-{port}"
                if fake_ip not in container_metadata:
                    container_metadata[fake_ip] = {}

                container_metadata[fake_ip].update({
                    f"easyhaproxy.{definition}.host": hostname,
                    f"easyhaproxy.{definition}.port": port,
                    f"easyhaproxy.{definition}.redirect": json.dumps({hostname: config["redirect"]}),
                    f"easyhaproxy.{definition}.redirect_only": "true",  # Marker to skip backend
                })
                continue

            # Get IPs/containers
            ip_list = config.get("ip", [hostname])

            # Process each container/IP
            for container_spec in ip_list:
                # Parse container:localport
                if ":" in container_spec:
                    container_addr, localport = container_spec.rsplit(":", 1)
                else:
                    container_addr = container_spec
                    localport = "80"

                # Use container address as IP (could be IP, DNS, or container name)
                ip = container_addr

                # Build labels dict
                labels = {
                    f"easyhaproxy.{definition}.host": hostname,
                    f"easyhaproxy.{definition}.port": port,
                    f"easyhaproxy.{definition}.localport": localport,
                }

                # Add optional settings
                for key in ["mode", "certbot", "redirect_ssl", "ssl", "balance", "proto", "ssl-check", "clone_to_ssl"]:
                    if key in config:
                        value = config[key]
                        # Convert boolean to string
                        if isinstance(value, bool):
                            value = "true" if value else "false"
                        labels[f"easyhaproxy.{definition}.{key}"] = str(value)

                # Handle plugins
                host_plugins = config.get("plugins", global_enabled)
                if host_plugins:
                    # Convert list to comma-separated string if needed
                    if isinstance(host_plugins, list):
                        plugins_str = ",".join(host_plugins)
                    else:
                        plugins_str = host_plugins
                    labels[f"easyhaproxy.{definition}.plugins"] = plugins_str

                    # Process plugin configurations
                    host_plugin_config = config.get("plugin", {})

                    # Parse plugins list
                    plugins_list = host_plugins if isinstance(host_plugins, list) else [p.strip() for p in host_plugins.split(",")]

                    for plugin_name in plugins_list:
                        # Merge global and host-specific config
                        merged_config = {}
                        if plugin_name in global_plugin_config:
                            merged_config.update(global_plugin_config[plugin_name])
                        if plugin_name in host_plugin_config:
                            merged_config.update(host_plugin_config[plugin_name])

                        # Convert plugin config to labels
                        for config_key, config_value in merged_config.items():
                            label_key = f"easyhaproxy.{definition}.plugin.{plugin_name}.{config_key}"

                            # Convert list values to comma-separated strings
                            if isinstance(config_value, list):
                                label_value = ",".join(str(v) for v in config_value)
                            else:
                                label_value = str(config_value)

                            labels[label_key] = label_value

                # Initialize container entry if it doesn't exist
                if ip not in container_metadata:
                    container_metadata[ip] = {}

                # Merge labels instead of overwriting
                container_metadata[ip].update(labels)

        return container_metadata

    def parse(self):
        """Create HaproxyConfigGenerator with YAML config merged into env vars"""
        self.cfg = HaproxyConfigGenerator(ContainerEnv.read(self.static_content))