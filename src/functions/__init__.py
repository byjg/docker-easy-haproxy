from datetime import datetime
import subprocess
import shlex
import numpy as np

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

        if not isinstance(message, (list, tuple, np.ndarray)):
            message = [message]
        
        for line in message:
            print("[%s] %s [%s]: %s" % (source, datetime.now().strftime("%x %X"), level, line.rstrip()))

    @staticmethod
    def run_bash(source, command, log_output=True, return_result=True):
        if not isinstance(command, (list, tuple, np.ndarray)):
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
                Functions.log(source, "error", process.stderr.readline())
                return_code = process.poll()
                if return_code is not None:
                    lines = []
                    for line in process.stdout.readlines():
                        output.append(line.rstrip()) if return_result else None
                        lines.append(line.rstrip())
                    Functions.log(source, "info", lines) if log_output else None
                    Functions.log(source, "error", process.stderr.readlines())
                    break

            return output
        except Exception as e:
            Functions.log(source, 'error', "%s" % (e))
