import base64
import hashlib
from jinja2 import Environment, FileSystemLoader
import json
import os
import re

class DockerLabelHandler:
    def __init__(self, label):
        self.__label_base = label

    def get_lookup_label(self):
        return self.__label_base

    def create(self, key):
        if isinstance(key, str):
            return "{}.{}".format(self.__label_base, key)

        return "{}.{}".format(self.__label_base, ".".join(key))


    def get(self, label, default_value = ""):
        if self.has_label(label):
            return self.__data[label]
        return default_value


    def get_bool(self, label, default_value = False):
        if self.has_label(label):
            return self.__data[label].lower() in ["true", "1", "yes"]
        return default_value

    def get_json(self, label, default_value = {}):
        if self.has_label(label):
            return json.loads(self.__data[label])
        return default_value

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
        self.mapping.setdefault("letsencrypt", {"email": ""})
        self.mapping["ssl_mode"] = self.mapping["ssl_mode"].lower()
        self.label = DockerLabelHandler(mapping['lookup_label'] if 'lookup_label' in mapping else "easyhaproxy")
        self.letsencrypt_hosts = []
        self.serving_hosts = []
        self.certs = {}
 
    def generate(self, container_metadata = {}):
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
            for definition in definitions.keys():
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

                letsencrypt = self.label.get_bool(
                    self.label.create([definition, "letsencrypt"]),
                    False
                ) and self.mapping["letsencrypt"]["email"] != "" 

                if port not in easymapping:
                    easymapping[port] = {
                        "mode": mode,
                        "health-check": "",
                        "port": port,
                        "hosts": dict(),
                        "redirect": dict(),
                    }

                # TODO: this could use `EXPOSE` from `Dockerfile`?
                ct_port = self.label.get(
                    self.label.create([definition, "localport"]),
                    "80"
                )

                easymapping[port]["health-check"] = self.label.get(
                    self.label.create([definition, "health-check"]),
                    ""
                )

                for hostname in d[host_label].split(","):
                    hostname = hostname.strip()
                    self.serving_hosts.append("%s:%s" % (hostname, port))
                    easymapping[port]["hosts"].setdefault(hostname, {})
                    easymapping[port]["hosts"][hostname].setdefault("containers", [])
                    easymapping[port]["hosts"][hostname].setdefault("letsencrypt", False)
                    easymapping[port]["hosts"][hostname]["containers"] += ["{}:{}".format(container, ct_port)]
                    easymapping[port]["hosts"][hostname]["letsencrypt"] = letsencrypt
                    easymapping[port]["hosts"][hostname]["redirect_ssl"] = self.label.get_bool(
                        self.label.create([definition, "redirect_ssl"])
                    )

                    easymapping[port]["redirect"] = self.label.get_json(
                        self.label.create([definition, "redirect"])
                    )

                    if letsencrypt:
                        if "443" not in easymapping:
                            easymapping["443"] = {
                                "mode": "http",
                                "health-check": "ssl",
                                "port": "443",
                                "hosts": dict(),
                                "redirect": dict(),
                            }
                        easymapping["443"]["hosts"][hostname] = dict(easymapping[port]["hosts"][hostname])
                        easymapping["443"]["hosts"][hostname]["letsencrypt"] = False
                        easymapping["443"]["hosts"][hostname]["redirect_ssl"] = False
                        easymapping["443"]["ssl"] = True
                        self.letsencrypt_hosts.append(hostname) if hostname not in self.letsencrypt_hosts else self.letsencrypt_hosts
                        

                    # handle SSL
                    ssl_label = self.label.create([definition, "sslcert"])
                    if self.label.has_label(ssl_label):
                        filename = "{}.pem".format(d[host_label])
                        easymapping[port]["ssl"] = True
                        self.certs[filename] = base64.b64decode(d[ssl_label]).decode('ascii')

                    if self.label.get_bool(self.label.create([definition, "ssl"])):
                        easymapping[port]["ssl"] = True

        return easymapping.values()
