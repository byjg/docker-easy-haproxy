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

    # assert on auth on stats
    assert "stats auth admin:test123" in haproxy_config

    # assert that we found redirect
    assert "redirect prefix http://host1.com.br code 301 if { hdr(host) -i www.host1.com.br }" in haproxy_config

    # assert that we found the services
    frontend_http_cfg = "frontend http_in_80_1\n"
    frontend_http_cfg += "    bind *:80"
    assert frontend_http_cfg in haproxy_config

    frontend_https_cfg = "frontend http_in_443_2\n"
    frontend_https_cfg += "    bind *:443"
    assert frontend_https_cfg in haproxy_config

    # print(haproxy_config)
    frontend_http8080_cfg = "frontend http_in_8080_3\n"
    frontend_http8080_cfg += "    bind *:8080"
    assert frontend_http8080_cfg in haproxy_config


    # verify ssl config with certificate
    frontend_ssl_cfg = "frontend http_in_443_2\n"
    frontend_ssl_cfg += "    bind *:443  ssl crt BASE64_PEM_CERTIFICATE"
    assert frontend_ssl_cfg in haproxy_config


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
