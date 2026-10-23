import shutil

import pytest

from easyhaproxy.main import apply_config
from functions import DaemonizeHAProxy, Functions

pytestmark = pytest.mark.skipif(shutil.which("haproxy") is None, reason="needs the haproxy binary (runs in the image build)")

CONFIG = """global
defaults
    mode http
    timeout connect 1s
    timeout client 1s
    timeout server 1s
frontend http
    bind :8080
    default_backend web
backend web
    server srv-0 {server}
"""
VALID = CONFIG.format(server="10.0.0.1:8080")
# What a headless Service or a named port used to produce
INVALID = CONFIG.format(server="10.0.0.1:None")


class ConfigWriter:
    def __init__(self, config):
        self.config = config

    def save_config(self, filename):
        Functions.save(filename, self.config)

    def save_certs(self, path):
        pass


def _apply(tmp_path, config):
    haproxy = DaemonizeHAProxy(custom_config_folder=str(tmp_path / "custom"))
    return apply_config(ConfigWriter(config), haproxy, str(tmp_path / "haproxy.cfg"), str(tmp_path))


def test_valid_config_is_written(tmp_path):
    assert _apply(tmp_path, VALID) is True
    assert (tmp_path / "haproxy.cfg").read_text() == VALID


def test_invalid_config_keeps_the_previous_one(tmp_path):
    """A reload with a config HAProxy rejects stopped HAProxy for every site"""
    _apply(tmp_path, VALID)

    assert _apply(tmp_path, INVALID) is False
    assert (tmp_path / "haproxy.cfg").read_text() == VALID
