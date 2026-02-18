from typing import Final

from easymapping import HaproxyConfigGenerator
from functions import Consts, ContainerEnv, Functions, logger_easyhaproxy


class ProcessorInterface:
    STATIC: Final[str] = "static"
    DOCKER: Final[str] = "docker"
    SWARM: Final[str] = "swarm"
    KUBERNETES: Final[str] = "kubernetes"

    static_file = Consts.easyhaproxy_config

    def __init__(self, filename=None):
        self.certbot_hosts = None
        self.parsed_object = None
        self.cfg = None
        self.hosts = None
        self.cfg = None
        self.certbot_hosts = None
        self.hosts = None
        self.filename = filename
        self.label = ContainerEnv.read()['lookup_label']
        self.refresh()

    @staticmethod
    def factory(mode):
        from .static import Static
        from .docker import Docker
        from .swarm import Swarm
        from .kubernetes import Kubernetes

        if mode == ProcessorInterface.STATIC:
            return Static(ProcessorInterface.static_file)
        elif mode == ProcessorInterface.DOCKER:
            return Docker()
        elif mode == ProcessorInterface.SWARM:
            return Swarm()
        elif mode == ProcessorInterface.KUBERNETES:
            return Kubernetes()
        else:
            logger_easyhaproxy.fatal(f"Expected mode to be 'static', 'docker', 'swarm' or 'kubernetes'. I got '{mode}'")
            return None

    def refresh(self):
        self.certbot_hosts = None
        self.parsed_object = None
        self.cfg = None
        self.hosts = None
        self.inspect_network()
        self.parse()

    def inspect_network(self):
        # Abstract
        pass

    def parse(self):
        self.cfg = HaproxyConfigGenerator(ContainerEnv.read())

    def get_certbot_hosts(self):
        return self.certbot_hosts

    def get_hosts(self):
        return self.hosts

    def get_parsed_object(self):
        return self.parsed_object

    def get_certs(self, key=None):
        if key is None:
            return self.cfg.certs
        else:
            return None if key not in self.cfg.certs else self.cfg.certs[key]

    def get_haproxy_conf(self):
        conf = self.cfg.generate(self.parsed_object)
        self.certbot_hosts = self.cfg.certbot_hosts
        self.hosts = self.cfg.serving_hosts
        return conf

    def save_config(self, filename):
        Functions.save(filename, self.get_haproxy_conf())

    def save_certs(self, path):
        for cert in self.get_certs():
            Functions.save(f"{path}/{cert}", self.get_certs(cert))