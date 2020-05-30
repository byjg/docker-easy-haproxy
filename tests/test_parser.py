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
    assert "frontend http_in_80_1" in haproxy_config
    assert "bind *:80"
    assert "frontend http_in_443_2" in haproxy_config
    assert "bind *:443"
    assert "frontend http_in_8080_3" in haproxy_config
    assert "bind :*8080"

    # verify ssl config
    assert "frontend http_in_443_2\n    bind *:443  ssl crt BASE64_PEM_CERTIFICATE" in haproxy_config
