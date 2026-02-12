"""
Shared pytest fixtures for EasyHAProxy integration tests.

This module provides fixtures used by both Docker Compose and Kubernetes tests.
"""

import subprocess
from pathlib import Path
import pytest
from utils import generate_jwt_token

BASE_DIR = Path(__file__).parent.absolute()


@pytest.fixture(scope="session", autouse=True)
def generate_ssl_certificates():
    """
    Generate SSL certificates once for all tests (Docker + Kubernetes).
    Runs automatically at the start of the test session.

    This fixture uses the working Docker approach (BASE_DIR) instead of the
    broken K8s approach (BASE_DIR.parent) which was outdated after restructuring.
    """
    script_path = BASE_DIR / "generate-keys.sh"

    if not script_path.exists():
        pytest.skip(f"SSL certificate generation script not found: {script_path}")

    # Run from tests_e2e directory (Docker approach - WORKING)
    result = subprocess.run(
        ["bash", str(script_path)],
        cwd=BASE_DIR,  # NOT BASE_DIR.parent (K8s bug)
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        pytest.fail(f"Failed to generate SSL certificates:\n{result.stderr}")

    # Return paths for K8s tests to use
    yield {
        "host1_local": BASE_DIR / "static" / "host1.local.pem",
        "host2_local": BASE_DIR / "docker" / "host2.local.pem",
        "jwt_private": BASE_DIR / "docker" / "jwt_private.pem",
        "jwt_pubkey": BASE_DIR / "docker" / "jwt_pubkey.pem",
    }
    # No cleanup needed - certificates can be reused


@pytest.fixture
def jwt_token(generate_ssl_certificates) -> str:
    """
    Generate a valid JWT token for Docker Compose tests.
    Uses simple defaults suitable for docker-compose examples.
    """
    certs = generate_ssl_certificates
    return generate_jwt_token(
        private_key_path=certs["jwt_private"],
        issuer='https://auth.example.com/',
        audience='https://api.example.com',
        expired=False
    )


def verify_haproxy_stats(port: int = 1936, username: str = "admin", password: str = "password"):
    """
    Verify HAProxy stats interface is accessible.

    This eliminates the duplicated test method that appears in 7 different
    test classes in test_docker_compose.py.

    Args:
        port: HAProxy stats port
        username: Basic auth username
        password: Basic auth password

    Raises:
        AssertionError: If stats page not accessible or missing expected content
    """
    import requests

    response = requests.get(f"http://localhost:{port}", auth=(username, password))
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "Statistics Report for HAProxy" in response.text, \
        "HAProxy stats page content not found"