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


@pytest.fixture(scope="function", autouse=True)
def reset_consts():
    """
    Reset Consts before and after each test.

    This ensures:
    1. Each test picks up the EASYHAPROXY_BASE_PATH environment variable
    2. Tests don't get permission errors trying to write to /etc/easyhaproxy/
    3. Consts path cache is cleared between tests for isolation
    """
    from functions import Consts
    Consts.reset()
    yield
    Consts.reset()


def pytest_sessionfinish(session, exitstatus):
    """
    Cleanup session temporary directory after all tests complete.
    """
    try:
        shutil.rmtree(_test_session_dir)
    except Exception:
        # Ignore cleanup errors
        pass