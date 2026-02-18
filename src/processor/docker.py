import socket

import docker

from .interface import ProcessorInterface


class Docker(ProcessorInterface):
    def __init__(self, filename=None):
        self.parsed_object = None
        self.client = docker.from_env()
        super().__init__()

    def inspect_network(self):
        try:
            ha_proxy_network_name = next(
                iter(self.client.containers.get(socket.gethostname()).attrs["NetworkSettings"]["Networks"]))
        except Exception:
            # HAProxy is not running in a container, get first container network
            if len(self.client.containers.list()) == 0:
                return
            ha_proxy_network_name = next(iter(
                self.client.containers.get(self.client.containers.list()[0].name).attrs["NetworkSettings"]["Networks"]))

        ha_proxy_network = self.client.networks.get(ha_proxy_network_name)

        self.parsed_object = {}
        for container in self.client.containers.list():
            # Issue 32 - Docker container cannot connect to containers in different network.
            if ha_proxy_network_name not in container.attrs["NetworkSettings"]["Networks"].keys():
                ha_proxy_network.connect(container.name)
                container = self.client.containers.get(container.name)  # refresh object

            ip_address = container.attrs["NetworkSettings"]["Networks"][ha_proxy_network_name]["IPAddress"]
            self.parsed_object[ip_address] = container.labels