import os

from functions import Functions, ContainerEnv


def test_container_env_empty():
    assert {
               "customerrors": False,
               "ssl_mode": "default",
               "lookup_label": "easyhaproxy",
               "logLevel": {
                   "easyhaproxy": Functions.DEBUG,
                   "haproxy": Functions.INFO,
                   "certbot": Functions.DEBUG,
               },
               "certbot": {"autoconfig": "",
                           "eab_hmac_key": "",
                           "eab_kid": "",
                           "email": "",
                           "server": False,
                           "retry_count": 60,
                           "preferred_challenges": "http",
                           "manual_auth_hook": False},
               "plugins": {
                   "abort_on_error": False,
                   "config": {},
                   "enabled": []
               }
           } == ContainerEnv.read()

    # os.environ['CERTBOT_LOG_LEVEL'] = 'warn'


def test_container_env_customerrors():
    os.environ['HAPROXY_CUSTOMERRORS'] = 'true'
    try:
        assert {
                   "customerrors": True,
                   "ssl_mode": "default",
                   "lookup_label": "easyhaproxy",
                   "logLevel": {
                       "easyhaproxy": Functions.DEBUG,
                       "haproxy": Functions.INFO,
                       "certbot": Functions.DEBUG,
                   },
                   "certbot": {"autoconfig": "",
                               "eab_hmac_key": "",
                               "eab_kid": "",
                               "email": "",
                               "server": False,
                               "retry_count": 60,
                               "preferred_challenges": "http",
                               "manual_auth_hook": False},
                   "plugins": {
                       "abort_on_error": False,
                       "config": {},
                       "enabled": []
                   }
               } == ContainerEnv.read()
    finally:
        del os.environ['HAPROXY_CUSTOMERRORS']


def test_container_env_sslmode():
    os.environ['EASYHAPROXY_SSL_MODE'] = 'STRICT'
    try:
        assert {
                   "customerrors": False,
                   "ssl_mode": "strict",
                   "lookup_label": "easyhaproxy",
                   "logLevel": {
                       "easyhaproxy": Functions.DEBUG,
                       "haproxy": Functions.INFO,
                       "certbot": Functions.DEBUG,
                   },
                   "certbot": {"autoconfig": "",
                               "eab_hmac_key": "",
                               "eab_kid": "",
                               "email": "",
                               "server": False,
                               "retry_count": 60,
                               "preferred_challenges": "http",
                               "manual_auth_hook": False},
                   "plugins": {
                       "abort_on_error": False,
                       "config": {},
                       "enabled": []
                   }
               } == ContainerEnv.read()
    finally:
        del os.environ['EASYHAPROXY_SSL_MODE']


def test_container_env_stats():
    os.environ['HAPROXY_USERNAME'] = 'abc'
    os.environ['HAPROXY_STATS_PORT'] = '2101'
    try:
        assert {
                   "customerrors": False,
                   "ssl_mode": "default",
                   "lookup_label": "easyhaproxy",
                   "logLevel": {
                       "easyhaproxy": Functions.DEBUG,
                       "haproxy": Functions.INFO,
                       "certbot": Functions.DEBUG,
                   },
                   "certbot": {"autoconfig": "",
                               "eab_hmac_key": "",
                               "eab_kid": "",
                               "email": "",
                               "server": False,
                               "retry_count": 60,
                               "preferred_challenges": "http",
                               "manual_auth_hook": False},
                   "plugins": {
                       "abort_on_error": False,
                       "config": {},
                       "enabled": []
                   }
               } == ContainerEnv.read()
    finally:
        del os.environ['HAPROXY_USERNAME']
        del os.environ['HAPROXY_STATS_PORT']


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
                   "logLevel": {
                       "easyhaproxy": Functions.DEBUG,
                       "haproxy": Functions.INFO,
                       "certbot": Functions.DEBUG,
                   },
                   "certbot": {"autoconfig": "",
                               "eab_hmac_key": "",
                               "eab_kid": "",
                               "email": "",
                               "server": False,
                               "retry_count": 60,
                               "preferred_challenges": "http",
                               "manual_auth_hook": False},
                   "plugins": {
                       "abort_on_error": False,
                       "config": {},
                       "enabled": []
                   }
               } == ContainerEnv.read()
    finally:
        del os.environ['HAPROXY_PASSWORD']


