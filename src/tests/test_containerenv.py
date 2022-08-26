import pytest
import os
from processor import ContainerEnv

def test_container_env_empty():
    assert {
        "customerrors": False,
        "ssl_mode": "default",
        "lookup_label": "easyhaproxy"
    } == ContainerEnv.read()

    # os.environ['CERTBOT_LOG_LEVEL'] = 'warn'

def test_container_env_customerrors():
    os.environ['HAPROXY_CUSTOMERRORS'] = 'true'
    try:
        assert {
            "customerrors": True,
            "ssl_mode": "default",
            "lookup_label": "easyhaproxy"
        } == ContainerEnv.read()
    finally:
        os.environ['HAPROXY_CUSTOMERRORS'] = ''

def test_container_env_sslmode():
    os.environ['EASYHAPROXY_SSL_MODE'] = 'strict'
    try:
        assert {
            "customerrors": False,
            "ssl_mode": "strict",
            "lookup_label": "easyhaproxy"
        } == ContainerEnv.read()
    finally:
        os.environ['EASYHAPROXY_SSL_MODE'] = ''

def test_container_env_stats():
    os.environ['HAPROXY_USERNAME'] = 'abc'
    os.environ['HAPROXY_STATS_PORT'] = '2101'
    try:
        assert {
            "customerrors": False,
            "ssl_mode": "default",
            "lookup_label": "easyhaproxy",
        } == ContainerEnv.read()
    finally:
        os.environ['HAPROXY_USERNAME'] = ''
        os.environ['HAPROXY_STATS_PORT'] = ''

def test_container_env_stats_password():
    os.environ['HAPROXY_PASSWORD'] = 'xyz'
    try:
        assert {
            "customerrors": False,
            "ssl_mode": "default",
            "lookup_label": "easyhaproxy",
            "stats": {
                "username": "admin",
                "password": "xyz",
                "port": "1936"

            }
        } == ContainerEnv.read()
    finally:
        os.environ['HAPROXY_PASSWORD'] = ''


def test_container_env_stats_password():
    os.environ['HAPROXY_USERNAME'] = 'abc'
    os.environ['HAPROXY_STATS_PORT'] = '2101'
    os.environ['HAPROXY_PASSWORD'] = 'xyz'
    try:
        assert {
            "customerrors": False,
            "ssl_mode": "default",
            "lookup_label": "easyhaproxy",
            "stats": {
                "username": "abc",
                "password": "xyz",
                "port": "2101"

            }
        } == ContainerEnv.read()
    finally:
        os.environ['HAPROXY_USERNAME'] = ''
        os.environ['HAPROXY_STATS_PORT'] = ''
        os.environ['HAPROXY_PASSWORD'] = ''


def test_container_env_stats_password():
    os.environ['EASYHAPROXY_LETSENCRYPT_EMAIL'] = 'acme@example.org'
    try:
        assert {
            "customerrors": False,
            "ssl_mode": "default",
            "lookup_label": "easyhaproxy",
            "letsencrypt": {
                "email": "acme@example.org",
            }
        } == ContainerEnv.read()
    finally:
        os.environ['EASYHAPROXY_LETSENCRYPT_EMAIL'] = ''

