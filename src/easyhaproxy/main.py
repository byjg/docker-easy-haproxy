import argparse
import os
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from deepdiff import DeepDiff

from functions import (
    Certbot,
    Consts,
    DaemonizeHAProxy,
    Functions,
    logger_easyhaproxy,
    logger_init,
)
from processor import ProcessorInterface


class DashboardHandler(BaseHTTPRequestHandler):
    _content: bytes | None = None

    def do_GET(self):
        if self.path in ("/", "/index.html", "/dashboard.html"):
            if DashboardHandler._content is None:
                dashboard_path = os.path.join(Consts.www_path, "dashboard.html")
                try:
                    with open(dashboard_path, "rb") as f:
                        DashboardHandler._content = f.read()
                except OSError:
                    DashboardHandler._content = b""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(DashboardHandler._content)))
            self.end_headers()
            self.wfile.write(DashboardHandler._content)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_dashboard_server():
    server = HTTPServer(("127.0.0.1", Consts.DASHBOARD_SERVER_PORT), DashboardHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger_easyhaproxy.info(f"Dashboard server listening on 127.0.0.1:{Consts.DASHBOARD_SERVER_PORT}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="easy-haproxy",
        description="HAProxy label-based routing with service discovery for Docker, Swarm, and Kubernetes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Core
    parser.add_argument("--discover", metavar="MODE",
                        choices=["static", "docker", "swarm", "kubernetes"],
                        help="Service discovery mode. Also set by EASYHAPROXY_DISCOVER.")
    parser.add_argument("--base-path", metavar="PATH",
                        help="Base directory for all EasyHAProxy files. Also set by EASYHAPROXY_BASE_PATH.")
    parser.add_argument("--label-prefix", metavar="PREFIX",
                        help="Label/annotation prefix used to discover services. Also set by EASYHAPROXY_LABEL_PREFIX.")
    parser.add_argument("--ssl-mode", metavar="MODE",
                        choices=["strict", "default", "loose"],
                        help="TLS policy: strict (TLS 1.3 only), default, or loose (all). Also set by EASYHAPROXY_SSL_MODE.")
    parser.add_argument("--refresh-conf", metavar="SECONDS", type=int,
                        help="Interval in seconds to poll for configuration changes. Also set by EASYHAPROXY_REFRESH_CONF.")
    parser.add_argument("--customer-errors", metavar="BOOL",
                        choices=["true", "false"],
                        help="Enable custom HAProxy HTML error pages. Also set by HAPROXY_CUSTOMERRORS.")

    # Logging
    log_levels = ["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
    parser.add_argument("--log-level", metavar="LEVEL", choices=log_levels,
                        help="EasyHAProxy log level. Also set by EASYHAPROXY_LOG_LEVEL.")
    parser.add_argument("--haproxy-log-level", metavar="LEVEL", choices=log_levels,
                        help="HAProxy process log level. Also set by HAPROXY_LOG_LEVEL.")
    parser.add_argument("--certbot-log-level", metavar="LEVEL", choices=log_levels,
                        help="Certbot log level. Also set by CERTBOT_LOG_LEVEL.")

    # Stats
    parser.add_argument("--haproxy-password", metavar="PASSWORD",
                        help="Enable HAProxy stats dashboard with this password. Also set by HAPROXY_PASSWORD.")
    parser.add_argument("--haproxy-username", metavar="USERNAME",
                        help="HAProxy stats dashboard username. Also set by HAPROXY_USERNAME.")
    parser.add_argument("--haproxy-stats-port", metavar="PORT",
                        help="HAProxy stats dashboard port. Also set by HAPROXY_STATS_PORT.")
    parser.add_argument("--haproxy-stats-cors-origin", metavar="ORIGIN",
                        help="Allowed CORS origin for the stats dashboard. Also set by HAPROXY_STATS_CORS_ORIGIN.")

    # ACME / Certbot
    parser.add_argument("--certbot-email", metavar="EMAIL",
                        help="Contact email for ACME/Let's Encrypt. Enables certbot when set. Also set by EASYHAPROXY_CERTBOT_EMAIL.")
    parser.add_argument("--certbot-autoconfig", metavar="CA",
                        choices=["letsencrypt", "letsencrypt_test", "buypass", "buypass_test",
                                 "sslcom_rca", "sslcom_ecc", "google", "google_test", "zerossl"],
                        help="Shorthand to configure a well-known ACME CA. Also set by EASYHAPROXY_CERTBOT_AUTOCONFIG.")
    parser.add_argument("--certbot-server", metavar="URL",
                        help="Custom ACME server directory URL. Also set by EASYHAPROXY_CERTBOT_SERVER.")
    parser.add_argument("--certbot-eab-kid", metavar="KID",
                        help="External Account Binding key ID (required by some CAs). Also set by EASYHAPROXY_CERTBOT_EAB_KID.")
    parser.add_argument("--certbot-eab-hmac-key", metavar="KEY",
                        help="External Account Binding HMAC key. Also set by EASYHAPROXY_CERTBOT_EAB_HMAC_KEY.")
    parser.add_argument("--certbot-retry-count", metavar="N", type=int,
                        help="Iterations before retrying after a rate limit. Also set by EASYHAPROXY_CERTBOT_RETRY_COUNT.")
    parser.add_argument("--certbot-preferred-challenges", metavar="TYPE",
                        help="ACME challenge type (default: http). Also set by EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES.")
    parser.add_argument("--certbot-manual-auth-hook", metavar="SCRIPT",
                        help="Path to manual auth hook script for certbot. Also set by EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK.")

    # Plugins
    parser.add_argument("--plugins-enabled", metavar="LIST",
                        help="Comma-separated list of plugins to enable. Also set by EASYHAPROXY_PLUGINS_ENABLED.")
    parser.add_argument("--plugins-abort-on-error", metavar="BOOL",
                        choices=["true", "false"],
                        help="Abort startup if a plugin fails to load. Also set by EASYHAPROXY_PLUGINS_ABORT_ON_ERROR.")

    # Kubernetes
    parser.add_argument("--update-ingress-status", metavar="BOOL",
                        choices=["true", "false"],
                        help="Update Kubernetes Ingress status with load-balancer IP. Also set by EASYHAPROXY_UPDATE_INGRESS_STATUS.")
    parser.add_argument("--deployment-mode", metavar="MODE",
                        choices=["auto", "single", "cluster"],
                        help="Kubernetes deployment mode. Also set by EASYHAPROXY_DEPLOYMENT_MODE.")
    parser.add_argument("--external-hostname", metavar="HOSTNAME",
                        help="External hostname reported in Ingress status. Also set by EASYHAPROXY_EXTERNAL_HOSTNAME.")
    parser.add_argument("--ingress-status-update-interval", metavar="SECONDS", type=int,
                        help="Interval in seconds to update Ingress status. Also set by EASYHAPROXY_STATUS_UPDATE_INTERVAL.")

    return parser


def _apply_args_to_env(args: argparse.Namespace) -> None:
    """Write non-None CLI arguments into os.environ so the rest of the code reads them."""
    mapping = {
        "discover":                        "EASYHAPROXY_DISCOVER",
        "base_path":                       "EASYHAPROXY_BASE_PATH",
        "label_prefix":                    "EASYHAPROXY_LABEL_PREFIX",
        "ssl_mode":                        "EASYHAPROXY_SSL_MODE",
        "refresh_conf":                    "EASYHAPROXY_REFRESH_CONF",
        "customer_errors":                 "HAPROXY_CUSTOMERRORS",
        "log_level":                       "EASYHAPROXY_LOG_LEVEL",
        "haproxy_log_level":               "HAPROXY_LOG_LEVEL",
        "certbot_log_level":               "CERTBOT_LOG_LEVEL",
        "haproxy_password":                "HAPROXY_PASSWORD",
        "haproxy_username":                "HAPROXY_USERNAME",
        "haproxy_stats_port":              "HAPROXY_STATS_PORT",
        "haproxy_stats_cors_origin":       "HAPROXY_STATS_CORS_ORIGIN",
        "certbot_email":                   "EASYHAPROXY_CERTBOT_EMAIL",
        "certbot_autoconfig":              "EASYHAPROXY_CERTBOT_AUTOCONFIG",
        "certbot_server":                  "EASYHAPROXY_CERTBOT_SERVER",
        "certbot_eab_kid":                 "EASYHAPROXY_CERTBOT_EAB_KID",
        "certbot_eab_hmac_key":            "EASYHAPROXY_CERTBOT_EAB_HMAC_KEY",
        "certbot_retry_count":             "EASYHAPROXY_CERTBOT_RETRY_COUNT",
        "certbot_preferred_challenges":    "EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES",
        "certbot_manual_auth_hook":        "EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK",
        "plugins_enabled":                 "EASYHAPROXY_PLUGINS_ENABLED",
        "plugins_abort_on_error":          "EASYHAPROXY_PLUGINS_ABORT_ON_ERROR",
        "update_ingress_status":           "EASYHAPROXY_UPDATE_INGRESS_STATUS",
        "deployment_mode":                 "EASYHAPROXY_DEPLOYMENT_MODE",
        "external_hostname":               "EASYHAPROXY_EXTERNAL_HOSTNAME",
        "ingress_status_update_interval":  "EASYHAPROXY_STATUS_UPDATE_INTERVAL",
    }
    for arg_name, env_name in mapping.items():
        value = getattr(args, arg_name, None)
        if value is not None:
            os.environ[env_name] = str(value)


def start():
    processor_obj = ProcessorInterface.factory(os.getenv("EASYHAPROXY_DISCOVER"))
    if processor_obj is None:
        exit(1)

    os.makedirs(Consts.certs_certbot, exist_ok=True)
    os.makedirs(Consts.certs_haproxy, exist_ok=True)

    start_dashboard_server()

    processor_obj.save_config(Consts.haproxy_config)
    processor_obj.save_certs(Consts.certs_haproxy)
    certbot_certs_found = processor_obj.get_certbot_hosts()
    logger_easyhaproxy.info(f'Found hosts: {", ".join(processor_obj.get_hosts())}')  # Needs to run after save_config
    logger_easyhaproxy.debug(f'Object Found: {processor_obj.get_parsed_object()}')

    old_haproxy = None
    haproxy = DaemonizeHAProxy()
    current_custom_config_files = haproxy.get_custom_config_files()
    haproxy.haproxy(DaemonizeHAProxy.HAPROXY_START)
    haproxy.sleep()

    certbot = Certbot(Consts.certs_certbot)

    # Check ACME environment readiness if Certbot is configured
    if certbot.email != "":
        is_ready, error_msg = Certbot.check_acme_environment_ready(certbot.email, certbot.acme_server)
        if not is_ready:
            logger_easyhaproxy.warning(f"ACME environment not ready: {error_msg}")
            logger_easyhaproxy.warning("Certificate auto-renewal may fail. Verify ACME server configuration.")
        else:
            logger_easyhaproxy.info("ACME environment validated and ready")

    while True:
        if old_haproxy is not None:
            old_haproxy.kill()
            old_haproxy = None
        try:
            old_parsed = processor_obj.get_parsed_object()
            processor_obj.refresh()
            if certbot.check_certificates(certbot_certs_found) or DeepDiff(old_parsed, processor_obj.get_parsed_object()) != {} or not haproxy.is_alive() or DeepDiff(current_custom_config_files, haproxy.get_custom_config_files()) != {}:
                logger_easyhaproxy.info('New configuration found. Reloading...')
                logger_easyhaproxy.debug(f'Object Found: {processor_obj.get_parsed_object()}')
                processor_obj.save_config(Consts.haproxy_config)
                processor_obj.save_certs(Consts.certs_haproxy)
                certbot_certs_found = processor_obj.get_certbot_hosts()
                logger_easyhaproxy.info(f'Found hosts: {", ".join(processor_obj.get_hosts())}')  # Needs to after save_config
                old_haproxy = haproxy
                haproxy = DaemonizeHAProxy()
                current_custom_config_files = haproxy.get_custom_config_files()
                haproxy.haproxy(DaemonizeHAProxy.HAPROXY_RELOAD)
                old_haproxy.terminate()

        except Exception as e:
            logger_easyhaproxy.fatal(f"Err: {e}")

        logger_easyhaproxy.info('Heartbeat')
        haproxy.sleep()


def main():
    haproxy_bin = shutil.which('haproxy')
    if haproxy_bin is None:
        print("ERROR: HAProxy is not installed or not in PATH.")
        print("Please install HAProxy before running easy-haproxy.")
        print("  Debian/Ubuntu: sudo apt install haproxy")
        print("  RHEL/Fedora:   sudo dnf install haproxy")
        print("  macOS:         brew install haproxy")
        sys.exit(1)

    args = _build_parser().parse_args()
    _apply_args_to_env(args)

    # Reset cached base_path so it re-evaluates after --base-path may have been applied
    Consts.reset()

    Functions.run_bash(logger_init, f'{haproxy_bin} -v')

    logger_init.info(r".........................__.....................................")
    logger_init.info(r"..___  ____ ________  __/ /_  ____ _____  _________  _  ____  __")
    logger_init.info(r"./ _ \/ __ `/ ___/ / / / __ \/ __ `/ __ \/ ___/ __ \| |/_/ / / /")
    logger_init.info(r"/  __/ /_/ (__  ) /_/ / / / / /_/ / /_/ / /  / /_/ />  </ /_/ /.")
    logger_init.info(r"\___/\__,_/____/\__, /_/ /_/\__,_/ .___/_/   \____/_/|_|\__, /..")
    logger_init.info(r".............../____/.........../_/..................../____/...")

    logger_init.info(f"Release: {os.getenv('RELEASE_VERSION')}")
    logger_init.debug('Environment:')
    for name, value in os.environ.items():
        if "HAPROXY" in name:
            logger_init.debug(f"- {name}: {value}")

    start()


if __name__ == '__main__':
    main()