import easymapping
import pytest
import os
import yaml


def load_fixture(file):
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/fixtures/" + file, 'r') as content_file:
        line_list = content_file.readlines()

    return line_list


def test_parser_doesnt_crash():
    line_list = load_fixture("no-services")

    result = {
        "customerrors": False
    }

    cfg = easymapping.HaproxyConfigGenerator(result, "/tmp")
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/no-services.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config


def test_parser_finds_services():
    line_list = load_fixture("services")

    result = {
        "customerrors": False
    }

    cert_file = "/tmp/www.somehost.com.br.1.pem"
    if os.path.exists(cert_file):
        os.remove(cert_file)

    cfg = easymapping.HaproxyConfigGenerator(result, "/tmp")
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config

    with open(cert_file, 'r') as expected_file:
        assert expected_file.read() == "Some PEM Certificate"

def test_parser_finds_services_changed_label():
    line_list = load_fixture("services-changed-label")

    result = {
        "customerrors": False,
        "lookup_label": "haproxy"
    }

    cert_file = "/tmp/www.somehost.com.br.1.pem"
    if os.path.exists(cert_file):
        os.remove(cert_file)

    cfg = easymapping.HaproxyConfigGenerator(result, "/tmp")
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config

    with open(cert_file, 'r') as expected_file:
        assert expected_file.read() == "Some PEM Certificate"

def test_parser_finds_services_raw():
    line_list = load_fixture("services")

    result = {
        "customerrors": False
    }

    cert_file = "/tmp/www.somehost.com.br.1.pem"
    if os.path.exists(cert_file):
        os.remove(cert_file)

    cfg = easymapping.HaproxyConfigGenerator(result, "/tmp")

    parsed_object = [
        {
            "mode":"tcp",
            "health-check":"",
            "port":"31339",
            "hosts":{
                "agent.quantum.example.org":[
                    "my-stack_agent:9001"
                ]
            },
            "redirect":{
                
            }
        },
        {
            "mode":"http",
            "health-check":"",
            "port":"31337",
            "hosts":{
                "cadvisor.quantum.example.org":[
                    "my-stack_cadvisor:8080"
                ],
                "node-exporter.quantum.example.org":[
                    "my-stack_node-exporter:9100"
                ]
            },
            "redirect":{
                
            }
        },
        {
            "mode":"http",
            "health-check":"",
            "port":"80",
            "hosts":{
                "www.somehost.com.br":[
                    "some-service:80"
                ]
            },
            "redirect":{
                "somehost.com.br":"https://www.somehost.com.br",
                "somehost.com":"https://www.somehost.com.br",
                "www.somehost.com":"https://www.somehost.com.br",
                "byjg.ca":"https://www.somehost.com.br",
                "www.byjg.ca":"https://www.somehost.com.br"
            }
        },
        {
            "mode":"http",
            "health-check":"",
            "port":"443",
            "hosts":{
                "www.somehost.com.br":[
                    "some-service:80"
                ]
            },
            "redirect":{
                "somehost.com.br":"https://www.somehost.com.br",
                "somehost.com":"https://www.somehost.com.br",
                "www.somehost.com":"https://www.somehost.com.br",
                "byjg.ca":"https://www.somehost.com.br",
                "www.byjg.ca":"https://www.somehost.com.br"
            },
            "ssl_cert":"/tmp/www.somehost.com.br.1.pem"
        }
    ]

    processed = list(cfg.parse(line_list))

    assert parsed_object == processed



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
    line_list = load_fixture("services-tcp")

    result = {
        "customerrors": False
    }

    cfg = easymapping.HaproxyConfigGenerator(result, "/tmp")
    haproxy_config = cfg.generate(line_list)
    # print(haproxy_config)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services-tcp.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config

def test_parser_multi_containers():
    line_list = load_fixture("services-multi-containers")

    result = {
        "customerrors": False
    }

    cfg = easymapping.HaproxyConfigGenerator(result, "/tmp")
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services-multi-containers.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config


#test_parser_finds_services_raw()
#test_parser_tcp()
