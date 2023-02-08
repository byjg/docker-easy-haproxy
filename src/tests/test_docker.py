import pytest
import os
import time
import docker
from functions import Functions
from processor import ProcessorInterface
from processor import Docker


def _get_hydrated_object(parsed_objects, lookup_key):
    hydrated_object = {}
    for key in parsed_objects:
        for keys in parsed_objects[key]:
            if lookup_key in keys:
                hydrated_object[keys] = parsed_objects[key][keys]
    return hydrated_object


def _get_ip_host(parsed_objects, lookup_key):
    hydrated_object = {}
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
                                          "easyhaproxy.http2.letsencrypt": "true",
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

        os.environ['EASYHAPROXY_LETSENCRYPT_EMAIL'] = 'docker@example.org'

        static = ProcessorInterface.factory("docker")
        assert static.get_letsencrypt_hosts() is None

        assert {
            'easyhaproxy.http.host': 'host1.local',
            'easyhaproxy.http.localport': '8080',
            'easyhaproxy.http.port': '80',
            'easyhaproxy.http2.host': 'host2.local',
            'easyhaproxy.http2.localport': '9000',
            'easyhaproxy.http2.port': '90',
            'easyhaproxy.http2.letsencrypt': 'true',
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

        assert static.get_letsencrypt_hosts() == ['host2.local']
        assert static.get_hosts() == [
            'hostssl.local:443',
            'host1.local:80',
            'host2.local:90'
        ]
        assert static.get_certs() == {
            'hostssl.local.pem': 'Some PEM Certificate'
        }
    finally:
        os.environ['EASYHAPROXY_LETSENCRYPT_EMAIL'] = ''
        container.stop()
        container2.stop()


# test_processor_docker()
