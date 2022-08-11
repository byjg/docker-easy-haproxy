import os
from easymapping import HaproxyConfigGenerator

# path = os.path.dirname(os.path.realpath(__file__))
with open("/tmp/.docker_data", 'r') as content_file:
    lineList = content_file.readlines()

result = {
    "customerrors": True if os.getenv("HAPROXY_CUSTOMERRORS") == "true" else False
}

if os.getenv("HAPROXY_PASSWORD"):
    result["stats"] = {
        "username": os.getenv("HAPROXY_USERNAME") if os.getenv("HAPROXY_USERNAME") else "admin",
        "password": os.getenv("HAPROXY_PASSWORD"),
        "port": os.getenv("HAPROXY_STATS_PORT") if os.getenv("HAPROXY_STATS_PORT") else "1936",
    }

result["lookup_label"] = os.getenv("LOOKUP_LABEL") if os.getenv("LOOKUP_LABEL") else "easyhaproxy"

cfg = HaproxyConfigGenerator(result)
print(cfg.generate(lineList))

# print(jsonStr)


