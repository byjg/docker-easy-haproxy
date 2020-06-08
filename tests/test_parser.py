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

    cfg = easymapping.HaproxyConfigGenerator(result, "/tmp")
    haproxy_config = cfg.generate(lineList)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/no-services.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config


def test_parser_finds_services():
    lineList = load_fixture("services")

    result = {
        "customerrors": False
    }

    cert_file = "/tmp/www.somehost.com.br.1.pem"
    if os.path.exists(cert_file):
        os.remove(cert_file)

    cfg = easymapping.HaproxyConfigGenerator(result, "/tmp")
    haproxy_config = cfg.generate(lineList)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config

    with open(cert_file, 'r') as expected_file:
        assert expected_file.read() == "Some PEM Certificate"


def test_parser_static():
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/fixtures/static.yml", 'r') as content_file:
        parsed = yaml.load(content_file.read(), Loader=yaml.FullLoader)

    cfg = easymapping.HaproxyConfigGenerator(parsed, "/tmp")
    haproxy_config = cfg.generate()
    assert len(haproxy_config) > 0

    with open(path + "/expected/static.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config


def test_parser_tcp():
    lineList = load_fixture("services-tcp")

    result = {
        "customerrors": False
    }

    cfg = easymapping.HaproxyConfigGenerator(result, "/tmp")
    haproxy_config = cfg.generate(lineList)
    # print(haproxy_config)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services-tcp.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config
