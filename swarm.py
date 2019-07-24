import os
import json
import time
import base64
import hashlib
from easymapping import HaproxyConfigGenerator

# path = os.path.dirname(os.path.realpath(__file__))
with open("/tmp/.docker_data", 'r') as content_file:
    lineList = content_file.readlines()

result = {
    "easymapping": [],
    "customerrors": True if os.getenv("HAPROXY_CUSTOMERRORS") == "true" else False
}
easymapping = dict()

if os.getenv("HAPROXY_PASSWORD"):
    result["stats"] = {
        "username": os.getenv("HAPROXY_USERNAME") if os.getenv("HAPROXY_USERNAME") else "admin",
        "password": os.getenv("HAPROXY_PASSWORD"),
        "port": os.getenv("HAPROXY_STATS_PORT") if os.getenv("HAPROXY_STATS_PORT") else "1936",
    }

for line in lineList:
    line = line.strip()
    i = line.find("=")
    container = line[:i]
    jsonStr = line[i+1:]
    d = json.loads(jsonStr)

    if "com.byjg.easyhaproxy.definitions" in d.keys():
        definitions = d["com.byjg.easyhaproxy.definitions"].split(",")

        for definition in definitions:
            if "com.byjg.easyhaproxy.host." + definition not in d:
                continue

            port = d["com.byjg.easyhaproxy.port." + definition] if "com.byjg.easyhaproxy.port." + definition in d else "80"
            hash = hashlib.md5(d["com.byjg.easyhaproxy.sslcert." + definition].encode('utf-8')).hexdigest() if "com.byjg.easyhaproxy.sslcert." + definition in d else ""

            key = port+hash

            if key not in easymapping:
                easymapping[key] = {
                    "port": port,
                    "hosts": dict(),
                    "redirect": dict(),
                    # "ssl_cert": ""
                }

            easymapping[key]["hosts"][d["com.byjg.easyhaproxy.host." + definition]] = container + ":" + (d["com.byjg.easyhaproxy.localport." + definition] if "com.byjg.easyhaproxy.localport." + definition in d else "80")

            if "com.byjg.easyhaproxy.sslcert." + definition in d:
                filename = '/etc/haproxy/certs/' + d["com.byjg.easyhaproxy.host." + definition] + "." + str(time.time()) + ".pem"
                easymapping[key]["ssl_cert"] = filename
                with open(filename, 'wb') as file:
                    file.write(base64.b64decode(d["com.byjg.easyhaproxy.sslcert." + definition]))

            if "com.byjg.easyhaproxy.redirect." + definition in d:
                redirect = d["com.byjg.easyhaproxy.redirect." + definition] if "com.byjg.easyhaproxy.redirect." + definition in d else ""
                for r in redirect.split(","):
                    r_parts = r.split("--")
                    easymapping[key]["redirect"][r_parts[0]] = r_parts[1]

        result["easymapping"] = easymapping.values()


cfg = HaproxyConfigGenerator(result)
print(cfg.generate())

# print(jsonStr)


