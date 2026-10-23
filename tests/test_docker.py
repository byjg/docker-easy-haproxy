import os
import time
from unittest.mock import MagicMock, Mock

import docker
import pytest

from functions import Functions
from processor import ProcessorInterface


def _get_hydrated_object(parsed_objects, lookup_key):
    hydrated_object = {}
    for key in parsed_objects:
        for keys in parsed_objects[key]:
            if lookup_key in keys:
                hydrated_object[keys] = parsed_objects[key][keys]
    return hydrated_object


def _get_ip_host(parsed_objects, lookup_key):
    for key in parsed_objects:
        for keys in parsed_objects[key]:
            if lookup_key in keys:
                return key


def test_processor_docker():
    try:
        client = docker.from_env()
    except docker.errors.DockerException:
        pytest.skip("There is no docker environment")

    if len(client.containers.list()) > 0:
        pytest.skip("I cannot run this test with other containers running.")

    container = client.containers.run("byjg/static-httpserver",
                                      name="test_processor_docker",
                                      detach=True,
                                      auto_remove=True,
                                      remove=True,
                                      labels={
                                          "easyhaproxy.http.port": "80",
                                          "easyhaproxy.http.localport": "8080",
                                          "easyhaproxy.http.host": "host1.local",

                                          "easyhaproxy.http2.port": "90",
                                          "easyhaproxy.http2.localport": "9000",
                                          "easyhaproxy.http2.host": "host2.local",
                                          "easyhaproxy.http2.certbot": "true",
                                      })
    container2 = client.containers.run("byjg/static-httpserver",
                                       name="test2_processor_docker",
                                       detach=True,
                                       auto_remove=True,
                                       remove=True,
                                       labels={
                                           "easyhaproxy.ssl.port": "443",
                                           "easyhaproxy.ssl.localport": "8080",
                                           "easyhaproxy.ssl.host": "hostssl.local",
                                           "easyhaproxy.ssl.sslcert": "U29tZSBQRU0gQ2VydGlmaWNhdGU="
                                       })
    try:
        time.sleep(1)

        os.environ['EASYHAPROXY_CERTBOT_EMAIL'] = 'docker@example.org'

        static = ProcessorInterface.factory(ProcessorInterface.DOCKER)
        assert static.get_certbot_hosts() is None

        assert {
            'easyhaproxy.http.host': 'host1.local',
            'easyhaproxy.http.localport': '8080',
            'easyhaproxy.http.port': '80',
            'easyhaproxy.http2.host': 'host2.local',
            'easyhaproxy.http2.localport': '9000',
            'easyhaproxy.http2.port': '90',
            'easyhaproxy.http2.certbot': 'true',
        } == _get_hydrated_object(static.get_parsed_object(), "easyhaproxy.http")
        assert {
            'easyhaproxy.ssl.host': 'hostssl.local',
            'easyhaproxy.ssl.localport': '8080',
            'easyhaproxy.ssl.port': '443',
            'easyhaproxy.ssl.sslcert': 'U29tZSBQRU0gQ2VydGlmaWNhdGU='
        } == _get_hydrated_object(static.get_parsed_object(), "easyhaproxy.ssl.")

        assert static.get_hosts() is None
        assert static.get_certs() == {}

        haproxy_cfg = static.get_haproxy_conf()
        assert haproxy_cfg == Functions.load(os.path.join(os.path.dirname(os.path.realpath(__file__)), "./expected/docker.txt")).replace("test_processor_docker", _get_ip_host(
            static.get_parsed_object(), "easyhaproxy.http")).replace("test2_processor_docker", _get_ip_host(static.get_parsed_object(), "easyhaproxy.ssl"))

        assert static.get_certbot_hosts() == ['host2.local']
        assert static.get_hosts() == [
            'hostssl.local:443',
            'host1.local:80',
            'host2.local:90'
        ]
        assert static.get_certs() == {
            'hostssl.local.pem': 'Some PEM Certificate'
        }
    finally:
        del os.environ['EASYHAPROXY_CERTBOT_EMAIL']
        container.stop()
        container2.stop()


