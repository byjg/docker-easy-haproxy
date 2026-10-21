"""
Stats and dashboard frontends, as rendered from the environment.

Stats are served unless HAPROXY_STATS_ENABLE=false. HAPROXY_PASSWORD only
decides whether they require a login.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import easymapping
from functions import ContainerEnv

STATS_VARS = ['HAPROXY_STATS_ENABLE', 'HAPROXY_PASSWORD', 'HAPROXY_USERNAME', 'HAPROXY_STATS_PORT']


def render(monkeypatch, **env):
    for name in STATS_VARS:
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return easymapping.HaproxyConfigGenerator(ContainerEnv.read()).generate({})


def test_stats_with_password_require_login(monkeypatch):
    cfg = render(monkeypatch, HAPROXY_PASSWORD='secret')
    assert 'frontend stats' in cfg
    assert 'stats auth admin:secret' in cfg
    assert 'frontend dashboard' in cfg


def test_stats_without_password_served_without_login(monkeypatch):
    cfg = render(monkeypatch)
    assert 'frontend stats' in cfg
    assert 'stats auth' not in cfg
    assert 'frontend dashboard' in cfg


def test_stats_disabled(monkeypatch):
    cfg = render(monkeypatch, HAPROXY_STATS_ENABLE='false', HAPROXY_PASSWORD='secret')
    assert 'frontend stats' not in cfg
    assert 'frontend dashboard' not in cfg


def test_stats_disabled_by_port_false(monkeypatch):
    """HAPROXY_STATS_PORT=false keeps working as a way to turn stats off"""
    cfg = render(monkeypatch, HAPROXY_STATS_PORT='false')
    assert 'frontend stats' not in cfg
    assert 'frontend dashboard' not in cfg


def test_stats_port_without_password(monkeypatch):
    """The port was ignored unless a password was set"""
    cfg = render(monkeypatch, HAPROXY_STATS_PORT='2101')
    assert 'bind *:2101' in cfg
    assert 'bind *:12101' in cfg
    assert 'bind *:1936' not in cfg


def test_stats_disabled_from_yaml_config(monkeypatch):
    for name in STATS_VARS:
        monkeypatch.delenv(name, raising=False)
    ContainerEnv._yaml_to_env({'stats': {'enabled': False}})
    try:
        cfg = easymapping.HaproxyConfigGenerator(ContainerEnv.read()).generate({})
    finally:
        os.environ.pop('HAPROXY_STATS_ENABLE', None)
    assert 'frontend stats' not in cfg
