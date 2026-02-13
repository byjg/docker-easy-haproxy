import os

from functions import ContainerEnv, Functions


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
               },
               "update_ingress_status": True,
               "deployment_mode": "auto",
               "external_hostname": "",
               "ingress_status_update_interval": 30
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
                   },
                   "update_ingress_status": True,
                   "deployment_mode": "auto",
                   "external_hostname": "",
                   "ingress_status_update_interval": 30
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
                   },
                   "update_ingress_status": True,
                   "deployment_mode": "auto",
                   "external_hostname": "",
                   "ingress_status_update_interval": 30
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
                   },
                   "update_ingress_status": True,
                   "deployment_mode": "auto",
                   "external_hostname": "",
                   "ingress_status_update_interval": 30
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
                   },
                   "update_ingress_status": True,
                   "deployment_mode": "auto",
                   "external_hostname": "",
                   "ingress_status_update_interval": 30
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
                   },
                   "update_ingress_status": True,
                   "deployment_mode": "auto",
                   "external_hostname": "",
                   "ingress_status_update_interval": 30
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
                   },
                   "update_ingress_status": True,
                   "deployment_mode": "auto",
                   "external_hostname": "",
                   "ingress_status_update_interval": 30
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
           },
           "update_ingress_status": True,
           "deployment_mode": "auto",
           "external_hostname": "",
           "ingress_status_update_interval": 30
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
           },
           "update_ingress_status": True,
           "deployment_mode": "auto",
           "external_hostname": "",
           "ingress_status_update_interval": 30
       } == ContainerEnv.read()
    finally:
        del os.environ['CERTBOT_LOG_LEVEL']
        del os.environ['EASYHAPROXY_LOG_LEVEL']
        del os.environ['HAPROXY_LOG_LEVEL']


def test_yaml_to_env_loglevel():
    """Test that YAML logLevel config is properly converted to environment variables"""
    yaml_config = {
        "logLevel": {
            "easyhaproxy": Functions.ERROR,
            "haproxy": Functions.FATAL,
            "certbot": Functions.TRACE,
        }
    }
    try:
        result = ContainerEnv.read(yaml_config)
        assert result["logLevel"]["easyhaproxy"] == Functions.ERROR
        assert result["logLevel"]["haproxy"] == Functions.FATAL
        assert result["logLevel"]["certbot"] == Functions.TRACE
        # Verify environment variables were set
        assert os.environ.get('EASYHAPROXY_LOG_LEVEL') == Functions.ERROR
        assert os.environ.get('HAPROXY_LOG_LEVEL') == Functions.FATAL
        assert os.environ.get('CERTBOT_LOG_LEVEL') == Functions.TRACE
    finally:
        # Cleanup
        for key in ['EASYHAPROXY_LOG_LEVEL', 'HAPROXY_LOG_LEVEL', 'CERTBOT_LOG_LEVEL']:
            if key in os.environ:
                del os.environ[key]


def test_yaml_to_env_certbot():
    """Test that YAML certbot config is properly converted to environment variables"""
    yaml_config = {
        "certbot": {
            "email": "test@example.com",
            "autoconfig": "letsencrypt",
            "server": "https://acme-v02.api.letsencrypt.org/directory",
            "eab_kid": "test_kid",
            "eab_hmac_key": "test_hmac",
            "retry_count": 10,
            "preferred_challenges": "dns",
            "manual_auth_hook": "test_hook"
        }
    }
    try:
        result = ContainerEnv.read(yaml_config)
        assert result["certbot"]["email"] == "test@example.com"
        assert result["certbot"]["autoconfig"] == "letsencrypt"
        assert result["certbot"]["server"] == "https://acme-v02.api.letsencrypt.org/directory"
        assert result["certbot"]["eab_kid"] == "test_kid"
        assert result["certbot"]["eab_hmac_key"] == "test_hmac"
        assert result["certbot"]["retry_count"] == 10
        assert result["certbot"]["preferred_challenges"] == "dns"
        assert result["certbot"]["manual_auth_hook"] == "test_hook"
        # Verify environment variables were set
        assert os.environ.get('EASYHAPROXY_CERTBOT_EMAIL') == "test@example.com"
        assert os.environ.get('EASYHAPROXY_CERTBOT_AUTOCONFIG') == "letsencrypt"
        assert os.environ.get('EASYHAPROXY_CERTBOT_SERVER') == "https://acme-v02.api.letsencrypt.org/directory"
        assert os.environ.get('EASYHAPROXY_CERTBOT_EAB_KID') == "test_kid"
        assert os.environ.get('EASYHAPROXY_CERTBOT_EAB_HMAC_KEY') == "test_hmac"
        assert os.environ.get('EASYHAPROXY_CERTBOT_RETRY_COUNT') == "10"
        assert os.environ.get('EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES') == "dns"
        assert os.environ.get('EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK') == "test_hook"
    finally:
        # Cleanup
        for key in ['EASYHAPROXY_CERTBOT_EMAIL', 'EASYHAPROXY_CERTBOT_AUTOCONFIG',
                    'EASYHAPROXY_CERTBOT_SERVER', 'EASYHAPROXY_CERTBOT_EAB_KID',
                    'EASYHAPROXY_CERTBOT_EAB_HMAC_KEY', 'EASYHAPROXY_CERTBOT_RETRY_COUNT',
                    'EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES', 'EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK']:
            if key in os.environ:
                del os.environ[key]


def test_yaml_to_env_combined():
    """Test that combined YAML config (logLevel + certbot) works correctly"""
    yaml_config = {
        "customerrors": True,
        "ssl_mode": "strict",
        "logLevel": {
            "easyhaproxy": Functions.WARN,
            "haproxy": Functions.ERROR,
        },
        "certbot": {
            "email": "combined@example.com",
            "retry_count": 5
        }
    }
    try:
        result = ContainerEnv.read(yaml_config)
        # Check the result
        assert result["customerrors"] == True
        assert result["ssl_mode"] == "strict"
        assert result["logLevel"]["easyhaproxy"] == Functions.WARN
        assert result["logLevel"]["haproxy"] == Functions.ERROR
        assert result["certbot"]["email"] == "combined@example.com"
        assert result["certbot"]["retry_count"] == 5
        # Verify environment variables
        assert os.environ.get('HAPROXY_CUSTOMERRORS') == "true"
        assert os.environ.get('EASYHAPROXY_SSL_MODE') == "strict"
        assert os.environ.get('EASYHAPROXY_LOG_LEVEL') == Functions.WARN
        assert os.environ.get('HAPROXY_LOG_LEVEL') == Functions.ERROR
        assert os.environ.get('EASYHAPROXY_CERTBOT_EMAIL') == "combined@example.com"
        assert os.environ.get('EASYHAPROXY_CERTBOT_RETRY_COUNT') == "5"
    finally:
        # Cleanup
        for key in ['HAPROXY_CUSTOMERRORS', 'EASYHAPROXY_SSL_MODE',
                    'EASYHAPROXY_LOG_LEVEL', 'HAPROXY_LOG_LEVEL',
                    'EASYHAPROXY_CERTBOT_EMAIL', 'EASYHAPROXY_CERTBOT_RETRY_COUNT']:
            if key in os.environ:
                del os.environ[key]
