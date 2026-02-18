import os
import shlex
import shutil
import subprocess
import sys
import time
from multiprocessing import Process
from typing import Final

import psutil

from .consts import Consts
from .functions import Functions
from .loggers import logger_haproxy


class DaemonizeHAProxy:
    HAPROXY_START: Final[str] = "start"
    HAPROXY_RELOAD: Final[str] = "reload"

    def __init__(self, custom_config_folder=None):
        self.process = None
        self.thread = None
        self.sleep_secs = None
        self.custom_config_folder = custom_config_folder if custom_config_folder is not None else Consts.custom_config_folder

    def haproxy(self, action):
        error = self.__prepare(self.get_haproxy_command(action), action)

        if error or self.process is None:
            logger_haproxy.fatal(f"Failed to start HAProxy ({action}). Exiting.")
            sys.exit(1)

        self.thread = Process(target=self.__start, args=())
        self.thread.start()

    @staticmethod
    def get_haproxy_bin() -> str:
        return shutil.which('haproxy') or '/usr/sbin/haproxy'

    def get_haproxy_command(self, action, pid_file="/run/haproxy.pid"):
        haproxy_bin = DaemonizeHAProxy.get_haproxy_bin()
        custom_config_files = ""
        if len(list(self.get_custom_config_files().keys())) != 0:
            custom_config_files = f"-f {self.custom_config_folder}"

        if action == DaemonizeHAProxy.HAPROXY_START or not os.path.exists(pid_file):
            return f"{haproxy_bin} -W -f {Consts.haproxy_config} {custom_config_files} -p {pid_file} -S /var/run/haproxy.sock"
        else:
            return_code, output = Functions().run_bash(logger_haproxy, f"cat {pid_file}", log_output=False)
            pid = "".join(output).rstrip()
            if psutil.pid_exists(int(pid)):
                return f"{haproxy_bin} -W -f {Consts.haproxy_config} {custom_config_files} -p {pid_file} -x /var/run/haproxy.sock -sf {pid}"
            else:
                os.unlink(pid_file)
                logger_haproxy.warning(
                    f"PID file {pid_file} does not exist. Restarting haproxy instead of reload."
                )
                return self.get_haproxy_command(DaemonizeHAProxy.HAPROXY_START, pid_file)

    def __validate_config(self):
        """Validate HAProxy configuration before starting."""
        validation_cmd = ["haproxy", "-c", "-f", Consts.haproxy_config]

        # Add custom config files if they exist
        for config_file in self.get_custom_config_files().keys():
            validation_cmd.extend(["-f", config_file])

        try:
            result = subprocess.run(
                validation_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return result.stderr if result.stderr else result.stdout
            return None

        except subprocess.TimeoutExpired:
            return "HAProxy configuration validation timed out"
        except Exception as e:
            return f"Error validating configuration: {e}"

    def __prepare(self, command, action=None):
        if not isinstance(command, (list, tuple)):
            command = shlex.split(command)

        # Validate HAProxy config before starting (but not on reload - HAProxy validates itself during reload)
        if action == DaemonizeHAProxy.HAPROXY_START:
            validation_error = self.__validate_config()
            if validation_error:
                logger_haproxy.fatal(f"HAProxy configuration validation failed:\n{validation_error}")
                return validation_error

        try:
            logger_haproxy.debug(f"HAPROXY command: {command}")
            self.process = subprocess.Popen(command,
                                            shell=False,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            bufsize=-1,
                                            universal_newlines=True)
            return None

        except Exception as e:
            error_msg = f"Failed to start HAProxy process: {e}"
            logger_haproxy.error(error_msg)
            return error_msg

    def __start(self):
        try:
            with self.process.stdout:
                for line in iter(self.process.stdout.readline, b''):
                    logger_haproxy.info(line.rstrip())

            return_code = self.process.wait()
            logger_haproxy.debug(f"Return code {return_code}")

        except Exception as e:
            logger_haproxy.error(f"{e}")

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