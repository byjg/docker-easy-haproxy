import socket

import docker

from functions import logger_easyhaproxy

from .interface import ProcessorInterface


class Swarm(ProcessorInterface):
    def __init__(self, filename=None):
        self.parsed_object = None
        self.client = docker.from_env()
        super().__init__()

    def inspect_network(self):
        ha_proxy_service_name = self.client.containers.get(socket.gethostname()).name.split('.')[0]
        ha_proxy_network_id = None
        swarm_ingress_id = None

        # Get the HAProxy network and the ingress network
        for endpoint in self.client.services.get(ha_proxy_service_name).attrs['Endpoint']["VirtualIPs"]:
            network_name = self.client.networks.get(endpoint["NetworkID"]).name
            if swarm_ingress_id is None and network_name == 'ingress':
                swarm_ingress_id = endpoint["NetworkID"]
            if ha_proxy_network_id is None and network_name != 'ingress':
                ha_proxy_network_id = endpoint["NetworkID"]
            if ha_proxy_network_id is not None and swarm_ingress_id is not None:
                break

        # Check if the service is attached to the HAProxy network
        self.parsed_object = {}
        for service in self.client.services.list():
            labels = service.attrs["Spec"].get("Labels") or {}
            if not any(key.startswith(f"{self.label}.") for key in labels):
                continue

            try:
                # dnsrr has no virtual IP, so there is no address to send the requests to
                endpoint_mode = (service.attrs["Spec"].get("EndpointSpec") or {}).get("Mode", "vip")
                if endpoint_mode != "vip":
                    logger_easyhaproxy.warn(f"Service {service.name} - Endpoint mode '{endpoint_mode}' is not supported; skipped")
                    continue

                ip_address = None
                network_list = []
                for endpoint in service.attrs["Endpoint"].get("VirtualIPs", []):
                    if ha_proxy_network_id == endpoint["NetworkID"]:
                        ip_address = endpoint["Addr"].split("/")[0]
                        break
                    elif swarm_ingress_id != endpoint["NetworkID"]:
                        network_list.append(endpoint["NetworkID"])

                # Attach the service to the HAProxy network
                if ip_address is None:
                    network_list.append(ha_proxy_network_id)
                    service.update(networks=network_list)
                    continue  # skip to the next service to give time to update the network

                self.parsed_object[ip_address] = labels
            except Exception as e:
                # One service the code does not expect must not stop the others
                logger_easyhaproxy.warn(f"Service {service.name} - Skipped: {e}")
