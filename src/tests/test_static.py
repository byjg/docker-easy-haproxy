import os

from functions import Functions
from processor import ProcessorInterface


def test_processor_static():
    ProcessorInterface.static_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "./fixtures/static.yml")
    static = ProcessorInterface.factory(ProcessorInterface.STATIC)

    parsed_object = [
        {
            "hosts": {
                "host1.com.br": {
                    "containers": [
                        "container:5000"
                    ],
                    "certbot": True
                },
                "host2.com.br": {
                    "containers": [
                        "other:3000"
                    ]
                }
            },
            "port": 80,
            "redirect": {
                "www.host1.com.br": "http://host1.com.br"
            }
        },
        {
            "hosts": {
                "host1.com.br": {
                    "containers": [
                        "container:80"
                    ]
                }
            },
            "port": 443,
            "ssl": True
        },
        {
            "hosts": {
                "host3.com.br": {
                    "containers": [
                        "domain:8181"
                    ]
                }
            },
            "port": 8080
        }
    ]
    hosts = [
        'host1.com.br:80',
        'host2.com.br:80',
        'host1.com.br:443',
        'host3.com.br:8080'
    ]

    assert static.get_certbot_hosts() is None
    assert static.get_parsed_object() == parsed_object
    assert static.get_hosts() == hosts

    haproxy_cfg = static.get_haproxy_conf()

    assert haproxy_cfg == Functions.load(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "./expected/static.txt"))

    # @todo: Static doesnt populate this fields
    assert static.get_certbot_hosts() == []
    assert static.get_parsed_object() == parsed_object
    assert static.get_hosts() == hosts

# test_processor_static()
