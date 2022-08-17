import easymapping
import pytest
import os
import yaml

CERTS_FOLDER="/tmp/certs"
CERT_FILE="/tmp/certs/haproxy/www.somehost.com.br.pem"
LETSENCRYPT_EMAIL="some@email.com"

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

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/no-services.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config
    assert [] == cfg.letsencrypt_hosts

def test_parser_finds_services():
    line_list = load_fixture("services")

    result = {
        "customerrors": False,
        "letsencrypt": {
            "email": LETSENCRYPT_EMAIL
        }
    }

    if os.path.exists(CERT_FILE):
        os.remove(CERT_FILE)

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config

    with open(CERT_FILE, 'r') as expected_file:
        assert expected_file.read() == "Some PEM Certificate"

    assert ['node-exporter.quantum.example.org'] == cfg.letsencrypt_hosts

def test_parser_finds_services_changed_label():
    line_list = load_fixture("services-changed-label")

    result = {
        "customerrors": False,
        "lookup_label": "haproxy",
        "letsencrypt": {
            "email": LETSENCRYPT_EMAIL
        }
    }

    if os.path.exists(CERT_FILE):
        os.remove(CERT_FILE)

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config

    with open(CERT_FILE, 'r') as expected_file:
        assert expected_file.read() == "Some PEM Certificate"

    assert ['node-exporter.quantum.example.org'] == cfg.letsencrypt_hosts

def test_parser_finds_services_raw():
    line_list = load_fixture("services")

    result = {
        "customerrors": False,
        "letsencrypt": {
            "email": LETSENCRYPT_EMAIL
        }
    }

    if os.path.exists(CERT_FILE):
        os.remove(CERT_FILE)

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)

    parsed_object = [
        {
            "mode":"tcp",
            "health-check":"",
            "port":"31339",
            "hosts":{
                "agent.quantum.example.org": {
                    "containers": [
                        "my-stack_agent:9001"
                    ],
                    "letsencrypt": False,
                    "redirect_ssl": False
                }
            },
            "redirect":{
                
            }
        },
        {
            "mode":"http",
            "health-check":"",
            "port":"31337",
            "hosts":{
                "cadvisor.quantum.example.org":{
                    "containers": [
                        "my-stack_cadvisor:8080"
                    ],
                    "letsencrypt": False,
                    "redirect_ssl": False
                },
                "node-exporter.quantum.example.org":{
                    "containers": [
                        "my-stack_node-exporter:9100"
                    ],
                    "letsencrypt": True,
                    "redirect_ssl": False
                }
            },
            "redirect":{
                
            },
        },
        {
            "mode":"http",
            "health-check":"",
            "port":"443",
            "hosts":{
                "node-exporter.quantum.example.org": {
                    "containers": [
                        "my-stack_node-exporter:9100"
                    ],
                    "letsencrypt": False,
                    "redirect_ssl": False
                },
                "www.somehost.com.br":{
                    "containers": [
                        "some-service:80"
                    ],
                    "letsencrypt": False,
                    "redirect_ssl": False
                }
            },
            "redirect":{
                "somehost.com.br":"https://www.somehost.com.br",
                "somehost.com":"https://www.somehost.com.br",
                "www.somehost.com":"https://www.somehost.com.br",
                "byjg.ca":"https://www.somehost.com.br",
                "www.byjg.ca":"https://www.somehost.com.br"
            },
            "ssl_cert":CERT_FILE
        },
        {
            "mode":"http",
            "health-check":"",
            "port":"80",
            "hosts":{
                "www.somehost.com.br":{
                    "containers": [
                        "some-service:80"
                    ],
                    "letsencrypt": False,
                    "redirect_ssl": False
                }
            },
            "redirect":{
                "somehost.com.br":"https://www.somehost.com.br",
                "somehost.com":"https://www.somehost.com.br",
                "www.somehost.com":"https://www.somehost.com.br",
                "byjg.ca":"https://www.somehost.com.br",
                "www.byjg.ca":"https://www.somehost.com.br"
            },
        }
    ]

    processed = list(cfg.parse(line_list))

    assert parsed_object == processed
    assert ['node-exporter.quantum.example.org'] == cfg.letsencrypt_hosts



