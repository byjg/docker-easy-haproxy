from datetime import datetime
from multiprocessing import Process, Lock
import subprocess
import shlex
import time
import os
import re
import time

class Functions:
    HAPROXY_LOG="HAPROXY"
    EASYHAPROXY_LOG="EASYHAPROXY"
    CERTBOT_LOG="CERTBOT"
    INIT_LOG="INIT"

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
            Functions.log(source, Functions.ERROR, "%s" % (e))


class Consts:
    easyhaproxy_config = "/etc/haproxy/static/config.yml"
    haproxy_config = "/etc/haproxy/haproxy.cfg"
    custom_config_folder = "/etc/haproxy/conf.d"
    certs_letsencrypt = "/certs/letsencrypt"
    certs_haproxy = "/certs/haproxy"

class DaemonizeHAProxy:
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

    def get_haproxy_command(self, action):
        custom_config_files = ""
        if len(list(self.get_custom_config_files().keys())) != 0:
            custom_config_files = "-f %s" % (self.custom_config_folder)

        if action == "start":
            return "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg %s -p /run/haproxy.pid -S /var/run/haproxy.sock" % (custom_config_files)
        else:
            pid = "".join(Functions().run_bash(Functions.HAPROXY_LOG, "cat /run/haproxy.pid", log_output=False))
            return "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg %s -p /run/haproxy.pid -x /var/run/haproxy.sock -sf %s" % (custom_config_files, pid)

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
            Functions.log(source, Functions.ERROR, "%s" % (e))


    def __start(self):
        source = Functions.HAPROXY_LOG
        try:
            with self.process.stdout:
                for line in iter(self.process.stdout.readline, b''): 
                    Functions.log(source, Functions.INFO, line)

            returncode = self.process.wait() 
            Functions.log(source, Functions.DEBUG, "Return code %s" % (returncode))

        except Exception as e:
            Functions.log(source, Functions.ERROR, "%s" % (e))

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
    def __init__(self, certs, email, test_server):
        self.certs = certs
        self.email = email
        self.test_server = self.set_test_server(test_server)

    def set_test_server(self, test_server):
        if test_server.lower() == "staging":
            return "--staging"
        elif test_server.lower().startswith("http"):
            return "--server " + test_server
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
                host_arg = '-d %s' % (host)
                if not os.path.exists(filename):
                    Functions.log(Functions.CERTBOT_LOG, Functions.DEBUG, "Request new certificate for %s" % (host))
                    request_certs.append(host_arg)
                else:
                    creation_time = os.path.getctime(filename)
                    if (current_time - creation_time) // (24 * 3600) > 90:
                        Functions.log(Functions.CERTBOT_LOG, Functions.DEBUG, "Request expired certificate for %s" % (host))
                        request_certs.append(host_arg)
                    if (current_time - creation_time) // (24 * 3600) >= 45:
                        Functions.log(Functions.CERTBOT_LOG, Functions.DEBUG, "Renew certificate for %s" % (host))
                        renew_certs.append(host_arg)

            certbot_certonly = ('/usr/bin/certbot certonly {test_server}'
                                '    --standalone'
                                '    --preferred-challenges http'
                                '    --http-01-port 2080'
                                '    --agree-tos'
                                '    --issuance-timeout 90'
                                '    --no-eff-email'
                                '    --non-interactive'
                                '    --max-log-backups=0'
                                '    {certs} --email {email}'.format(certs = ' '.join(request_certs),
                                                           email = self.email,
                                                           test_server = self.test_server)
                            )

            ret_reload = False
            if len(request_certs) > 0:
                Functions.run_bash(Functions.CERTBOT_LOG, certbot_certonly, return_result=False)
                ret_reload = True

            if len(renew_certs) > 0:
                Functions.run_bash(Functions.CERTBOT_LOG, "/usb/bin/certbot renew", return_result=False)
                ret_reload = True

            if ret_reload:
                self.find_live_certificates()

            return ret_reload
        except Exception as e:
            Functions.log(Functions.CERTBOT_LOG, Functions.ERROR, "%s" % (e))
            return False
        
    def merge_certificate(self, cert, key, filename):
        Functions.save(filename, cert + key)
    
    def find_live_certificates(self):
        letsencrypt_certs = "/etc/letsencrypt/live/"
        if not os.path.exists(letsencrypt_certs):
            return
        for item in os.listdir(letsencrypt_certs):
            path = os.path.join(letsencrypt_certs, item)
            if os.path.isdir(path):
                cert = Functions.load(os.path.join(path, "cert.pem"))
                key = Functions.load(os.path.join(path, "privkey.pem"))
                filename = "%s/%s.pem" % (self.certs, item)
                self.merge_certificate(cert, key, filename)
