import os

import requests

from .functions import Functions
from .loggers import logger_certbot


class ContainerEnv:
    @staticmethod
    def read(yaml_config=None):
        """
        Read configuration from environment variables, optionally merged with YAML config.

        Args:
            yaml_config: Optional dict from YAML file (for static mode). YAML values take precedence.

        Returns:
            Dict with configuration settings
        """
        # Convert YAML config to environment variables first (if provided)
        if yaml_config:
            ContainerEnv._yaml_to_env(yaml_config)

        env_vars = {
            "customerrors": True if os.getenv("HAPROXY_CUSTOMERRORS") == "true" else False,
            "ssl_mode": os.getenv("EASYHAPROXY_SSL_MODE").lower() if os.getenv("EASYHAPROXY_SSL_MODE") else 'default'
        }

        if os.getenv("HAPROXY_PASSWORD"):
            env_vars["stats"] = {
                "username": os.getenv("HAPROXY_USERNAME") if os.getenv("HAPROXY_USERNAME") else "admin",
                "password": os.getenv("HAPROXY_PASSWORD"),
                "port": os.getenv("HAPROXY_STATS_PORT") if os.getenv("HAPROXY_STATS_PORT") else "1936",
                "cors_origin": os.getenv("HAPROXY_STATS_CORS_ORIGIN", ""),
            }

        env_vars["lookup_label"] = os.getenv("EASYHAPROXY_LABEL_PREFIX") if os.getenv(
            "EASYHAPROXY_LABEL_PREFIX") else "easyhaproxy"

        env_vars["logLevel"] = {
            "easyhaproxy": os.getenv("EASYHAPROXY_LOG_LEVEL") if os.getenv(
                "EASYHAPROXY_LOG_LEVEL") else Functions.DEBUG,
            "haproxy": os.getenv("HAPROXY_LOG_LEVEL") if os.getenv("HAPROXY_LOG_LEVEL") else Functions.INFO,
            "certbot": os.getenv("CERTBOT_LOG_LEVEL") if os.getenv("CERTBOT_LOG_LEVEL") else Functions.DEBUG,
        }

        env_vars["certbot"] = {
            "autoconfig": os.getenv("EASYHAPROXY_CERTBOT_AUTOCONFIG", ""),
            "email": os.getenv("EASYHAPROXY_CERTBOT_EMAIL", ""),
            "server": os.getenv("EASYHAPROXY_CERTBOT_SERVER", False),
            "eab_kid": os.getenv("EASYHAPROXY_CERTBOT_EAB_KID", ""),
            "eab_hmac_key": os.getenv("EASYHAPROXY_CERTBOT_EAB_HMAC_KEY", ""),
            "retry_count": int(os.getenv("EASYHAPROXY_CERTBOT_RETRY_COUNT", 60)),
            "preferred_challenges": os.getenv("EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES", "http"),
            "manual_auth_hook": os.getenv("EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK", False),
        }

        if env_vars["certbot"]["autoconfig"] != "" and not env_vars["certbot"]["server"] and env_vars["certbot"]["email"] != "":
            if env_vars["certbot"]["autoconfig"] == "letsencrypt":
                env_vars["certbot"]["server"] = "https://acme-v02.api.letsencrypt.org/directory"

            if env_vars["certbot"]["autoconfig"] == "letsencrypt_test":
                env_vars["certbot"]["server"] = "https://acme-staging-v02.api.letsencrypt.org/directory"

            if env_vars["certbot"]["autoconfig"] == "buypass":
                env_vars["certbot"]["server"] = "https://api.buypass.com/acme/directory"

            if env_vars["certbot"]["autoconfig"] == "buypass_test":
                env_vars["certbot"]["server"] = "https://api.test4.buypass.no/acme/directory"

            if env_vars["certbot"]["autoconfig"] == "sslcom_rca":
                env_vars["certbot"]["server"] = "https://acme.ssl.com/sslcom-dv-rsa"

            if env_vars["certbot"]["autoconfig"] == "sslcom_ecc":
                env_vars["certbot"]["server"] = "https://acme.ssl.com/sslcom-dv-ecc"

            if env_vars["certbot"]["autoconfig"] == "google":
                env_vars["certbot"]["server"] = "https://dv.acme-v02.api.pki.goog/directory"

            if env_vars["certbot"]["autoconfig"] == "google_test":
                env_vars["certbot"]["server"] = "https://dv.acme-v02.test-api.pki.goog/directory"

            if env_vars["certbot"]["autoconfig"] == "zerossl":
                url = "https://api.zerossl.com/acme/eab-credentials-email"
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
                data = "email=" + env_vars["certbot"]["email"]
                resp = requests.post(url, headers=headers, data=data).json()

                if resp["success"]:
                    env_vars["certbot"]["server"] = "https://acme.zerossl.com/v2/DV90"
                    env_vars["certbot"]["eab_kid"] = os.environ['EASYHAPROXY_CERTBOT_EAB_KID'] = resp["eab_kid"]
                    env_vars["certbot"]["eab_hmac_key"] = os.environ['EASYHAPROXY_CERTBOT_EAB_HMAC_KEY'] = resp["eab_hmac_key"]
                else:
                    del os.environ["EASYHAPROXY_CERTBOT_EMAIL"]
                    logger_certbot.error("Could not obtain ZeroSSL credentials " + resp["error"]["type"])

            os.environ['EASYHAPROXY_CERTBOT_SERVER'] = env_vars["certbot"]["server"]

        # Plugin configuration
        env_vars["plugins"] = {
            "abort_on_error": os.getenv("EASYHAPROXY_PLUGINS_ABORT_ON_ERROR", "false").lower() == "true",
            "enabled": os.getenv("EASYHAPROXY_PLUGINS_ENABLED", "").split(",") if os.getenv("EASYHAPROXY_PLUGINS_ENABLED") else [],
            "config": {}  # Individual plugin configs from env vars
        }

        # Parse individual plugin configs (e.g., EASYHAPROXY_PLUGIN_CLOUDFLARE_*)
        for key, value in os.environ.items():
            if key.startswith("EASYHAPROXY_PLUGIN_"):
                parts = key.split("_", 3)  # ['EASYHAPROXY', 'PLUGIN', 'NAME', 'KEY']
                if len(parts) >= 4:
                    plugin_name = parts[2].lower()
                    config_key = "_".join(parts[3:]).lower()
                    env_vars["plugins"]["config"].setdefault(plugin_name, {})
                    env_vars["plugins"]["config"][plugin_name][config_key] = value

        # Ingress status update configuration
        env_vars["update_ingress_status"] = os.getenv("EASYHAPROXY_UPDATE_INGRESS_STATUS", "true").lower() == "true"
        env_vars["deployment_mode"] = os.getenv("EASYHAPROXY_DEPLOYMENT_MODE", "auto")
        env_vars["external_hostname"] = os.getenv("EASYHAPROXY_EXTERNAL_HOSTNAME", "")
        env_vars["ingress_status_update_interval"] = int(os.getenv("EASYHAPROXY_STATUS_UPDATE_INTERVAL", "30"))

        return env_vars

    @staticmethod
    def _yaml_to_env(yaml_config):
        """Convert YAML configuration to environment variables"""

        # Convert customerrors
        if 'customerrors' in yaml_config:
            os.environ['HAPROXY_CUSTOMERRORS'] = 'true' if yaml_config['customerrors'] else 'false'

        # Convert ssl_mode
        if 'ssl_mode' in yaml_config:
            os.environ['EASYHAPROXY_SSL_MODE'] = str(yaml_config['ssl_mode'])

        # Convert stats
        if 'stats' in yaml_config:
            stats = yaml_config['stats']
            if 'username' in stats:
                os.environ['HAPROXY_USERNAME'] = str(stats['username'])
            if 'password' in stats:
                os.environ['HAPROXY_PASSWORD'] = str(stats['password'])
            if 'port' in stats:
                os.environ['HAPROXY_STATS_PORT'] = str(stats['port'])
            if 'cors_origin' in stats:
                os.environ['HAPROXY_STATS_CORS_ORIGIN'] = str(stats['cors_origin'])

        # Convert logLevel
        if 'logLevel' in yaml_config:
            log_level = yaml_config['logLevel']
            for source, level in log_level.items():
                os.environ[source.upper() + '_LOG_LEVEL'] = str(level)

        # Convert certbot
        if 'certbot' in yaml_config:
            certbot = yaml_config['certbot']
            for config, value in certbot.items():
                os.environ['EASYHAPROXY_CERTBOT_' + config.upper()] = str(value)

        # Convert plugins
        if 'plugins' in yaml_config:
            plugins = yaml_config['plugins']

            # Convert enabled list
            if 'enabled' in plugins:
                enabled_list = plugins['enabled'] if isinstance(plugins['enabled'], list) else [plugins['enabled']]
                os.environ['EASYHAPROXY_PLUGINS_ENABLED'] = ','.join(enabled_list)

            # Convert abort_on_error
            if 'abort_on_error' in plugins:
                os.environ['EASYHAPROXY_PLUGINS_ABORT_ON_ERROR'] = 'true' if plugins['abort_on_error'] else 'false'

            # Convert plugin configs
            if 'config' in plugins:
                for plugin_name, plugin_config in plugins['config'].items():
                    for config_key, config_value in plugin_config.items():
                        # Convert to env var format: EASYHAPROXY_PLUGIN_<NAME>_<KEY>
                        env_key = f"EASYHAPROXY_PLUGIN_{plugin_name.upper()}_{config_key.upper()}"

                        # Convert list values to comma-separated strings
                        if isinstance(config_value, list):
                            env_value = ','.join(str(v) for v in config_value)
                        else:
                            env_value = str(config_value)

                        os.environ[env_key] = env_value