def test_parser_static():
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/fixtures/static.yml", 'r') as content_file:
        parsed = yaml.load(content_file.read(), Loader=yaml.FullLoader)

    cfg = easymapping.HaproxyConfigGenerator(parsed, CERTS_FOLDER)
    haproxy_config = cfg.generate()
    assert len(haproxy_config) > 0

    with open(path + "/expected/static.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config
    assert [] == cfg.letsencrypt_hosts

def test_parser_static_raw():
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/fixtures/static.yml", 'r') as content_file:
        parsed = yaml.load(content_file.read(), Loader=yaml.FullLoader)

    expected = {
        "stats": {
            "username": "admin",
            "password": "test123",
            "port": 1936
        },
        "customerrors": True,
        "easymapping": [
            {
                "port": 80,
                "hosts": {
                    "host1.com.br": {
                        "containers": [
                            "container:5000"
                        ],
                        "letsencrypt": True
                    },
                    "host2.com.br": {
                        "containers": [
                            "other:3000"
                        ]
                    }
                },
                "redirect": {
                    "www.host1.com.br": "http://host1.com.br"
                }
            },
            {
                "port": 443,
                "ssl_cert": "/certs/haproxy/mycert.pem",
                "hosts": {
                    "host1.com.br": {
                        "containers": [
                            "container:80"
                        ]
                    }
                }
            },
            {
                "port": 8080,
                "hosts": {
                    "host3.com.br": {
                        "containers": [
                            "domain:8181"
                        ]
                    }
                }
            }
        ]
    }

    assert expected == parsed



def test_parser_tcp():
    line_list = load_fixture("services-tcp")

    result = {
        "customerrors": False
    }

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)
    haproxy_config = cfg.generate(line_list)
    # print(haproxy_config)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services-tcp.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config
    assert [] == cfg.letsencrypt_hosts

def test_parser_multi_containers():
    line_list = load_fixture("services-multi-containers")

    result = {
        "customerrors": False
    }

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services-multi-containers.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config
    assert [] == cfg.letsencrypt_hosts


def test_parser_multiple_hosts():
    line_list = load_fixture("services-multiple-hosts")

    result = {
        "customerrors": True,
        "stats": {
            "username": "joe",
            "password": "s3cr3t",
            "port": "1937"
        }
    }

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services-multiple-hosts.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config
    assert [] == cfg.letsencrypt_hosts


def test_parser_redirect_ssl():
    line_list = load_fixture("services-redirect-ssl")

    result = {
        "customerrors": False
    }

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services-redirect-ssl.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config
    assert [] == cfg.letsencrypt_hosts


def test_parser_ssl_strict():
    line_list = load_fixture("no-services")

    result = {
        "customerrors": False,
        "ssl_mode": "strict"
    }

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/ssl-strict.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config
    assert [] == cfg.letsencrypt_hosts

def test_parser_ssl_loose():
    line_list = load_fixture("no-services")

    result = {
        "customerrors": False,
        "ssl_mode": "loose"
    }

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/ssl-loose.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config
    assert [] == cfg.letsencrypt_hosts

def test_parser_ssl_letsencrypt():
    line_list = load_fixture("services-letsencrypt")

    result = {
        "customerrors": True,
        "stats": {
            "username": "admin",
            "password": "password"
        },
        "letsencrypt": {
            "email": LETSENCRYPT_EMAIL
        }
    }

    cfg = easymapping.HaproxyConfigGenerator(result, CERTS_FOLDER)
    haproxy_config = cfg.generate(line_list)

    assert len(haproxy_config) > 0
    path = os.path.dirname(os.path.realpath(__file__))
    with open(path + "/expected/services-letsencrypt.txt", 'r') as expected_file:
        assert expected_file.read() == haproxy_config
    assert ["test.example.org"] == cfg.letsencrypt_hosts

#test_parser_finds_services_raw()
#test_parser_tcp()
#test_parser_multiple_hosts()
#test_parser_ssl_letsencrypt()