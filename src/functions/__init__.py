from datetime import datetime
from multiprocessing import Process, Lock
import subprocess
import shlex

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



    @staticmethod
    def log_ts(source, level, message, lock):
        if message is None or message == "":
            return

        if not isinstance(message, (list, tuple)):
            message = [message]
        
        lock.acquire()
        try:
            for line in message:
                print("[%s] %s [%s]: %s" % (source, datetime.now().strftime("%x %X"), level, line.rstrip()))
        finally:
            lock.release()

    @staticmethod
    def run_bash_ts(source, command, lock):
        if not isinstance(command, (list, tuple)):
            command = shlex.split(command)

        try:
            process = subprocess.Popen(command, 
                            shell=False,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            bufsize=-1,
                            universal_newlines=True)

            with process.stdout:
                for line in iter(process.stdout.readline, b''): 
                    Functions.log(source, "info", line)

            returncode = process.wait() 
            Functions.log(source, "info", "Return code %s" % (returncode))

        except Exception as e:
            Functions.log_ts(source, 'error', "%s" % (e), lock)


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
            Functions.log_ts(source, 'error', "%s" % (e), lock)


    def __start(self):
        source = "HAPROXY"
        try:
            with self.process.stdout:
                for line in iter(self.process.stdout.readline, b''): 
                    Functions.log(source, "info", line)

            returncode = self.process.wait() 
            Functions.log(source, "info", "Return code %s" % (returncode))

        except Exception as e:
            Functions.log_ts(source, 'error', "%s" % (e), lock)

    def is_alive(self):
        return self.thread.is_alive()

    def kill(self):
        self.process.kill()
        self.thread.kill()

    def terminate(self):
        self.process.terminate()
        self.thread.terminate()

    