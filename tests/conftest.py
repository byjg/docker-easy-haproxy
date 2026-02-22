"""
Pytest configuration and fixtures for EasyHAProxy tests.

This module provides session-wide and function-level fixtures for testing.
"""

import os
import shutil
import tempfile
import pytest


# Create a session-wide temporary directory for all tests
# Use a different prefix to avoid conflicts with cleanup plugin (which looks for "easyhaproxy_*")
_test_session_dir = tempfile.mkdtemp(prefix="pytest_easyhaproxy_")
os.environ["EASYHAPROXY_BASE_PATH"] = _test_session_dir


_CONTAINER_ENV_VARS = [
    "HAPROXY_USERNAME",
    "HAPROXY_PASSWORD",
    "HAPROXY_STATS_PORT",
    "HAPROXY_STATS_CORS_ORIGIN",
    "HAPROXY_CUSTOMERRORS",
    "EASYHAPROXY_SSL_MODE",
    "EASYHAPROXY_LABEL_PREFIX",
    "EASYHAPROXY_LOG_LEVEL",
    "HAPROXY_LOG_LEVEL",
    "CERTBOT_LOG_LEVEL",
    "EASYHAPROXY_CERTBOT_EMAIL",
    "EASYHAPROXY_CERTBOT_SERVER",
    "EASYHAPROXY_CERTBOT_AUTOCONFIG",
    "EASYHAPROXY_CERTBOT_EAB_KID",
    "EASYHAPROXY_CERTBOT_EAB_HMAC_KEY",
    "EASYHAPROXY_PLUGINS_ENABLED",
    "EASYHAPROXY_PLUGINS_ABORT_ON_ERROR",
]


@pytest.fixture(scope="function", autouse=True)
def reset_consts():
    """
    Reset Consts and ContainerEnv environment variables before and after each test.

    This ensures:
    1. Each test picks up the EASYHAPROXY_BASE_PATH environment variable
    2. Tests don't get permission errors trying to write to /etc/easyhaproxy/
    3. Consts path cache is cleared between tests for isolation
    4. Environment variables set by ContainerEnv._yaml_to_env don't bleed across tests
    """
    from functions import Consts
    Consts.reset()
    for var in _CONTAINER_ENV_VARS:
        os.environ.pop(var, None)
    yield
    Consts.reset()
    for var in _CONTAINER_ENV_VARS:
        os.environ.pop(var, None)


def pytest_sessionfinish(session, exitstatus):
    """
    Cleanup session temporary directory after all tests complete.
    """
    try:
        shutil.rmtree(_test_session_dir)
    except Exception:
        # Ignore cleanup errors
        pass