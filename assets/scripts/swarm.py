import os
from easymapping import HaproxyConfigGenerator

# path = os.path.dirname(os.path.realpath(__file__))
with open("/tmp/.docker_data", 'r') as content_file:
    lineList = content_file.readlines()

result = {
    "customerrors": True if os.getenv("HAPROXY_CUSTOMERRORS") == "true" else False
}

if os.getenv("HAPROXY_PASSWORD"):
    password = os.getenv("HAPROXY_PASSWORD")
    if password.startswith("/run/secrets/"): # support docker secrets
        with open(password) as passfh:
            password = passfh.read().strip()
    result["stats"] = {
        "username": os.getenv("HAPROXY_USERNAME") if os.getenv("HAPROXY_USERNAME") else "admin",
        "password": password,
        "port": os.getenv("HAPROXY_STATS_PORT") if os.getenv("HAPROXY_STATS_PORT") else "1936",
    }

cfg = HaproxyConfigGenerator(result)
print(cfg.generate(lineList))

# print(jsonStr)


