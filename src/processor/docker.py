import socket

import docker

from functions import logger_easyhaproxy

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
            # Only containers with EasyHAProxy labels are routed, so only they join the HAProxy network
            if not any(key.startswith(f"{self.label}.") for key in container.labels):
                continue

            try:
                # host, none and container:<name> cannot join another network
                network_mode = container.attrs["HostConfig"]["NetworkMode"]
                if network_mode in ("host", "none") or network_mode.startswith("container:"):
                    logger_easyhaproxy.warn(f"Container {container.name} - Network mode '{network_mode}' is not supported; skipped")
                    continue

                # Issue 32 - Docker container cannot connect to containers in different network.
                if ha_proxy_network_name not in container.attrs["NetworkSettings"]["Networks"].keys():
                    ha_proxy_network.connect(container.name)
                    container = self.client.containers.get(container.name)  # refresh object

                ip_address = container.attrs["NetworkSettings"]["Networks"][ha_proxy_network_name]["IPAddress"]
                self.parsed_object[ip_address] = container.labels
            except Exception as e:
                # One container the code does not expect must not stop the others
                logger_easyhaproxy.warn(f"Container {container.name} - Skipped: {e}")
