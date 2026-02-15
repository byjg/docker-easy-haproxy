"""
Pytest test suite for EasyHAProxy Static Configuration Mode

These tests verify static YAML configuration mode (EASYHAPROXY_DISCOVER=static).
Tests are organized by configuration file and can be run individually or as a suite.

Requirements:
- pytest
- requests
- PyJWT
- cryptography
- docker-compose

Usage:
    # Run all static tests
    pytest test_static.py -v

    # Run specific test class
    pytest test_static.py::TestStaticBasic -v

    # Run specific test
    pytest test_static.py::TestStaticBasic::test_https_host1 -v
"""

import subprocess
import shutil
from pathlib import Path
import pytest
import requests
from typing import Generator
from utils import extract_backend_block, DockerComposeFixture

# Base directory for static configuration
BASE_DIR = Path(__file__).parent.absolute()
STATIC_DIR = BASE_DIR / "static"
CONF_DIR = STATIC_DIR / "conf"

class StaticDockerComposeFixture(DockerComposeFixture):
    """Helper class to manage static docker-compose lifecycle with config file switching"""

    def __init__(self, config_file: str, startup_wait: int = 3, build: bool = None):
        # Initialize parent with static docker-compose.yml path
        super().__init__(str(STATIC_DIR / "docker-compose.yml"), startup_wait, build)

        self.config_file = config_file
        self.config_source = CONF_DIR / config_file
        self.config_target = CONF_DIR / "config.yml"

    def up(self):
        """Start docker-compose services with specified config"""
        print()  # Newline for better test output formatting
        print(f"  → Using static config: {self.config_file}")

        # Copy the config file to config.yml
        shutil.copy(self.config_source, self.config_target)
        print(f"  ✓ Config copied to config.yml")

        # Call parent's up() method to start services
        super().up()


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def static_basic() -> Generator[None, None, None]:
    """Fixture for config-basic.yml"""
    fixture = StaticDockerComposeFixture("config-basic.yml")
    fixture.up()
    yield
    fixture.down()


@pytest.fixture
def static_deny_pages() -> Generator[None, None, None]:
    """Fixture for config-deny-pages.yml"""
    fixture = StaticDockerComposeFixture("config-deny-pages.yml")
    fixture.up()
    yield
    fixture.down()


@pytest.fixture
def static_jwt_validator() -> Generator[None, None, None]:
    """Fixture for config-jwt-validator.yml"""
    fixture = StaticDockerComposeFixture("config-jwt-validator.yml")
    fixture.up()
    yield
    fixture.down()


# =============================================================================
# Test: config-basic.yml - Basic HTTP→HTTPS Redirect
# =============================================================================

@pytest.mark.static
class TestStaticBasic:
    """Tests for static config-basic.yml"""

    def test_haproxy_config(self, static_basic):
        """Test HAProxy configuration has SSL and redirect configurations"""
        result = subprocess.run(
            ["docker", "exec", "static-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Test HTTPS backend for host1
        https_host1_block = extract_backend_block(config, "srv_host1_local_443")
        assert https_host1_block, "Backend srv_host1_local_443 not found"
        assert "mode http" in https_host1_block

        # Verify SSL frontend exists
        assert "frontend https_in_443" in config or "bind *:443" in config

        # Verify HTTP to HTTPS redirect (new format uses http-request redirect scheme)
        assert "http-request redirect scheme https code 301" in config

    def test_https_host1(self, static_basic):
        """Test HTTPS access to host1.local"""
        response = requests.get(
            "https://127.0.0.1/",
            headers={"Host": "host1.local"},
            verify=False
        )
        assert response.status_code == 200

    def test_http_redirect_host1(self, static_basic):
        """Test HTTP to HTTPS redirect for host1.local"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "host1.local"},
            allow_redirects=False
        )
        assert response.status_code == 301
        assert "https://host1.local" in response.headers.get("location", "")

    def test_haproxy_stats(self, static_basic):
        """Test HAProxy stats interface"""
        from conftest import verify_haproxy_stats
        verify_haproxy_stats()


# =============================================================================
# Test: config-deny-pages.yml - Deny Pages Plugin
# =============================================================================

@pytest.mark.static
class TestStaticDenyPages:
    """Tests for static config-deny-pages.yml"""

    def test_haproxy_config(self, static_deny_pages):
        """Test HAProxy configuration has deny pages rules"""
        result = subprocess.run(
            ["docker", "exec", "static-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Extract backend for host1.local (should have global deny_pages config)
        backend_block = extract_backend_block(config, "srv_host1_local_80")
        assert backend_block, "Backend srv_host1_local_80 not found"

        # Verify deny pages plugin is configured
        assert "# Deny Pages - Block specific paths" in backend_block
        assert "acl denied_path path_beg" in backend_block
        assert "/admin" in backend_block
        assert "/.env" in backend_block
        assert "/config" in backend_block
        assert "http-request deny" in backend_block

    def test_normal_access(self, static_deny_pages):
        """Test normal access to allowed paths"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "host1.local"}
        )
        assert response.status_code == 200

    def test_blocked_paths(self, static_deny_pages):
        """Test access to blocked paths"""
        blocked_paths = ["/admin", "/.env", "/config"]
        for path in blocked_paths:
            response = requests.get(
                f"http://127.0.0.1{path}",
                headers={"Host": "host1.local"}
            )
            assert response.status_code == 404, f"Path {path} should be blocked with 404"

    def test_haproxy_stats(self, static_deny_pages):
        """Test HAProxy stats interface"""
        from conftest import verify_haproxy_stats
        verify_haproxy_stats()


# =============================================================================
# Test: config-jwt-validator.yml - JWT Validator Plugin
# =============================================================================

@pytest.mark.static
class TestStaticJWTValidator:
    """Tests for static config-jwt-validator.yml"""

    def test_haproxy_config(self, static_jwt_validator):
        """Test HAProxy configuration has JWT validation rules"""
        result = subprocess.run(
            ["docker", "exec", "static-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Extract backend for API (static mode uses different naming)
        # Find any backend that contains JWT validation
        assert "# JWT Validator - Validate JWT tokens" in config, \
            "JWT Validator plugin comment not found"
        assert "jwt_verify" in config, \
            "JWT signature verification not found"
        assert "Missing Authorization HTTP header" in config, \
            "JWT authorization check not found"

    def test_without_token(self, static_jwt_validator):
        """Test API access without JWT token (should fail)"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "api.local"}
        )
        assert response.status_code == 403
        assert "Missing Authorization HTTP header" in response.text

    def test_with_valid_token(self, static_jwt_validator, jwt_token):
        """Test API access with valid JWT token (should succeed)"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={
                "Host": "api.local",
                "Authorization": f"Bearer {jwt_token}"
            }
        )
        assert response.status_code == 200

    def test_haproxy_stats(self, static_jwt_validator):
        """Test HAProxy stats interface"""
        from conftest import verify_haproxy_stats
        verify_haproxy_stats()


if __name__ == "__main__":
    print("This is a pytest test suite. Run with: pytest test_static.py -v")
    print("\nAvailable test classes:")
    print("  - TestStaticBasic: Basic static configuration tests")
    print("  - TestStaticDenyPages: Deny pages plugin tests")
    print("  - TestStaticJWTValidator: JWT validator plugin tests")