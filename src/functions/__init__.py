import os
import shlex
import subprocess
import time
from datetime import datetime
from multiprocessing import Process

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

        env_vars["certbot"] = {
            "email": os.getenv("EASYHAPROXY_CERTBOT_EMAIL", ""),
            "server": os.getenv("EASYHAPROXY_CERTBOT_SERVER", False),
            "eab_kid": os.getenv("EASYHAPROXY_CERTBOT_EAB_KID", ""),
            "eab_hmac_key": os.getenv("EASYHAPROXY_CERTBOT_EAB_HMAC_KEY", ""),
        }

        return env_vars


class Functions:
    HAPROXY_LOG = "HAPROXY"
    EASYHAPROXY_LOG = "EASYHAPROXY"
    CERTBOT_LOG = "CERTBOT"
    INIT_LOG = "INIT"

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"

    debug_log = None

    @staticmethod
    def skip_log(source, log_level_str):
        level = os.getenv("%s_LOG_LEVEL" % (source.upper()), "").upper()
        level_importance = {
            Functions.TRACE: 0,
            Functions.DEBUG: 1,
            Functions.INFO: 2,
            Functions.WARN: 3,
            Functions.ERROR: 4,
            Functions.FATAL: 5
        }
        level_required = 1 if level not in level_importance else level_importance[level]
        level_asked = 1 if log_level_str.upper() not in level_importance else level_importance[log_level_str.upper()]
        return level_asked < level_required

    @staticmethod
    def load(filename):
        with open(filename, 'r') as content_file:
            return content_file.read()

    @staticmethod
    def save(filename, contents):
        with open(filename, 'w') as file:
            file.write(contents)

    @staticmethod
    def log(source, level, message):
        if message is None or message == "":
            return

        if Functions.skip_log(source, level):
            return

        if not isinstance(message, (list, tuple)):
            message = [message]

        for line in message:
            log = "[%s] %s [%s]: %s" % (source, datetime.now().strftime("%x %X"), level, line.rstrip())
            print(log)
            if Functions.debug_log is not None:
                Functions.debug_log.append(log)

    @staticmethod
    def run_bash(source, command, log_output=True, return_result=True):
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
                output.append(line) if return_result else None
                Functions.log(source, Functions.INFO, line) if log_output else None
                Functions.log(source, Functions.WARN, process.stderr.readline())
                return_code = process.poll()
                if return_code is not None:
                    lines = []
                    for line in process.stdout.readlines():
                        output.append(line.rstrip()) if return_result else None
                        lines.append(line.rstrip())
                    Functions.log(source, Functions.INFO, lines) if log_output else None
                    Functions.log(source, Functions.WARN, process.stderr.readlines())
                    break

            return output
        except Exception as e:
            Functions.log(source, Functions.ERROR, "%s" % e)


class Consts:
    easyhaproxy_config = "/etc/haproxy/static/config.yml"
    haproxy_config = "/etc/haproxy/haproxy.cfg"
    certs_certbot = "/certs/certbot"
    certs_haproxy = "/certs/haproxy"


class DaemonizeHAProxy:
    def __init__(self):
        self.process = None
        self.thread = None
        self.sleep_secs = None

    def haproxy(self, action):
        if action == "start":
            self.__prepare(
                "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -S /var/run/haproxy.sock")
        else:
            pid = "".join(Functions().run_bash(Functions.HAPROXY_LOG, "cat /run/haproxy.pid", log_output=False))
            self.__prepare(
                "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -x /var/run/haproxy.sock -sf %s" %
                pid)

        if self.process is None:
            return

        self.thread = Process(target=self.__start, args=())
        self.thread.start()

    def __prepare(self, command):
        source = Functions.HAPROXY_LOG
        if not isinstance(command, (list, tuple)):
            command = shlex.split(command)

        try:
            self.process = subprocess.Popen(command,
                                            shell=False,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            bufsize=-1,
                                            universal_newlines=True)

        except Exception as e:
            Functions.log(source, Functions.ERROR, "%s" % e)

    def __start(self):
        source = Functions.HAPROXY_LOG
        try:
            with self.process.stdout:
                for line in iter(self.process.stdout.readline, b''):
                    Functions.log(source, Functions.INFO, line)

            return_code = self.process.wait()
            Functions.log(source, Functions.DEBUG, "Return code %s" % return_code)

        except Exception as e:
            Functions.log(source, Functions.ERROR, "%s" % e)

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


class Certbot:
    def __init__(self, certs):
        env = ContainerEnv.read()

        self.certs = certs
        self.email = env["certbot"]["email"]
        self.acme_server = self.set_acme_server(env["certbot"]["server"])
        self.eab_kid = self.set_eab_kid(env["certbot"]["eab_kid"])
        self.eab_hmac_key = self.set_eab_hmac_key(env["certbot"]["eab_hmac_key"])

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
            current_time = time.time()
            for host in hosts:
                filename = "%s/%s.pem" % (self.certs, host)
                host_arg = '-d %s' % host
                if not os.path.exists(filename):
                    Functions.log(Functions.CERTBOT_LOG, Functions.DEBUG, "Request new certificate for %s" % host)
                    request_certs.append(host_arg)
                else:
                    try:
                        with open(filename, 'rb') as file:
                            certificate_str = file.read()
                        certificate = crypto.load_certificate(crypto.FILETYPE_PEM, certificate_str)
                        expiration_after = datetime.strptime(certificate.get_notAfter().decode()[:-1],
                                                             '%Y%m%d%H%M%S').timestamp()

                        if current_time >= expiration_after:
                            Functions.log(Functions.CERTBOT_LOG, Functions.DEBUG,
                                          "Request expired certificate for %s" % host)
                            request_certs.append(host_arg)
                        if (expiration_after - current_time) // (24 * 3600) <= 15:
                            Functions.log(Functions.CERTBOT_LOG, Functions.DEBUG, "Renew certificate for %s" % host)
                            renew_certs.append(host_arg)
                    except Exception as e:
                        Functions.log(Functions.CERTBOT_LOG, Functions.ERROR, "Certificate %s error %s" % (host, e))

            certbot_certonly = ('/usr/bin/certbot certonly {acme_server}'
                                '    --standalone'
                                '    --preferred-challenges http'
                                '    --http-01-port 2080'
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
                                                                     acme_server=self.acme_server)
                                )

            ret_reload = False
            if len(request_certs) > 0:
                Functions.run_bash(Functions.CERTBOT_LOG, certbot_certonly, return_result=False)
                ret_reload = True

            if len(renew_certs) > 0:
                Functions.run_bash(Functions.CERTBOT_LOG, "/usr/bin/certbot renew", return_result=False)
                ret_reload = True

            if ret_reload:
                self.find_live_certificates()

            return ret_reload
        except Exception as e:
            Functions.log(Functions.CERTBOT_LOG, Functions.ERROR, "%s" % e)
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
