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


    def set_data(self, data):
        self.__data = data


    def has_label(self, label):
        if label in self.__data:
            return True
        return False


class HaproxyConfigGenerator:
    def __init__(self, mapping, ssl_cert_folder="/etc/haproxy/certs"):
        self.mapping = mapping
        self.label = DockerLabelHandler(mapping['lookup_label'] if 'lookup_label' in mapping else "easyhaproxy")
        self.ssl_cert_folder = ssl_cert_folder
        self.ssl_cert_increment = 0
        os.makedirs(self.ssl_cert_folder, exist_ok=True)


    def generate(self, line_list = []):
        # static?
        if len(line_list) > 0:
            self.mapping["easymapping"] = self.parse(line_list)
        else:
            for d in self.mapping["easymapping"]:
                for name, hosts in d.get('hosts', {}).items():
                    if type(hosts) != list:
                        d['hosts'][name] = [hosts]
        # still 'None' -> default to [] for jinja2
        if self.mapping["easymapping"] is None:
            self.mapping["easymapping"] = []

        file_loader = FileSystemLoader('templates')
        env = Environment(loader=file_loader)
        env.trim_blocks = True
        env.lstrip_blocks = True
        env.rstrip_blocks = True
        template = env.get_template('haproxy.cfg.j2')
        return template.render(data=self.mapping)


    def parse(self, line_list):
        easymapping = dict()

        for line in line_list:
            line = line.strip()
            i = line.find("=")
            container = line[:i]
            json_str = line[i+1:]
            d = json.loads(json_str)

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

                hash = ""
                if self.label.create([definition, "sslcert"]) in d:
                    hash = hashlib.md5(
                        d[self.label.create([definition, "sslcert"])].encode('utf-8')
                    ).hexdigest()

                key = port if not hash else port + "_" + hash

                if key not in easymapping:
                    easymapping[key] = {
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

                easymapping[key]["health-check"] = self.label.get(
                    self.label.create([definition, "health-check"]),
                    ""
                )

                easymapping[key]["hosts"].setdefault(d[host_label], [])
                easymapping[key]["hosts"][d[host_label]] += ["{}:{}".format(container, ct_port)]

                # handle SSL
                ssl_label = self.label.create([definition, "sslcert"])
                if self.label.has_label(ssl_label):
                    self.ssl_cert_increment += 1
                    filename = "{}/{}.{}.pem".format(
                        self.ssl_cert_folder, d[host_label], str(self.ssl_cert_increment)
                    )
                    easymapping[key]["ssl_cert"] = filename
                    with open(filename, 'wb') as file:
                        file.write(
                            base64.b64decode(d[ssl_label])
                        )

                # handle redirects
                redirect = self.label.get(
                    self.label.create([definition, "redirect"])
                )
                if len(redirect) > 0:
                    for r in redirect.split(","):
                        r_parts = r.split("--")
                        easymapping[key]["redirect"][r_parts[0]] = r_parts[1]

        return easymapping.values()
