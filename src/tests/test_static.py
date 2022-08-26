import pytest
import os
from functions import Functions
from processor import ProcessorInterface
from processor import Static

def test_processor_static():
    ProcessorInterface.static_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "./fixtures/static.yml")
    static = ProcessorInterface.factory("static")

    assert static.get_letsencrypt_hosts() is None
    assert static.get_parsed_object() == {}
    assert static.get_hosts() is None

    haproxy_cfg = static.get_haproxy_conf()

    assert haproxy_cfg == Functions.load(os.path.join(os.path.dirname(os.path.realpath(__file__)), "./expected/static.txt"))

    # @todo: Static doesnt populate this fields
    assert static.get_letsencrypt_hosts() == []
    assert static.get_parsed_object() == {}
    assert static.get_hosts() == []

# test_processor_static()