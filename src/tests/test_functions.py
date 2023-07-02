import os
import random
import re
import string

from functions import Functions


def test_functions_check_local_level():
    assert Functions.skip_log('CERTBOT', Functions.INFO) == False
    assert Functions.skip_log('HAPOROXY', Functions.INFO) == False
    assert Functions.skip_log('EASYHAPROXY', Functions.INFO) == False

    os.environ['CERTBOT_LOG_LEVEL'] = 'warn'
    assert Functions.skip_log('CERTBOT', Functions.INFO) == True
    os.environ['CERTBOT_LOG_LEVEL'] = ''

    os.environ['HAPROXY_LOG_LEVEL'] = 'warn'
    assert Functions.skip_log('HAPROXY', Functions.INFO) == True
    os.environ['HAPROXY_LOG_LEVEL'] = ''

    os.environ['EASYHAPROXY_LOG_LEVEL'] = 'warn'
    assert Functions.skip_log('EASYHAPROXY', Functions.INFO) == True
    os.environ['EASYHAPROXY_LOG_LEVEL'] = ''


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


def test_functions_check_log_sanity():
    print()
    Functions.log(Functions.EASYHAPROXY_LOG, Functions.INFO, "Test 1")
    assert Functions.debug_log is None

    Functions.debug_log = []
    try:
        Functions.log(Functions.EASYHAPROXY_LOG, Functions.INFO, "Test 2")
        assert len(Functions.debug_log) == 1
        assert re.match("\[EASYHAPROXY\] .* \[INFO\]: Test 2", Functions.debug_log[0])

        os.environ['CERTBOT_LOG_LEVEL'] = 'DEBUG'
        Functions.log(Functions.EASYHAPROXY_LOG, Functions.INFO, "Test 3")
        assert len(Functions.debug_log) == 2
        assert re.match("\[EASYHAPROXY\] .* \[INFO\]: Test 3", Functions.debug_log[1])

        os.environ['EASYHAPROXY_LOG_LEVEL'] = 'warn'
        Functions.log(Functions.EASYHAPROXY_LOG, Functions.INFO, "Test 4")  # Should not log to debug
        assert len(Functions.debug_log) == 2

    finally:
        os.environ['EASYHAPROXY_LOG_LEVEL'] = ''
        Functions.debug_log = None


def test_functions_run_bash_log_output():
    print()
    Functions.debug_log = []
    try:
        return_code, result = Functions.run_bash(Functions.EASYHAPROXY_LOG, "echo 'test run 1'", log_output=True,
                                                 return_result=False)
        assert return_code == 0
        assert result == []
        assert len(Functions.debug_log) == 1
        assert re.match("\[EASYHAPROXY\] .* \[INFO\]: test run 1", Functions.debug_log[0])
    finally:
        Functions.debug_log = None


def test_functions_run_bash_no_log_output():
    print()
    Functions.debug_log = []
    try:
        return_code, result = Functions.run_bash(Functions.EASYHAPROXY_LOG, "echo 'test run 2'", log_output=False,
                                                 return_result=False)
        assert return_code == 0
        assert result == []
        assert len(Functions.debug_log) == 0
    finally:
        Functions.debug_log = None


def test_functions_run_bash_return():
    print()
    Functions.debug_log = []
    try:
        return_code, result = Functions.run_bash(Functions.EASYHAPROXY_LOG, "echo 'test run 3'", log_output=False,
                                                 return_result=True)
        assert return_code == 0
        assert len(Functions.debug_log) == 0
        assert "".join(result) == 'test run 3'
    finally:
        Functions.debug_log = None


def test_functions_run_bash_log_and_return_output():
    print()
    Functions.debug_log = []
    try:
        return_code, result = Functions.run_bash(Functions.EASYHAPROXY_LOG, "echo 'test run 4'", log_output=True, return_result=True)
        assert return_code == 0
        assert "".join(result) == 'test run 4'
        assert len(Functions.debug_log) == 1
        assert re.match("\[EASYHAPROXY\] .* \[INFO\]: test run 4", Functions.debug_log[0])
    finally:
        Functions.debug_log = None


def test_functions_run_bash_ok():
    print()
    Functions.debug_log = []
    try:
        return_code, result = Functions.run_bash(Functions.EASYHAPROXY_LOG, "%s/fixtures/run_bash.sh" % os.path.dirname(__file__), log_output=True,
                                                 return_result=False)
        assert return_code == 0
        assert result == []
        assert len(Functions.debug_log) == 1
        assert re.match("\[EASYHAPROXY\] .* \[INFO\]: Processing run_bash.sh", Functions.debug_log[0])
    finally:
        Functions.debug_log = None


def test_functions_run_bash_fail():
    print()
    Functions.debug_log = []
    try:
        return_code, result = Functions.run_bash(Functions.EASYHAPROXY_LOG, "%s/fixtures/run_bash.sh 15" % os.path.dirname(__file__), log_output=True,
                                                 return_result=False)
        assert return_code == 15
        assert result == []
        assert len(Functions.debug_log) == 1
        assert re.match("\[EASYHAPROXY\] .* \[INFO\]: Processing run_bash.sh", Functions.debug_log[0])
    finally:
        Functions.debug_log = None


def test_functions_run_command_not_found():
    print()
    Functions.debug_log = []
    try:
        return_code, result = Functions.run_bash(Functions.EASYHAPROXY_LOG, "no_command_here", log_output=True,
                                                 return_result=False)
        assert return_code == -99
        assert str(result) == "[Errno 2] No such file or directory: 'no_command_here'"
        assert len(Functions.debug_log) == 0
    finally:
        Functions.debug_log = None
