from .context import easymapping
import pytest
import os
import yaml


def load_fixture(file):
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/fixtures/" + file, 'r') as content_file:
        lineList = content_file.readlines()

    return lineList


def test_parser_doesnt_crash():
    lineList = load_fixture("no-services")

    result = {
        "customerrors": False
    }

    cfg = easymapping.HaproxyConfigGenerator(result)
    haproxy_config = cfg.generate(lineList)
    assert len(haproxy_config) > 0
    assert "frontend" not in haproxy_config
    assert "backend" not in haproxy_config


def test_parser_finds_services():
    lineList = load_fixture("services")

    result = {
        "customerrors": False
    }

    cfg = easymapping.HaproxyConfigGenerator(result)
    haproxy_config = cfg.generate(lineList)
    assert len(haproxy_config) > 0
    assert "mode tcp" in haproxy_config
    assert "mode http" in haproxy_config

    assert "frontend tcp_in_31339_1" in haproxy_config
    assert "frontend http_in_31337_2" in haproxy_config


def test_parser_static():
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/fixtures/static.yml", 'r') as content_file:
        parsed = yaml.load(content_file.read(), Loader=yaml.FullLoader)

    cfg = easymapping.HaproxyConfigGenerator(parsed)
    haproxy_config = cfg.generate()
    assert len(haproxy_config) > 0

    with open(path + "/expected/static.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config

def test_parser_tcp():
    lineList = load_fixture("services-tcp")

    result = {
        "customerrors": False
    }

    cfg = easymapping.HaproxyConfigGenerator(result)
    haproxy_config = cfg.generate(lineList)
    # print(haproxy_config)

    frontend_cfg = "frontend tcp_in_31339_1\n"
    frontend_cfg += "    bind *:31339\n"
    frontend_cfg += "    mode tcp\n"
    frontend_cfg += "    option tcplog\n"
    frontend_cfg += "    log global\n"
    frontend_cfg += "    default_backend srv_agent_quantum_local_31339_1\n\n"
    assert frontend_cfg in haproxy_config

    backend_cfg = "backend srv_agent_quantum_local_31339_1\n"
    backend_cfg += "    balance roundrobin\n"
    backend_cfg += "    mode tcp\n"
    backend_cfg += "    option tcp-check\n"
    backend_cfg += "    tcp-check connect ssl\n"
    backend_cfg += "    server srv test_agent:9001 check weight 1 verify none"

    assert backend_cfg in haproxy_config
