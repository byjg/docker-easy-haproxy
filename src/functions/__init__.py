from datetime import datetime
from multiprocessing import Process, Lock
import subprocess
import shlex
import time
import os

class Functions:
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

        if not isinstance(message, (list, tuple)):
            message = [message]
        
        for line in message:
            print("[%s] %s [%s]: %s" % (source, datetime.now().strftime("%x %X"), level, line.rstrip()))

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
                Functions.log(source, "info", line) if log_output else None
                Functions.log(source, "warning", process.stderr.readline())
                return_code = process.poll()
                if return_code is not None:
                    lines = []
                    for line in process.stdout.readlines():
                        output.append(line.rstrip()) if return_result else None
                        lines.append(line.rstrip())
                    Functions.log(source, "info", lines) if log_output else None
                    Functions.log(source, "warning", process.stderr.readlines())
                    break

            return output
        except Exception as e:
            Functions.log(source, 'error', "%s" % (e))


class DaemonizeHAProxy:
    def __init__(self):
        self.process = None
        self.thread = None

    def haproxy(self, action):
        if action == "start":
            self.__prepare("/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -S /var/run/haproxy.sock")
        else:
            pid = "".join(Functions().run_bash("HAPROXY", "cat /run/haproxy.pid", log_output=False))
            self.__prepare("/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -x /var/run/haproxy.sock -sf %s" % (pid))

        if self.process is None:
            return

        self.thread = Process(target=self.__start, args=())
        self.thread.start()

    def __prepare(self, command):
        source = "HAPROXY"
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
            Functions.log(source, 'error', "%s" % (e))


    def __start(self):
        source = "HAPROXY"
        try:
            with self.process.stdout:
                for line in iter(self.process.stdout.readline, b''): 
                    Functions.log(source, "info", line)

            returncode = self.process.wait() 
            Functions.log(source, "info", "Return code %s" % (returncode))

        except Exception as e:
            Functions.log(source, 'error', "%s" % (e))

    def is_alive(self):
        return self.thread.is_alive()

    def kill(self):
        self.process.kill()
        self.thread.kill()

    def terminate(self):
        self.process.terminate()
        self.thread.terminate()


class Certbot:
    def __init__(self, certs, email):
        self.certs = certs
        self.email = email

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
                    Functions.log("CERTBOT", "info", "Request new certificate for %s" % (host))
                    request_certs.append(host_arg)
                else:
                    creation_time = os.path.getctime(filename)
                    if (current_time - creation_time) // (24 * 3600) > 90:
                        Functions.log("CERTBOT", "info", "Request expired certificate for %s" % (host))
                        request_certs.append(host_arg)
                    if (current_time - creation_time) // (24 * 3600) >= 45:
                        Functions.log("CERTBOT", "info", "Renew certificate for %s" % (host))
                        renew_certs.append(host_arg)

            certbot_certonly = ('/usr/bin/certbot certonly '
                                '    --standalone'
                                '    --preferred-challenges http'
                                '    --http-01-port 2080'
                                '    --agree-tos'
                                '    --issuance-timeout 90'
                                '    --no-eff-email'
                                '    --non-interactive'
                                '    --max-log-backups=0'
                                '    %s --email %s' % (' '.join(request_certs), self.email)
                            )

            ret_reload = False
            if len(request_certs) > 0:
                Functions.run_bash("CERTBOT", certbot_certonly, return_result=False)
                ret_reload = True

            if len(renew_certs) > 0:
                Functions.run_bash("CERTBOT", "/usb/bin/certbot renew", return_result=False)
                ret_reload = True

            if ret_reload:
                self.find_live_certificates()

            return ret_reload
        except Exception as e:
            Functions.log("CERTBOT", "error", "%s" % (e))
            return False
        
    def merge_certificate(self, cert, key, filename):
        Functions.save(filename, cert + key)
    
    def find_live_certificates(self):
        letsencrypt_certs = "/etc/letsencrypt/live/"
        for item in os.listdir(letsencrypt_certs):
            path = os.path.join(letsencrypt_certs, item)
            if os.path.isdir(path):
                cert = Functions.load(os.path.join(path, "fullchain.pem"))
                key = Functions.load(os.path.join(path, "privkey.pem"))
                filename = "%s/%s.pem" % (self.certs, item)
                self.merge_certificate(cert, key, filename)
