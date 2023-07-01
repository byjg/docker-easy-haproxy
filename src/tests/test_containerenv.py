import pytest
import os
from processor import ContainerEnv

def test_container_env_empty():
    assert {
        "customerrors": False,
        "ssl_mode": "default",
        "lookup_label": "easyhaproxy",
        "certbot": {"eab_hmac_key": "",
                    "eab_kid": "",
                    "email": "",
                    "server": False}
    } == ContainerEnv.read()

    # os.environ['CERTBOT_LOG_LEVEL'] = 'warn'

def test_container_env_customerrors():
    os.environ['HAPROXY_CUSTOMERRORS'] = 'true'
    try:
        assert {
            "customerrors": True,
            "ssl_mode": "default",
            "lookup_label": "easyhaproxy",
            "certbot": {"eab_hmac_key": "",
                        "eab_kid": "",
                        "email": "",
                        "server": False}
        } == ContainerEnv.read()
    finally:
        os.environ['HAPROXY_CUSTOMERRORS'] = ''

def test_container_env_sslmode():
    os.environ['EASYHAPROXY_SSL_MODE'] = 'STRICT'
    try:
        assert {
            "customerrors": False,
            "ssl_mode": "strict",
            "lookup_label": "easyhaproxy",
            "certbot": {"eab_hmac_key": "",
                        "eab_kid": "",
                        "email": "",
                        "server": False}
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
            "certbot": {"eab_hmac_key": "",
                        "eab_kid": "",
                        "email": "",
                        "server": False}
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

            },
            "certbot": {"eab_hmac_key": "",
                        "eab_kid": "",
                        "email": "",
                        "server": False}
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
            },
            "certbot": {"eab_hmac_key": "",
                        "eab_kid": "",
                        "email": "",
                        "server": False}
        } == ContainerEnv.read()
    finally:
        os.environ['HAPROXY_USERNAME'] = ''
        os.environ['HAPROXY_STATS_PORT'] = ''
        os.environ['HAPROXY_PASSWORD'] = ''


def test_container_env_certbot_email():
    os.environ['EASYHAPROXY_CERTBOT_EMAIL'] = 'acme@example.org'
    try:
        assert {
            "customerrors": False,
            "ssl_mode": "default",
            "lookup_label": "easyhaproxy",
            "certbot": {
                'eab_hmac_key': "",
                'eab_kid': "",
                "email": "acme@example.org",
                "server": False
            }
        } == ContainerEnv.read()
    finally:
        os.environ['EASYHAPROXY_CERTBOT_EMAIL'] = ''

def test_container_env_certbot_full():
    os.environ['EASYHAPROXY_CERTBOT_EMAIL'] = 'acme@example.org'
    os.environ['EASYHAPROXY_CERTBOT_SERVER'] = 'schema://url/a'
    os.environ['EASYHAPROXY_CERTBOT_EAB_KID'] = 'eab_kid'
    os.environ['EASYHAPROXY_CERTBOT_EAB_HMAC_KEY'] = 'eab_hmac_key'
    try:
        assert {
            "customerrors": False,
            "ssl_mode": "default",
            "lookup_label": "easyhaproxy",
            "certbot": {
                "email": "acme@example.org",
                "server": "schema://url/a",
                'eab_hmac_key': 'eab_hmac_key',
                'eab_kid': 'eab_kid',
            }
        } == ContainerEnv.read()
    finally:
        os.environ['EASYHAPROXY_CERTBOT_EMAIL'] = ''