import logging
import os
import random
import re
import string
from logging import Logger

from functions import Functions, loggerEasyHaproxy, loggerCertbot, loggerHaproxy

from io import StringIO

log_stream = StringIO() # Create StringIO object
log_handler = logging.StreamHandler(log_stream)
log_formatter = logging.Formatter('%(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)
loggerDebug = logging.getLogger(__name__)
loggerDebug.setLevel(logging.DEBUG)
loggerDebug.addHandler(log_handler)

def test_functions_check_local_level():
    assert Functions.skip_log(loggerCertbot, Functions.INFO) == logging.INFO
    assert Functions.skip_log(loggerHaproxy, Functions.INFO) == logging.INFO
    assert Functions.skip_log(loggerEasyHaproxy, Functions.INFO) == logging.INFO

    os.environ['CERTBOT_LOG_LEVEL'] = 'warn'
    assert Functions.skip_log(loggerCertbot, Functions.WARN) == logging.WARNING
    del os.environ['CERTBOT_LOG_LEVEL']

    os.environ['HAPROXY_LOG_LEVEL'] = 'warn'
    assert Functions.skip_log(loggerHaproxy, Functions.INFO) == logging.WARNING
    del os.environ['HAPROXY_LOG_LEVEL']

    os.environ['EASYHAPROXY_LOG_LEVEL'] = 'warn'
    assert Functions.skip_log(loggerEasyHaproxy, Functions.INFO) == logging.WARNING
    del os.environ['EASYHAPROXY_LOG_LEVEL']


def test_function_load_and_save():
    filename = '/tmp/x.txt'
    try:
        assert os.path.exists(filename) == False
        text = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(50))
        Functions.save(filename, text)
        assert os.path.exists(filename) == True
        assert Functions.load(filename) == text
    finally:
        os.unlink(filename)

def test_functions_run_bash_log_output():
    print()
    try:
        return_code, result = Functions.run_bash(loggerDebug, "echo 'test run 1'", log_output=True,
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
        return_code, result = Functions.run_bash(loggerDebug, "echo 'test run 2'", log_output=False,
                                                 return_result=False)
        assert return_code == 0
        assert result == []
        assert len(log_stream.getvalue()) == 0
    finally:
        log_stream.truncate(0)


def test_functions_run_bash_return():
    print()
    try:
        return_code, result = Functions.run_bash(loggerDebug, "echo 'test run 3'", log_output=False,
                                                 return_result=True)
        assert return_code == 0
        assert len(log_stream.getvalue()) == 0
        assert "".join(result) == 'test run 3'
    finally:
        log_stream.truncate(0)


def test_functions_run_bash_log_and_return_output():
    print()
    try:
        return_code, result = Functions.run_bash(loggerDebug, "echo 'test run 4'", log_output=True, return_result=True)
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
        return_code, result = Functions.run_bash(loggerDebug, "%s/fixtures/run_bash.sh" % os.path.dirname(__file__), log_output=True,
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
        return_code, result = Functions.run_bash(loggerDebug, "%s/fixtures/run_bash.sh 15" % os.path.dirname(__file__), log_output=True,
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
        return_code, result = Functions.run_bash(loggerDebug, "no_command_here", log_output=True,
                                                 return_result=False)
        assert return_code == -99
        assert str(result) == "[Errno 2] No such file or directory: 'no_command_here'"
        log_value = log_stream.getvalue().strip("\x00")
        assert len(log_value) > 0
        assert log_value == "ERROR - [Errno 2] No such file or directory: 'no_command_here'\n"
    finally:
        log_stream.truncate(0)