# test_processor_docker()


def _mock_container(name, ip=None, labels=None, network_mode="bridge"):
    container = Mock()
    container.name = name
    container.labels = labels or {}
    networks = {"easyhaproxy": {"IPAddress": ip}} if ip else {}
    container.attrs = {"HostConfig": {"NetworkMode": network_mode}, "NetworkSettings": {"Networks": networks}}
    return container


def _scan_docker(monkeypatch, containers):
    client = MagicMock()
    by_name = {container.name: container for container in containers}
    client.containers.list.return_value = containers
    client.containers.get.side_effect = lambda name: by_name.get(name, containers[0])
    client.networks.get.return_value.connect.side_effect = docker.errors.APIError("cannot connect")
    monkeypatch.setattr(docker, "from_env", lambda: client)
    return ProcessorInterface.factory(ProcessorInterface.DOCKER).get_parsed_object(), client


def test_processor_docker_skips_containers_that_cannot_join_the_network(monkeypatch):
    """host, none and container:<name> cannot join the HAProxy network: connecting them failed the whole scan"""
    labels = {"easyhaproxy.http.host": "web.test", "easyhaproxy.http.localport": "8080"}
    containers = [
        _mock_container("haproxy", ip="10.0.0.9"),
        _mock_container("web", ip="10.0.0.2", labels=labels),
        _mock_container("hostnet", labels=labels, network_mode="host"),
        _mock_container("nonet", network_mode="none"),
        _mock_container("sidecar", network_mode="container:web"),
    ]

    parsed, client = _scan_docker(monkeypatch, containers)

    assert parsed == {"10.0.0.2": labels}
    client.networks.get.return_value.connect.assert_not_called()


def test_processor_docker_unexpected_error_skips_only_that_container(monkeypatch):
    labels = {"easyhaproxy.http.host": "web.test", "easyhaproxy.http.localport": "8080"}
    broken = _mock_container("broken", labels=labels)
    broken.attrs = {"HostConfig": {"NetworkMode": "bridge"}}  # no NetworkSettings
    containers = [_mock_container("haproxy", ip="10.0.0.9"), broken, _mock_container("web", ip="10.0.0.2", labels=labels)]

    parsed, _ = _scan_docker(monkeypatch, containers)

    assert parsed == {"10.0.0.2": labels}


def test_processor_docker_does_not_connect_unlabeled_containers(monkeypatch):
    """A container without EasyHAProxy labels is not routed, so it must not join the HAProxy network"""
    labels = {"easyhaproxy.http.host": "web.test", "easyhaproxy.http.localport": "8080"}
    containers = [_mock_container("haproxy", ip="10.0.0.9"),
                  _mock_container("database"),  # on another network, no labels
                  _mock_container("web", ip="10.0.0.2", labels=labels)]

    parsed, client = _scan_docker(monkeypatch, containers)

    assert parsed == {"10.0.0.2": labels}
    client.networks.get.return_value.connect.assert_not_called()


def test_processor_docker_custom_label_prefix(monkeypatch):
    """Only labels that start with the prefix count: a short prefix must not match other labels"""
    monkeypatch.setenv("EASYHAPROXY_LABEL_PREFIX", "my")
    labels = {"my.http.host": "web.test", "my.http.localport": "8080"}
    containers = [_mock_container("haproxy", ip="10.0.0.9"),
                  _mock_container("app", labels={"com.mycompany.version": "1"}),  # another network
                  _mock_container("old", labels={"easyhaproxy.http.host": "old.test"}),  # another network
                  _mock_container("web", ip="10.0.0.2", labels=labels)]

    parsed, client = _scan_docker(monkeypatch, containers)

    assert parsed == {"10.0.0.2": labels}
    client.networks.get.return_value.connect.assert_not_called()
