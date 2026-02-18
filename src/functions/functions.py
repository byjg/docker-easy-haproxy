import logging
import os
import shlex
import subprocess
import sys
from typing import Final

from .filter import SingleLineNonEmptyFilter


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
        level = os.getenv(f"{source.name.upper()}_LOG_LEVEL", "").upper()
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
        with open(filename) as content_file:
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
            log_source.error(f"{e}")
            return [-99, e]