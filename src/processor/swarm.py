import socket

import docker

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
            if not any(self.label in key for key in service.attrs["Spec"]["Labels"]):
                continue

            ip_address = None
            network_list = []
            for endpoint in service.attrs["Endpoint"]["VirtualIPs"]:
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

            self.parsed_object[ip_address] = service.attrs["Spec"]["Labels"]