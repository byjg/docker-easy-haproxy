import base64
import json
import re

from jinja2 import Environment, FileSystemLoader


class DockerLabelHandler:
    def __init__(self, label):
        self.__data = None
        self.__label_base = label

    def get_lookup_label(self):
        return self.__label_base

    def format(self, key):
        if isinstance(key, str):
            return "{}.{}".format(self.__label_base, key)

        return "{}.{}".format(self.__label_base, ".".join(key))

    def get(self, label, default_value=""):
        if self.has_label(label):
            return self.__data[label]
        return default_value

    def get_bool(self, label, default_value=False):
        if self.has_label(label):
            return self.__data[label].lower() in ["true", "1", "yes"]
        return default_value

    def get_json(self, label, default_value={}):
        if self.has_label(label):
            return json.loads(self.__data[label])
        return default_value

    def get_pattern(self, label):
        label += "."
        matching_elements = [element for element in self.__data if element.startswith(label)]
        result_dict = {}

        for element in matching_elements:
            plugin_name = element[len(label):]
            result_dict[plugin_name] = self.get(element)

        return result_dict if result_dict else False

    def set_data(self, data):
        self.__data = data

    def has_label(self, label):
        if label in self.__data:
            return True
        return False


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

    def generate(self, container_metadata={}):
        self.mapping.setdefault("easymapping", [])

        if container_metadata != {}:
            self.mapping["easymapping"] = self.parse(container_metadata)

        file_loader = FileSystemLoader('templates')
        env = Environment(loader=file_loader)
        env.trim_blocks = True
        env.lstrip_blocks = True
        env.rstrip_blocks = True
        template = env.get_template('haproxy.cfg.j2')
        return template.render(data=self.mapping)

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
                    self.label.format([definition, "mode"]),
                    "http"
                )

                # TODO: we can ignore "host" in TCP, but it would break the template
                host_label = self.label.format([definition, "host"])
                if not self.label.has_label(host_label):
                    continue

                port = self.label.get(
                    self.label.format([definition, "port"]),
                    "80"
                )

                certbot = self.label.get_bool(
                    self.label.format([definition, "certbot"]),
                    False
                ) and self.mapping["certbot"]["email"] != ""
                clone_to_ssl = self.label.get_bool(
                    self.label.format([definition, "clone_to_ssl"])
                )

                if port not in easymapping:
                    easymapping[port] = {
                        "mode": mode,
                        "ssl-check": "",
                        "port": port,
                        "hosts": dict(),
                        "redirect": dict(),
                    }

                # TODO: this could use `EXPOSE` from `Dockerfile`?
                ct_port = self.label.get(
                    self.label.format([definition, "localport"]),
                    "80"
                )

                easymapping[port]["ssl-check"] = self.label.get(
                    self.label.format([definition, "ssl-check"]),
                    ""
                )

                plugins = self.label.get_pattern(self.label.format([definition, "plugin"]))

                for hostname in sorted(d[host_label].split(",")):
                    hostname = hostname.strip()
                    self.serving_hosts.append("%s:%s" % (hostname, port))
                    easymapping[port]["hosts"].setdefault(hostname, {})
                    easymapping[port]["hosts"][hostname].setdefault("containers", [])
                    easymapping[port]["hosts"][hostname].setdefault("certbot", False)
                    easymapping[port]["hosts"][hostname]["containers"] += ["{}:{}".format(container, ct_port)]
                    easymapping[port]["hosts"][hostname]["certbot"] = certbot
                    easymapping[port]["hosts"][hostname]["redirect_ssl"] = self.label.get_bool(
                        self.label.format([definition, "redirect_ssl"])
                    )
                    easymapping[port]["hosts"][hostname]["balance"] = self.label.get(
                        self.label.format([definition, "balance"]),
                        "roundrobin"
                    )

                    easymapping[port]["redirect"] = self.label.get_json(
                        self.label.format([definition, "redirect"])
                    )

                    if (plugins):
                        easymapping[port]["hosts"][hostname]["plugins"] = plugins

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
                    ssl_label = self.label.format([definition, "sslcert"])
                    if self.label.has_label(ssl_label):
                        filename = "{}.pem".format(d[host_label])
                        easymapping[port]["ssl"] = True if not clone_to_ssl else False
                        self.certs[filename] = base64.b64decode(d[ssl_label]).decode('ascii')

                    if self.label.get_bool(self.label.format([definition, "ssl"])):
                        easymapping[port]["ssl"] = True if not clone_to_ssl else False

        return easymapping.values()
