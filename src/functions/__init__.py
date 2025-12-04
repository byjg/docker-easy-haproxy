import os
import shlex
import subprocess
import sys
import psutil
import time
import logging
from datetime import datetime
from multiprocessing import Process
from typing import Final
import requests
from OpenSSL import crypto

class ContainerEnv:
    @staticmethod
    def read():
        env_vars = {
            "customerrors": True if os.getenv("HAPROXY_CUSTOMERRORS") == "true" else False,
            "ssl_mode": os.getenv("EASYHAPROXY_SSL_MODE").lower() if os.getenv("EASYHAPROXY_SSL_MODE") else 'default'
        }

        if os.getenv("HAPROXY_PASSWORD"):
            env_vars["stats"] = {
                "username": os.getenv("HAPROXY_USERNAME") if os.getenv("HAPROXY_USERNAME") else "admin",
                "password": os.getenv("HAPROXY_PASSWORD"),
                "port": os.getenv("HAPROXY_STATS_PORT") if os.getenv("HAPROXY_STATS_PORT") else "1936",
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
                    loggerCertbot.error("Could not obtain ZeroSSL credentials " + resp["error"]["type"])

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

        return env_vars


class Functions:
    HAPROXY_LOG: Final[str] = "HAPROXY"
    EASYHAPROXY_LOG: Final[str] = "EASYHAPROXY"
    CERTBOT_LOG: Final[str] = "CERTBOT"
    INIT_LOG: Final[str] = "INIT"

    TRACE: Final[str] = "TRACE"
    DEBUG: Final[str] = "DEBUG"
    INFO: Final[str] = "INFO"
    WARN: Final[str] = "WARN"
    ERROR: Final[str] = "ERROR"
    FATAL: Final[str] = "FATAL"

    @staticmethod
    def setup_log(source):
        level = os.getenv("%s_LOG_LEVEL" % (source.name.upper()), "").upper()
        level_importance = {
            Functions.TRACE: logging.DEBUG,
            Functions.DEBUG: logging.DEBUG,
            Functions.INFO: logging.INFO,
            Functions.WARN: logging.WARNING,
            Functions.ERROR: logging.ERROR,
            Functions.FATAL: logging.FATAL
        }
        selected_level = level_importance[level] if level in level_importance else logging.INFO

        log_source_handler = logging.StreamHandler(sys.stdout)
        log_source_formatter = logging.Formatter('%(name)s [%(asctime)s] %(levelname)s - %(message)s')
        log_source_handler.setFormatter(log_source_formatter)
        log_source_handler.addFilter(SingleLineNonEmptyFilter())
        source.setLevel(selected_level)
        source.addHandler(log_source_handler)
        return selected_level

    @staticmethod
    def load(filename):
        with open(filename, 'r') as content_file:
            return content_file.read()

    @staticmethod
    def save(filename, contents):
        with open(filename, 'w') as file:
            file.write(contents)

    @staticmethod
    def run_bash(log_source, command, log_output=True, return_result=True):
        if not isinstance(command, (list, tuple)):
            command = shlex.split(command)

        try:
            process = subprocess.Popen(command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       universal_newlines=True)

            output = []

            while True:
                line = process.stdout.readline().rstrip()
                error_line = process.stderr.readline().rstrip()
                output.append(line) if return_result else None
                log_source.info(line) if log_output and len(line) > 0 else None
                log_source.warning(error_line) if len(error_line) > 0 else None
                return_code = process.poll()
                if return_code is not None:
                    lines = []
                    error_line = process.stderr.readline().rstrip()
                    for line in process.stdout.readlines():
                        output.append(line.rstrip()) if return_result else None
                        lines.append(line.rstrip())
                    log_source.info(lines) if log_output and len(lines) > 0 else None
                    log_source.warning(error_line) if len(error_line) > 0 else None
                    break

            return [return_code, output]
        except Exception as e:
            log_source.error("%s" % e)
            return [-99, e]


class Consts:
    easyhaproxy_config = "/etc/haproxy/static/config.yml"
    haproxy_config = "/etc/haproxy/haproxy.cfg"
    custom_config_folder = "/etc/haproxy/conf.d"
    certs_certbot = "/certs/certbot"
    certs_haproxy = "/certs/haproxy"


class DaemonizeHAProxy:
    HAPROXY_START: Final[str] = "start"
    HAPROXY_RELOAD: Final[str] = "reload"

    def __init__(self, custom_config_folder = None):
        self.process = None
        self.thread = None
        self.sleep_secs = None
        self.custom_config_folder = custom_config_folder if custom_config_folder is not None else Consts.custom_config_folder

    def haproxy(self, action):
        self.__prepare(self.get_haproxy_command(action))

        if self.process is None:
            return

        self.thread = Process(target=self.__start, args=())
        self.thread.start()

    def get_haproxy_command(self, action, pid_file="/run/haproxy.pid"):
        custom_config_files = ""
        if len(list(self.get_custom_config_files().keys())) != 0:
            custom_config_files = "-f %s" % self.custom_config_folder

        if action == DaemonizeHAProxy.HAPROXY_START or not os.path.exists(pid_file):
            return "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg %s -p %s -S /var/run/haproxy.sock" % (custom_config_files, pid_file)
        else:
            return_code, output = Functions().run_bash(loggerHaproxy, "cat %s" % pid_file, log_output=False)
            pid = "".join(output).rstrip()
            if psutil.pid_exists(int(pid)):
                return "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg %s -p %s -x /var/run/haproxy.sock -sf %s" % (custom_config_files, pid_file, pid)
            else:
                os.unlink(pid_file)
                loggerHaproxy.warning(
                    "PID file %s does not exist. Restarting haproxy instead of reload." % pid_file
                )
                return self.get_haproxy_command(DaemonizeHAProxy.HAPROXY_START, pid_file)

    def __prepare(self, command):
        if not isinstance(command, (list, tuple)):
            command = shlex.split(command)

        try:
            loggerHaproxy.debug("HAPROXY command: %s" % command)
            self.process = subprocess.Popen(command,
                                            shell=False,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            bufsize=-1,
                                            universal_newlines=True)

        except Exception as e:
            loggerHaproxy.error("%s" % e)

    def __start(self):
        try:
            with self.process.stdout:
                for line in iter(self.process.stdout.readline, b''):
                    loggerHaproxy.info(line.rstrip())

            return_code = self.process.wait()
            loggerHaproxy.debug("Return code %s" % return_code)

        except Exception as e:
            loggerHaproxy.error("%s" % e)

    def is_alive(self):
        return self.thread.is_alive()

    def kill(self):
        self.process.kill()
        self.thread.kill()

    def terminate(self):
        self.process.terminate()
        self.thread.terminate()

    def sleep(self):
        if self.sleep_secs is None:
            try:
                self.sleep_secs = int(os.getenv("EASYHAPROXY_REFRESH_CONF", "10"))
            except ValueError:
                self.sleep_secs = 10

        time.sleep(self.sleep_secs)

    def get_custom_config_files(self):
        if not os.path.exists(self.custom_config_folder):
            return {}

        files = {}
        for file in os.listdir(self.custom_config_folder):
            if file.endswith(".cfg"):
                files[os.path.join(self.custom_config_folder, file)] = os.path.getmtime(os.path.join(self.custom_config_folder, file))
        return dict(sorted(files.items(), key=lambda t: t[0]))


class Certbot:
    def __init__(self, certs):
        env = ContainerEnv.read()

        self.certs = certs
        self.email = env["certbot"]["email"]
        self.acme_server = self.set_acme_server(env["certbot"]["server"])
        self.eab_kid = self.set_eab_kid(env["certbot"]["eab_kid"])
        self.eab_hmac_key = self.set_eab_hmac_key(env["certbot"]["eab_hmac_key"])
        self.freeze_issue = {}
        self.retry_count = env["certbot"]["retry_count"]
        self.certbot_preferred_challenges = env["certbot"]["preferred_challenges"]
        self.certbot_manual_auth_hook = env["certbot"]["manual_auth_hook"]

    @staticmethod
    def set_acme_server(acme_server):
        if not acme_server:
            return ""
        if acme_server.lower() == "staging":
            return "--staging"
        elif acme_server.lower().startswith("http"):
            return "--server " + acme_server
        else:
            return ""

    @staticmethod
    def set_eab_kid(eab_kid):
        if eab_kid != "":
            return "--eab-kid \"%s\"" % eab_kid
        else:
            return ""

    @staticmethod
    def set_eab_hmac_key(eab_hmac_key):
        if eab_hmac_key != "":
            return "--eab-hmac-key \"%s\"" % eab_hmac_key
        else:
            return ""

    def check_certificates(self, hosts):
        if self.email == "" or len(hosts) == 0:
            return False

        try:
            request_certs = []
            renew_certs = []
            for host in hosts:
                cert_status = self.get_certificate_status(host)
                host_arg = '-d %s' % host
                if cert_status == "ok" or cert_status == "error":
                    continue
                elif host in self.freeze_issue:
                    freeze_count = self.freeze_issue.pop(host, 0)
                    if freeze_count > 0:
                        loggerCertbot.debug("Waiting freezing period (%d) for %s due previous errors" % (freeze_count, host))
                        self.freeze_issue[host] = freeze_count-1
                elif cert_status == "not_found" or cert_status == "expired":
                    loggerCertbot.debug("[%s] Request new certificate for %s" % (cert_status, host))
                    request_certs.append(host_arg)
                elif cert_status == "expiring":
                    loggerCertbot.debug("[%s] Renew certificate for %s" % (cert_status, host))
                    renew_certs.append(host_arg)

            certbot_certonly = ('/usr/bin/certbot certonly {acme_server}'
                                '    --preferred-challenges {challenge}'
                                '    --agree-tos'
                                '    --issuance-timeout 90'
                                '    --no-eff-email'
                                '    --non-interactive'
                                '    --max-log-backups=0'
                                '    {eab_kid} {eab_hmac_key}'
                                '    {certs} --email {email}'.format(eab_kid=self.eab_kid,
                                                                     eab_hmac_key=self.eab_hmac_key,
                                                                     certs=' '.join(request_certs),
                                                                     email=self.email,
                                                                     challenge=self.certbot_preferred_challenges,
                                                                     acme_server=self.acme_server)
                                )

            if 'http' in self.certbot_preferred_challenges:
                certbot_certonly += ('    --http-01-port 2080'
                                     '    --standalone'
                                    )

            if self.certbot_manual_auth_hook:
                certbot_certonly += '    --manual --manual-auth-hook \'{hook}\''.format(hook=self.certbot_manual_auth_hook)

            if loggerCertbot.level == logging.DEBUG:
                certbot_certonly += '    -v'

            loggerCertbot.debug("certbot_certonly: %s" % certbot_certonly)

            ret_reload = False
            return_code_issue = 0
            return_code_renew = 0
            if len(request_certs) > 0:
                return_code_issue, output = Functions.run_bash(loggerCertbot, certbot_certonly, return_result=False)
                ret_reload = True

            if len(renew_certs) > 0:
                return_code_renew, output = Functions.run_bash(loggerCertbot, "/usr/bin/certbot renew", return_result=False)
                ret_reload = True

            if ret_reload:
                self.find_live_certificates()

            if return_code_issue != 0:
                self.find_missing_certificates(request_certs)
            if return_code_renew != 0:
                self.find_missing_certificates(renew_certs)

            return ret_reload
        except Exception as e:
            loggerCertbot.error("%s" % e)
            return False

    @staticmethod
    def merge_certificate(cert, key, filename):
        Functions.save(filename, cert + key)

    def find_live_certificates(self):
        certbot_certs = "/etc/letsencrypt/live/"
        if not os.path.exists(certbot_certs):
            return
        for item in os.listdir(certbot_certs):
            path = os.path.join(certbot_certs, item)
            if os.path.isdir(path):
                cert = Functions.load(os.path.join(path, "cert.pem"))
                key = Functions.load(os.path.join(path, "privkey.pem"))
                filename = "%s/%s.pem" % (self.certs, item)
                self.merge_certificate(cert, key, filename)

    def get_certificate_status(self, host):
        current_time = time.time()
        filename = "%s/%s.pem" % (self.certs, host)
        if not os.path.exists(filename):
            return "not_found"

        try:
            with open(filename, 'rb') as file:
                certificate_str = file.read()
            certificate = crypto.load_certificate(crypto.FILETYPE_PEM, certificate_str)
            expiration_after = datetime.strptime(certificate.get_notAfter().decode()[:-1], '%Y%m%d%H%M%S').timestamp()
            if current_time >= expiration_after:
                return "expired"
            elif (expiration_after - current_time) // (24 * 3600) <= 15:
                return "expiring"
        except Exception as e:
            loggerCertbot.error("Certificate %s error %s" % (host, e))
            return "error"

        return "ok"

    def find_missing_certificates(self, hosts):
        for host in hosts:
            if host.startswith("-d "):
                host = host[3:]
            cert_status = self.get_certificate_status(host)
            if cert_status != "ok":
                self.freeze_issue[host] = self.retry_count
                loggerCertbot.debug("Freeze issuing ssl for %s due failure. The certificate is %s" % (host, cert_status))



class SingleLineNonEmptyFilter(logging.Filter):
    """
    Logging filter that ensures messages are single-line and non-empty.
    - Collapses newlines into spaces and strips surrounding whitespace.
    - Drops the record if the resulting message is empty.
    """
    def filter(self, record: logging.LogRecord) -> int:
        try:
            msg = record.getMessage()
        except Exception:
            # If formatting fails, drop the record
            return 0

        # Convert any non-string to string representation
        if not isinstance(msg, str):
            msg = str(msg)

        # Collapse multi-line to single line and trim
        sanitized = " ".join(msg.splitlines()).strip()

        if sanitized == "":
            return 0

        # If we changed the message, update the record and clear args
        if sanitized != record.getMessage():
            record.msg = sanitized
            record.args = ()
        return 1


# ####################################################################################################################
# Setup Global Log
loggerInit = logging.getLogger(Functions.INIT_LOG)
loggerHaproxy = logging.getLogger(Functions.HAPROXY_LOG)
loggerEasyHaproxy = logging.getLogger(Functions.EASYHAPROXY_LOG)
loggerCertbot = logging.getLogger(Functions.CERTBOT_LOG)
Functions.setup_log(loggerInit)
Functions.setup_log(loggerHaproxy)
Functions.setup_log(loggerEasyHaproxy)
Functions.setup_log(loggerCertbot)
