from unittest.mock import MagicMock, Mock

import docker

from processor import ProcessorInterface

LABELS = {"easyhaproxy.http.host": "web.test", "easyhaproxy.http.localport": "8080"}


def _mock_service(name, labels=None, virtual_ips=None, endpoint_mode=None):
    service = Mock()
    service.name = name
    spec = {"Labels": labels}
    if endpoint_mode:
        spec["EndpointSpec"] = {"Mode": endpoint_mode}
    endpoint = {"VirtualIPs": virtual_ips} if virtual_ips is not None else {"Spec": {}}
    service.attrs = {"Spec": spec, "Endpoint": endpoint}
    return service


def _scan_swarm(monkeypatch, services):
    client = MagicMock()
    client.containers.get.return_value.name = "easyhaproxy.1.abc"
    client.services.get.return_value.attrs = {"Endpoint": {"VirtualIPs": [{"NetworkID": "net1", "Addr": "10.0.1.5/24"}]}}
    client.networks.get.return_value.name = "easyhaproxy_net"
    client.services.list.return_value = services
    monkeypatch.setattr(docker, "from_env", lambda: client)
    return ProcessorInterface.factory(ProcessorInterface.SWARM).get_parsed_object()


def test_processor_swarm(monkeypatch):
    web = _mock_service("web", LABELS, [{"NetworkID": "net1", "Addr": "10.0.1.7/24"}])

    assert _scan_swarm(monkeypatch, [web, _mock_service("unlabeled", {})]) == {"10.0.1.7": LABELS}


def test_processor_swarm_dnsrr_service_is_skipped(monkeypatch):
    """dnsrr has no virtual IP: the scan failed with KeyError 'VirtualIPs', or kept updating the service"""
    web = _mock_service("web", LABELS, [{"NetworkID": "net1", "Addr": "10.0.1.7/24"}])
    dnsrr = _mock_service("dnsrr", LABELS, endpoint_mode="dnsrr")

    assert _scan_swarm(monkeypatch, [dnsrr, web]) == {"10.0.1.7": LABELS}
    dnsrr.update.assert_not_called()


def test_processor_swarm_service_without_network_is_attached(monkeypatch):
    """A service with no network has no VirtualIPs yet: it is attached to the HAProxy network"""
    lonely = _mock_service("lonely", LABELS)

    assert _scan_swarm(monkeypatch, [lonely]) == {}
    lonely.update.assert_called_once_with(networks=["net1"])


def test_processor_swarm_unexpected_error_skips_only_that_service(monkeypatch):
    web = _mock_service("web", LABELS, [{"NetworkID": "net1", "Addr": "10.0.1.7/24"}])
    broken = _mock_service("broken", LABELS)
    broken.attrs = {"Spec": {"Labels": LABELS}}  # no Endpoint

    assert _scan_swarm(monkeypatch, [broken, web]) == {"10.0.1.7": LABELS}


def test_processor_swarm_custom_label_prefix(monkeypatch):
    monkeypatch.setenv("EASYHAPROXY_LABEL_PREFIX", "my")
    labels = {"my.http.host": "web.test", "my.http.localport": "8080"}
    web = _mock_service("web", labels, [{"NetworkID": "net1", "Addr": "10.0.1.7/24"}])
    app = _mock_service("app", {"com.mycompany.version": "1"})  # no network

    assert _scan_swarm(monkeypatch, [app, web]) == {"10.0.1.7": labels}
    app.update.assert_not_called()
