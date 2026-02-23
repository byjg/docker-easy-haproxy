import base64
import os
import re

from jinja2 import Environment, FileSystemLoader

from functions import Functions, logger_easyhaproxy, Consts

from .label_handler import DockerLabelHandler


class HaproxyConfigGenerator:
    def __init__(self, mapping):
        self.mapping = mapping
        self.mapping.setdefault("ssl_mode", 'default')
        self.mapping.setdefault("certbot", {"email": "", "server": False, "eab_kid": False, "eab_hmac_key": False})
        self.mapping["ssl_mode"] = self.mapping["ssl_mode"].lower()
        self.label = DockerLabelHandler(mapping['lookup_label'] if 'lookup_label' in mapping else "easyhaproxy")
        self.certbot_hosts = []
        self.serving_hosts = []
        self.certs = {}
        self.defaults_plugin_configs = []

        # Initialize plugin system
        try:
            from plugins import PluginManager
            self.plugin_manager = PluginManager(
                abort_on_error=self.mapping.get("plugins", {}).get("abort_on_error", False)
            )
            self.plugin_manager.load_plugins()
            self.plugin_manager.configure_plugins(self.mapping.get("plugins", {}))
            self.plugin_manager.initialize_plugins()
            self.global_plugin_configs = []
        except Exception as e:
            # If plugin system fails to initialize, log but continue
            logger_easyhaproxy.warning(f"Failed to initialize plugin system: {e}")
            self.plugin_manager = None
            self.global_plugin_configs = []

    def generate(self, container_metadata={}):
        self.mapping.setdefault("easymapping", [])

        if container_metadata != {}:
            self.mapping["easymapping"] = self.parse(container_metadata)

        # Execute global plugins
        if self.plugin_manager:
            try:
                from plugins import PluginContext
                global_context = PluginContext(
                    parsed_object=container_metadata,
                    easymapping=self.mapping.get("easymapping", []),
                    container_env=self.mapping,
                    domain=None,
                    port=None,
                    host_config=None
                )

                # Get enabled plugins from config
                enabled_list = self.mapping.get("plugins", {}).get("enabled", [])
                # If enabled list contains only empty string, treat as no plugins enabled
                if enabled_list and len(enabled_list) > 0 and enabled_list[0] == "":
                    enabled_list = []

                global_results = self.plugin_manager.execute_global_plugins(global_context, enabled_list)

                # Extract all plugin configs in a single loop
                for result in global_results:
                    # HAProxy config snippets
                    if result.haproxy_config:
                        self.global_plugin_configs.append(result.haproxy_config)

                    # Global-level configs (e.g., fcgi-app definitions)
                    for config in result.global_configs:
                        if config and config not in self.global_plugin_configs:
                            self.global_plugin_configs.append(config)

                    # Defaults-level configs (e.g., log-format)
                    for config in result.defaults_configs:
                        if config and config not in self.defaults_plugin_configs:
                            self.defaults_plugin_configs.append(config)
            except Exception as e:
                logger_easyhaproxy.warning(f"Failed to execute global plugins: {e}")

        templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'templates')
        file_loader = FileSystemLoader(templates_dir)
        env = Environment(loader=file_loader)
        env.trim_blocks = True
        env.lstrip_blocks = True
        env.rstrip_blocks = True
        template = env.get_template('haproxy.cfg.j2')
        return template.render(
            data=self.mapping,
            global_plugin_configs=self.global_plugin_configs,
            defaults_plugin_configs=self.defaults_plugin_configs,
            dashboard_server_port=Consts.DASHBOARD_SERVER_PORT
        )

    def parse(self, container_metadata):
        easymapping = dict()

        for container in container_metadata:
            d = container_metadata[container]

            # Extract the definitions dynamically
            definitions = {}
            r = re.compile(self.label.get_lookup_label() + r"\.(.*)\..*")
            for key in d.keys():
                if r.match(key):
                    definitions[r.search(key).group(1)] = 1

            if len(definitions.keys()) == 0:
                continue

            self.label.set_data(d)

            # Parse each definition found.
            for definition in sorted(definitions.keys()):
                mode = self.label.get(
                    self.label.create([definition, "mode"]),
                    "http"
                )

                # TODO: we can ignore "host" in TCP, but it would break the template
                host_label = self.label.create([definition, "host"])
                if not self.label.has_label(host_label):
                    continue

                port = self.label.get(
                    self.label.create([definition, "port"]),
                    "80"
                )

                certbot = self.label.get_bool(
                    self.label.create([definition, "certbot"]),
                    False
                ) and self.mapping["certbot"]["email"] != ""
                clone_to_ssl = self.label.get_bool(
                    self.label.create([definition, "clone_to_ssl"])
                )

                # Check if this is a redirect-only entry (no backend)
                redirect_only = self.label.get_bool(
                    self.label.create([definition, "redirect_only"]),
                    False
                )

                if port not in easymapping:
                    easymapping[port] = {
                        "mode": mode,
                        "ssl-check": "",
                        "port": port,
                        "hosts": dict(),
                        "redirect": dict(),
                    }

                if redirect_only:
                    easymapping[port]["redirect"].update(self.label.get_json(
                        self.label.create([definition, "redirect"])
                    ))
                    continue

                # TODO: this could use `EXPOSE` from `Dockerfile`?
                ct_port = self.label.get(
                    self.label.create([definition, "localport"]),
                    "80"
                )

                easymapping[port]["ssl-check"] = self.label.get(
                    self.label.create([definition, "ssl-check"]),
                    ""
                )

                # Protocol for backend server communication (e.g., fcgi, h2)
                proto = self.label.get(
                    self.label.create([definition, "proto"]),
                    ""
                )

                # Unix socket path (alternative to host:port)
                socket_path = self.label.get(
                    self.label.create([definition, "socket"]),
                    ""
                )

                for hostname in sorted(d[host_label].split(",")):
                    hostname = hostname.strip()
                    self.serving_hosts.append(f"{hostname}:{port}")
                    easymapping[port]["hosts"].setdefault(hostname, {})
                    easymapping[port]["hosts"][hostname].setdefault("containers", [])
                    easymapping[port]["hosts"][hostname].setdefault("certbot", False)
                    easymapping[port]["hosts"][hostname].setdefault("proto", proto)

                    # Determine server address: Unix socket or TCP host:port
                    if socket_path:
                        server_address = socket_path
                    else:
                        server_address = f"{container}:{ct_port}"

                    easymapping[port]["hosts"][hostname]["containers"] += [server_address]
                    easymapping[port]["hosts"][hostname]["certbot"] = certbot
                    easymapping[port]["hosts"][hostname]["redirect_ssl"] = self.label.get_bool(
                        self.label.create([definition, "redirect_ssl"])
                    )
                    easymapping[port]["hosts"][hostname]["balance"] = self.label.get(
                        self.label.create([definition, "balance"]),
                        "roundrobin"
                    )

                    easymapping[port]["redirect"] = self.label.get_json(
                        self.label.create([definition, "redirect"])
                    )

                    # Execute domain plugins for this host
                    if self.plugin_manager:
                        try:
                            from plugins import PluginContext

                            domain_context = PluginContext(
                                parsed_object=container_metadata,
                                easymapping=easymapping,
                                container_env=self.mapping,
                                domain=hostname,
                                port=port,
                                host_config=easymapping[port]["hosts"][hostname]
                            )

                            # Check if plugins are enabled for this domain (from labels)
                            enabled_plugins = []
                            if self.label.has_label(self.label.create([definition, "plugins"])):
                                enabled_plugins = self.label.get(
                                    self.label.create([definition, "plugins"]),
                                    ""
                                ).split(",")
                                enabled_plugins = [p.strip() for p in enabled_plugins if p.strip()]

                            # Extract plugin configurations from labels
                            # Format: easyhaproxy.http.plugin.PLUGIN_NAME.CONFIG_KEY
                            plugin_configs = {}
                            for plugin_name in enabled_plugins:
                                plugin_configs[plugin_name] = {}
                                # Look for all labels matching easyhaproxy.{definition}.plugin.{plugin_name}.*
                                plugin_label_prefix = self.label.create([definition, "plugin", plugin_name])
                                for label_key in d.keys():
                                    if label_key.startswith(plugin_label_prefix + "."):
                                        # Extract config key (everything after plugin_label_prefix + ".")
                                        config_key = label_key[len(plugin_label_prefix) + 1:]
                                        plugin_configs[plugin_name][config_key] = d[label_key]

                            # Configure plugins with label-specific configs before execution
                            for plugin_name, config in plugin_configs.items():
                                if plugin_name in self.plugin_manager.plugins:
                                    self.plugin_manager.plugins[plugin_name].configure(config)

                            domain_results = self.plugin_manager.execute_domain_plugins(
                                domain_context,
                                enabled_list=enabled_plugins
                            )

                            # Extract all plugin configs in a single loop
                            plugin_configs_for_host = []
                            for result in domain_results:
                                # HAProxy config snippets for this domain
                                if result.haproxy_config:
                                    plugin_configs_for_host.append(result.haproxy_config)

                                # Global-level configs (e.g., fcgi-app definitions)
                                for config in result.global_configs:
                                    if config and config not in self.global_plugin_configs:
                                        self.global_plugin_configs.append(config)

                                # Defaults-level configs (e.g., log-format)
                                for config in result.defaults_configs:
                                    if config and config not in self.defaults_plugin_configs:
                                        self.defaults_plugin_configs.append(config)

                            # Store domain plugin configs for this host
                            easymapping[port]["hosts"][hostname]["plugin_configs"] = plugin_configs_for_host
                        except Exception as e:
                            logger_easyhaproxy.warning(f"Failed to execute domain plugins for {hostname}: {e}")
                            easymapping[port]["hosts"][hostname]["plugin_configs"] = []
                    else:
                        easymapping[port]["hosts"][hostname]["plugin_configs"] = []

                    if certbot or clone_to_ssl:
                        if "443" not in easymapping:
                            easymapping["443"] = {
                                "mode": "http",
                                "ssl-check": "ssl",
                                "port": "443",
                                "hosts": dict(),
                                "redirect": dict(),
                            }
                        easymapping["443"]["hosts"][hostname] = dict(easymapping[port]["hosts"][hostname])
                        easymapping["443"]["hosts"][hostname]["certbot"] = False
                        easymapping["443"]["hosts"][hostname]["redirect_ssl"] = False
                        easymapping["443"]["ssl"] = True
                        self.certbot_hosts.append(
                            hostname) if certbot and hostname not in self.certbot_hosts else self.certbot_hosts

                    # handle SSL
                    ssl_label = self.label.create([definition, "sslcert"])
                    if self.label.has_label(ssl_label):
                        filename = f"{d[host_label]}.pem"
                        easymapping[port]["ssl"] = True if not clone_to_ssl else False
                        self.certs[filename] = base64.b64decode(d[ssl_label]).decode('ascii')

                    if self.label.get_bool(self.label.create([definition, "ssl"])):
                        easymapping[port]["ssl"] = True if not clone_to_ssl else False

        return easymapping.values()