def test_container_env_stats_password_2():
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
                   "logLevel": {
                       "easyhaproxy": Functions.DEBUG,
                       "haproxy": Functions.INFO,
                       "certbot": Functions.DEBUG,
                   },
                   "certbot": {"autoconfig": "",
                               "eab_hmac_key": "",
                               "eab_kid": "",
                               "email": "",
                               "server": False,
                               "retry_count": 60,
                               "preferred_challenges": "http",
                               "manual_auth_hook": False},
                   "plugins": {
                       "abort_on_error": False,
                       "config": {},
                       "enabled": []
                   }
               } == ContainerEnv.read()
    finally:
        del os.environ['HAPROXY_USERNAME']
        del os.environ['HAPROXY_STATS_PORT']
        del os.environ['HAPROXY_PASSWORD']


def test_container_env_certbot_email():
    os.environ['EASYHAPROXY_CERTBOT_EMAIL'] = 'acme@example.org'
    try:
        assert {
                   "customerrors": False,
                   "ssl_mode": "default",
                   "lookup_label": "easyhaproxy",
                   "logLevel": {
                       "easyhaproxy": Functions.DEBUG,
                       "haproxy": Functions.INFO,
                       "certbot": Functions.DEBUG,
                   },
                   "certbot": {
                       "autoconfig": "",
                       'eab_hmac_key': "",
                       'eab_kid': "",
                       "email": "acme@example.org",
                       "server": False,
                       "retry_count": 60,
                       "preferred_challenges": "http",
                       "manual_auth_hook": False
                   },
                   "plugins": {
                       "abort_on_error": False,
                       "config": {},
                       "enabled": []
                   }
               } == ContainerEnv.read()
    finally:
        del os.environ['EASYHAPROXY_CERTBOT_EMAIL']


def test_container_env_certbot_full():
    os.environ['EASYHAPROXY_CERTBOT_EMAIL'] = 'acme@example.org'
    os.environ['EASYHAPROXY_CERTBOT_SERVER'] = 'schema://url/a'
    os.environ['EASYHAPROXY_CERTBOT_EAB_KID'] = 'eab_kid'
    os.environ['EASYHAPROXY_CERTBOT_EAB_HMAC_KEY'] = 'eab_hmac_key'
    os.environ['EASYHAPROXY_CERTBOT_RETRY_COUNT'] = "10"
    os.environ['EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES'] = "dns"
    os.environ['EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK'] = "something_manual_auth_hook"
    try:
        assert {
            "customerrors": False,
            "ssl_mode": "default",
            "lookup_label": "easyhaproxy",
            "logLevel": {
                "easyhaproxy": Functions.DEBUG,
                "haproxy": Functions.INFO,
                "certbot": Functions.DEBUG,
            },
           "certbot": {
               "autoconfig": "",
               "email": "acme@example.org",
               "server": "schema://url/a",
               'eab_hmac_key': 'eab_hmac_key',
               'eab_kid': 'eab_kid',
               'retry_count': 10,
               "preferred_challenges": "dns",
               "manual_auth_hook": "something_manual_auth_hook"
           },
           "plugins": {
               "abort_on_error": False,
               "config": {},
               "enabled": []
           }
        } == ContainerEnv.read()
    finally:
        del os.environ['EASYHAPROXY_CERTBOT_EMAIL']
        del os.environ['EASYHAPROXY_CERTBOT_SERVER']
        del os.environ['EASYHAPROXY_CERTBOT_EAB_KID']
        del os.environ['EASYHAPROXY_CERTBOT_EAB_HMAC_KEY']
        del os.environ['EASYHAPROXY_CERTBOT_RETRY_COUNT']
        del os.environ['EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES']
        del os.environ['EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK']


def test_container_log_level():
    os.environ['CERTBOT_LOG_LEVEL'] = Functions.TRACE
    os.environ['EASYHAPROXY_LOG_LEVEL'] = Functions.ERROR
    os.environ['HAPROXY_LOG_LEVEL'] = Functions.FATAL
    try:
        assert {
           "customerrors": False,
           "ssl_mode": "default",
           "lookup_label": "easyhaproxy",
           "logLevel": {
               "easyhaproxy": Functions.ERROR,
               "haproxy": Functions.FATAL,
               "certbot": Functions.TRACE,
           },
           "certbot": {
               "autoconfig": "",
               'eab_hmac_key': "",
               'eab_kid': "",
               "email": "",
               "server": False,
               "retry_count": 60,
               "preferred_challenges": "http",
               "manual_auth_hook": False
           },
           "plugins": {
               "abort_on_error": False,
               "config": {},
               "enabled": []
           }
       } == ContainerEnv.read()
    finally:
        del os.environ['CERTBOT_LOG_LEVEL']
        del os.environ['EASYHAPROXY_LOG_LEVEL']
        del os.environ['HAPROXY_LOG_LEVEL']
