import os
import json
from easymapping import HaproxyConfigGenerator

path = os.path.dirname(os.path.realpath(__file__))
with open(path + "/.docker_data", 'r') as content_file:
    lineList = content_file.readlines()

result = {
    "easymapping": []
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
            port = d["com.byjg.easyhaproxy.port." + definition] if "com.byjg.easyhaproxy.port." + definition in d else "80"
            data = {
                "port": port,
                "hosts": dict(),
                "redirect": dict(),
                # "ssl_cert": ""
            }

            data["hosts"][d["com.byjg.easyhaproxy.host." + definition] if "com.byjg.easyhaproxy.host." + definition in d else ""] = container + ":" + (d["com.byjg.easyhaproxy.localport." + definition] if "com.byjg.easyhaproxy.localport." + definition in d else "80")

            redirect = d["com.byjg.easyhaproxy.redirect." + definition] if "com.byjg.easyhaproxy.redirect." + definition in d else ""
            for r in redirect.split(","):
                r_parts = r.split("=>")
                data["redirect"][r_parts[0]] = r_parts[1]

            result["easymapping"].append(data)


cfg = HaproxyConfigGenerator(result)
print(cfg.generate())

print(result)
# print(jsonStr)


