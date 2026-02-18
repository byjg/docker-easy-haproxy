import logging
import os
import random
import string
from io import StringIO

from functions import Functions, logger_certbot, logger_easyhaproxy, logger_haproxy

log_stream = StringIO() # Create StringIO object
log_handler = logging.StreamHandler(log_stream)
log_formatter = logging.Formatter('%(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)
logger_debug = logging.getLogger(__name__)
logger_debug.setLevel(logging.DEBUG)
logger_debug.addHandler(log_handler)

def test_functions_check_local_level():
    assert Functions.setup_log(logger_certbot) == logging.INFO
    assert Functions.setup_log(logger_haproxy) == logging.INFO
    assert Functions.setup_log(logger_easyhaproxy) == logging.INFO

    os.environ['CERTBOT_LOG_LEVEL'] = 'warn'
    assert Functions.setup_log(logger_certbot) == logging.WARNING
    del os.environ['CERTBOT_LOG_LEVEL']

    os.environ['HAPROXY_LOG_LEVEL'] = 'warn'
    assert Functions.setup_log(logger_haproxy) == logging.WARNING
    del os.environ['HAPROXY_LOG_LEVEL']

    os.environ['EASYHAPROXY_LOG_LEVEL'] = 'warn'
    assert Functions.setup_log(logger_easyhaproxy) == logging.WARNING
    del os.environ['EASYHAPROXY_LOG_LEVEL']


def test_function_load_and_save():
    filename = '/tmp/x.txt'
    try:
        assert not os.path.exists(filename)
        text = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(50))
        Functions.save(filename, text)
        assert os.path.exists(filename)
        assert Functions.load(filename) == text
    finally:
        os.unlink(filename)

def test_functions_run_bash_log_output():
    print()
    try:
        return_code, result = Functions.run_bash(logger_debug, "echo 'test run 1'", log_output=True,
                                                 return_result=False)
        assert return_code == 0
        assert result == []
        log_value = log_stream.getvalue()
        assert len(log_value) > 0
        assert log_value == "INFO - test run 1\n"
    finally:
        log_stream.truncate(0)


def test_functions_run_bash_no_log_output():
    print()
    try:
        return_code, result = Functions.run_bash(logger_debug, "echo 'test run 2'", log_output=False,
                                                 return_result=False)
        assert return_code == 0
        assert result == []
        assert len(log_stream.getvalue()) == 0
    finally:
        log_stream.truncate(0)


def test_functions_run_bash_return():
    print()
    try:
        return_code, result = Functions.run_bash(logger_debug, "echo 'test run 3'", log_output=False,
                                                 return_result=True)
        assert return_code == 0
        assert len(log_stream.getvalue()) == 0
        assert "".join(result) == 'test run 3'
    finally:
        log_stream.truncate(0)


def test_functions_run_bash_log_and_return_output():
    print()
    try:
        return_code, result = Functions.run_bash(logger_debug, "echo 'test run 4'",
                                                 log_output=True,
                                                 return_result=True)
        assert return_code == 0
        assert "".join(result) == 'test run 4'
        log_value = log_stream.getvalue().strip("\x00")
        assert len(log_value) > 0
        assert log_value == "INFO - test run 4\n"
    finally:
        log_stream.truncate(0)


def test_functions_run_bash_ok():
    print()
    try:
        return_code, result = Functions.run_bash(logger_debug, f"{os.path.dirname(__file__)}/fixtures/run_bash.sh",
                                                 log_output=True,
                                                 return_result=False)
        assert return_code == 0
        assert result == []
        log_value = log_stream.getvalue().strip("\x00")
        assert len(log_value) > 1
        assert log_value == "INFO - Processing run_bash.sh\n"
    finally:
        log_stream.truncate(0)


def test_functions_run_bash_fail():
    print()
    try:
        return_code, result = Functions.run_bash(logger_debug, f"{os.path.dirname(__file__)}/fixtures/run_bash.sh 15",
                                                 log_output=True,
                                                 return_result=False)
        assert return_code == 15
        assert result == []
        log_value = log_stream.getvalue().strip("\x00")
        assert len(log_value) > 0
        assert log_value == "INFO - Processing run_bash.sh\n"
    finally:
        log_stream.truncate(0)


def test_functions_run_command_not_found():
    print()
    try:
        return_code, result = Functions.run_bash(logger_debug, "no_command_here",
                                                 log_output=True,
                                                 return_result=False)
        assert return_code == -99
        assert str(result) == "[Errno 2] No such file or directory: 'no_command_here'"
        log_value = log_stream.getvalue().strip("\x00")
        assert len(log_value) > 0
        assert log_value == "ERROR - [Errno 2] No such file or directory: 'no_command_here'\n"
    finally:
        log_stream.truncate(0)
