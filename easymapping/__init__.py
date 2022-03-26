import base64
import hashlib
from jinja2 import Environment, FileSystemLoader
import json
import os

class DockerLabelHandler:
    def __init__(self, label):
        self.__label_base = label


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
        self.label = DockerLabelHandler("easyhaproxy")
        self.ssl_cert_folder = ssl_cert_folder
        self.ssl_cert_increment = 0
        os.makedirs(self.ssl_cert_folder, exist_ok=True)


    def generate(self, lineList = []):
        # static?
        if len(lineList) > 0:
            self.mapping["easymapping"] = self.__parse(lineList)

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


    def __parse(self, lineList):
        easymapping = dict()

        for line in lineList:
            line = line.strip()
            i = line.find("=")
            container = line[:i]
            jsonStr = line[i+1:]
            d = json.loads(jsonStr)

            if self.label.create("definitions") not in d.keys():
                continue

            self.label.set_data(d)

            definitions = d[self.label.create("definitions")].split(",")
            for definition in definitions:
                mode = self.label.get(
                    self.label.create(["mode", definition]),
                    "http"
                )

                # TODO: we can ignore "host" in TCP, but it would break the template
                host_label = self.label.create(["host", definition])
                if not self.label.has_label(host_label):
                    continue

                port = self.label.get(
                    self.label.create(["port", definition]),
                    "80"
                )

                hash = ""
                if self.label.create(["sslcert", definition]) in d:
                    hash = hashlib.md5(
                        d[self.label.create(["sslcert", definition])].encode('utf-8')
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
                    self.label.create(["localport", definition]),
                    "80"
                )

                easymapping[key]["health-check"] = self.label.get(
                    self.label.create(["health-check", definition]),
                    ""
                )

                easymapping[key]["hosts"][d[host_label]] = "{}:{}".format(container, ct_port)

                # handle SSL
                ssl_label = self.label.create(["sslcert", definition])
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
                    self.label.create(["redirect", definition])
                )
                if len(redirect) > 0:
                    for r in redirect.split(","):
                        r_parts = r.split("--")
                        easymapping[key]["redirect"][r_parts[0]] = r_parts[1]

        return easymapping.values()
