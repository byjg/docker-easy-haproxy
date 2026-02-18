"""
Pytest test suite for EasyHAProxy Docker Swarm examples

These tests verify the functionality of Docker Swarm stack configurations.
Tests require Docker with Swarm support.

Test scenarios:
  1. TestSwarmBasicServices: easyhaproxy.yml + services.yml
     - HTTPS for host1.local and host2.local (embedded SSL cert)
     - HTTP to HTTPS redirect
     - HAProxy stats interface
     - HAProxy config verification

  2. TestSwarmPluginsCombined: plugins-combined.yml
     - Public website (Cloudflare + deny_pages)
     - Protected API (JWT validator + deny_pages)
     - Admin panel (IP whitelist)
     - HAProxy stats interface

Requirements:
- Docker with Swarm support
- pytest, requests, PyJWT, cryptography

Usage:
    # Run all swarm tests
    pytest tests_e2e/test_swarm.py -v

    # Run specific test class
    pytest tests_e2e/test_swarm.py::TestSwarmBasicServices -v

    # Run with markers
    pytest tests_e2e/test_swarm.py -m swarm -v
"""

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Generator

import pytest
import requests

BASE_DIR = Path(__file__).parent.absolute()
SWARM_DIR = BASE_DIR / "swarm"

# Session-level init state (prevent redundant work within a session;
# swarm and network are left running after the session so subsequent runs skip setup)
_swarm_image_built = False
_swarm_initialized = False
_swarm_network_created = False
# Session-level cloudflare config state
_cloudflare_config_created = False


# =============================================================================
# Image and Swarm Infrastructure Helpers
# =============================================================================

def ensure_haproxy_image():
    """Build byjg/easy-haproxy:local from source at the start of the test session.

    If the image already exists (e.g. pre-built by a CI step), the build is
    skipped so that CI can control how/when the image is built without the
    pytest session re-triggering a potentially slow or hanging `docker build`.
    Subsequent calls within the same session are no-ops (image already built).
    """
    global _swarm_image_built
    if _swarm_image_built:
        return

    # Skip build if image already exists (e.g. pre-built in CI)
    inspect = subprocess.run(
        ["docker", "image", "inspect", "byjg/easy-haproxy:local"],
        capture_output=True,
    )
    if inspect.returncode == 0:
        print("\n  ✓ byjg/easy-haproxy:local already exists, skipping build")
        _swarm_image_built = True
        return

    project_root = BASE_DIR.parent
    print("\n  → Building byjg/easy-haproxy:local from source...")
    subprocess.run(
        [
            "docker", "build",
            "-t", "byjg/easy-haproxy:local",
            "-f", str(project_root / "deploy/docker/Dockerfile"),
            str(project_root),
        ],
        check=True,
    )
    print("  ✓ Image built as byjg/easy-haproxy:local")
    _swarm_image_built = True


def init_swarm() -> None:
    """Initialize Docker Swarm if not already done this session.

    Uses a session-level flag (like ensure_haproxy_image) so the check runs at most
    once per pytest session regardless of how many fixtures call it.
    Swarm is left running after the session so subsequent runs skip initialization.
    """
    global _swarm_initialized
    if _swarm_initialized:
        return

    result = subprocess.run(
        ["docker", "info", "--format", "{{.Swarm.LocalNodeState}}"],
        capture_output=True, text=True, check=True
    )
    if result.stdout.strip() != "active":
        print("\n  → Initializing Docker Swarm...")
        subprocess.run(["docker", "swarm", "init"], check=True, capture_output=True)
        print("  ✓ Docker Swarm initialized")
    else:
        print("\n  ✓ Docker Swarm already active")

    _swarm_initialized = True


def create_overlay_network(network_name: str = "easyhaproxy") -> None:
    """Create an attachable overlay network if not already done this session.

    Uses a session-level flag (like ensure_haproxy_image / init_swarm) so the check
    runs at most once per pytest session.  The network is left running after the
    session so subsequent runs skip creation.
    """
    global _swarm_network_created
    if _swarm_network_created:
        return

    result = subprocess.run(
        ["docker", "network", "ls", "--filter", f"name={network_name}", "--format", "{{.Name}}"],
        capture_output=True, text=True, check=True
    )
    existing = [n.strip() for n in result.stdout.strip().split("\n") if n.strip()]
    if network_name not in existing:
        print(f"\n  → Creating overlay network '{network_name}'...")
        subprocess.run(
            ["docker", "network", "create", "--driver", "overlay", "--attachable", network_name],
            check=True, capture_output=True
        )
        print(f"  ✓ Overlay network '{network_name}' created")
    else:
        print(f"\n  ✓ Overlay network '{network_name}' already exists")

    _swarm_network_created = True


def wait_for_swarm_services(stack_name: str, timeout: int = 120) -> bool:
    """Poll until all services in a stack have reached their target replica count."""
    start_time = time.time()
    print(f"\n  → Waiting for stack '{stack_name}' services (timeout: {timeout}s)...")
    while time.time() - start_time < timeout:
        result = subprocess.run(
            ["docker", "stack", "services", stack_name, "--format", "{{.Replicas}}"],
            capture_output=True, text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            time.sleep(2)
            continue

        replicas = [r.strip() for r in result.stdout.strip().split("\n") if "/" in r]
        if not replicas:
            time.sleep(2)
            continue

        all_ready = all(r.split("/")[0] == r.split("/")[1] for r in replicas)
        if all_ready:
            elapsed = time.time() - start_time
            print(f"  ✓ All {len(replicas)} service(s) ready ({elapsed:.1f}s)")
            return True

        time.sleep(2)

    return False


def wait_for_http(
    url: str,
    headers: dict = None,
    expected_status: list = None,
    timeout: int = 120,
    verify_ssl: bool = False,
) -> bool:
    """Poll an HTTP endpoint until it responds with an expected status code."""
    if expected_status is None:
        expected_status = [200, 301, 302, 403, 401, 404]

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(
                url,
                headers=headers or {},
                verify=verify_ssl,
                allow_redirects=False,
                timeout=5,
            )
            if resp.status_code in expected_status:
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pass

        time.sleep(1)

    return False


def get_haproxy_container_id(stack_name: str, service_name: str = "haproxy") -> str:
    """Return the container ID for a swarm service (e.g., 'easyhaproxy_haproxy')."""
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name={stack_name}_{service_name}", "--format", "{{.ID}}"],
        capture_output=True, text=True, check=True
    )
    container_ids = [c.strip() for c in result.stdout.strip().split("\n") if c.strip()]
    if not container_ids:
        raise RuntimeError(f"No container found for {stack_name}_{service_name}")
    return container_ids[0]


def create_swarm_config(config_name: str, file_path: Path) -> None:
    """Create a Docker swarm config from a file, removing any existing one first."""
    subprocess.run(["docker", "config", "rm", config_name], capture_output=True)
    subprocess.run(
        ["docker", "config", "create", config_name, str(file_path)],
        check=True, capture_output=True
    )
    print(f"  ✓ Docker config '{config_name}' created")


def remove_swarm_config(config_name: str) -> None:
    """Remove a Docker swarm config, ignoring errors if it doesn't exist."""
    subprocess.run(["docker", "config", "rm", config_name], capture_output=True)


def create_cloudflare_config():
    """Download Cloudflare IP ranges and create a Docker swarm config.

    Adds the 10.0.0.0/8 range so that requests routed through Docker Swarm's
    ingress network (typically 10.x.x.x) are treated as Cloudflare IPs in tests.
    """
    global _cloudflare_config_created
    if _cloudflare_config_created:
        return

    print("\n  → Creating 'cloudflare_ips' Docker config...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".lst", delete=False) as f:
        temp_path = Path(f.name)

    try:
        # Add Docker ingress range so test requests appear to come from Cloudflare
        with open(temp_path, "a") as f:
            f.write("10.0.0.0/8\n")

        create_swarm_config("cloudflare_ips", temp_path)
        _cloudflare_config_created = True
    finally:
        temp_path.unlink(missing_ok=True)


# =============================================================================
# SwarmFixture: manages docker stack lifecycle
# =============================================================================

class SwarmFixture:
    """Helper class to manage Docker Swarm stack lifecycle."""

    def __init__(self, stack_files, stack_name: str, timeout: int = 120):
        self.stack_files = stack_files if isinstance(stack_files, list) else [stack_files]
        self.stack_name = stack_name
        self.timeout = timeout

    def deploy(self):
        """Issue `docker stack deploy` for each file without waiting for replicas."""
        for stack_file in self.stack_files:
            name = Path(stack_file).name
            print(f"\n  → Deploying stack '{self.stack_name}' from {name}...")
            result = subprocess.run(
                [
                    "docker", "stack", "deploy",
                    "--resolve-image", "never",   # use local image, never pull from registry
                    "-c", stack_file, self.stack_name,
                ],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"  ✗ Deploy failed:\n    stdout: {result.stdout}\n    stderr: {result.stderr}")
                raise subprocess.CalledProcessError(
                    result.returncode, result.args, result.stdout, result.stderr
                )

    def wait_ready(self):
        """Wait until all services in this stack have reached their target replica count."""
        if not wait_for_swarm_services(self.stack_name, self.timeout):
            raise TimeoutError(
                f"Stack '{self.stack_name}' services did not become ready within {self.timeout}s"
            )

    def up(self):
        """Deploy the stack and wait for all services to be running."""
        self.deploy()
        self.wait_ready()

    def down(self):
        """Force-kill all stack containers, then remove the stack definition."""
        print(f"\n  → Removing stack '{self.stack_name}'...")

        # Force-kill all running containers immediately (SIGKILL — no grace period)
        result = subprocess.run(
            ["docker", "ps", "-q", "--filter", f"name={self.stack_name}_"],
            capture_output=True, text=True
        )
        container_ids = [c.strip() for c in result.stdout.strip().split("\n") if c.strip()]
        if container_ids:
            subprocess.run(["docker", "kill"] + container_ids, capture_output=True)

        # Remove the stack definition (services, configs, secrets)
        subprocess.run(
            ["docker", "stack", "rm", self.stack_name],
            capture_output=True, text=True
        )

        # Containers are already dead from docker kill above; ports are freed immediately.
        print(f"  ✓ Stack '{self.stack_name}' removed")


# =============================================================================
# Session-level setup: swarm mode + overlay network + image build
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def swarm_setup():
    """Session fixture: build image, initialize Docker Swarm, and create overlay network.

    Each step runs at most once per session (guarded by module-level flags).
    Swarm mode and the overlay network are left running after the session so that
    a subsequent test run can skip setup — the same pattern as the image build.
    Only deployed stacks (SwarmFixture) are torn down between test classes.
    """
    ensure_haproxy_image()
    init_swarm()
    create_overlay_network()

    yield
    # No teardown of swarm/network: they persist for subsequent runs (faster second run)


# =============================================================================
# Per-test fixtures
# =============================================================================

@pytest.fixture(scope="class")
def swarm_basic_services(generate_ssl_certificates) -> Generator[None, None, None]:
    """Fixture for easyhaproxy.yml + services.yml.

    Deploys two stacks:
    - easyhaproxy: HAProxy in swarm discovery mode
    - services:    Two backends (host1.local, host2.local) with embedded SSL

    EasyHAProxy auto-attaches services to the easyhaproxy overlay network on
    each refresh cycle (default: every 10 seconds), then regenerates HAProxy
    config to include the discovered backends.
    """
    easyhaproxy = SwarmFixture(str(SWARM_DIR / "easyhaproxy.yml"), "easyhaproxy", timeout=120)
    services = SwarmFixture(str(SWARM_DIR / "services.yml"), "services", timeout=60)

    # Deploy both stacks immediately so they start pulling/starting in parallel,
    # then wait for each to reach its target replica count.
    easyhaproxy.deploy()
    services.deploy()
    easyhaproxy.wait_ready()
    services.wait_ready()

    # Wait for EasyHAProxy to auto-attach services, regenerate config, and
    # for HAProxy to start serving traffic (up to 2 refresh cycles = ~20s).
    # Do NOT include 503 — that means HAProxy is up but the backend isn't ready yet.
    print("\n  → Waiting for HAProxy to discover and configure swarm services...")
    ready = wait_for_http(
        "https://127.0.0.1/",
        headers={"Host": "host1.local"},
        expected_status=[200, 301, 302],
        timeout=120,
    )
    if not ready:
        print("  ⚠ Warning: Services may not be fully configured yet")
    else:
        print("  ✓ Services are reachable through HAProxy")

    yield
    services.down()
    easyhaproxy.down()


@pytest.fixture(scope="class")
def swarm_plugins_combined(generate_ssl_certificates) -> Generator[None, None, None]:
    """Fixture for plugins-combined.yml.

    Creates required Docker swarm configs (jwt_api_pubkey, cloudflare_ips) and
    deploys a self-contained stack containing:
    - HAProxy with plugin support
    - Public website (Cloudflare + deny_pages)
    - Protected API (JWT validator + deny_pages)
    - Admin panel (IP whitelist: 203.0.113.0/24, 10.0.0.0/8)
    """
    certs = generate_ssl_certificates

    print("\n  → Setting up Docker configs for plugins-combined stack...")
    create_swarm_config("jwt_api_pubkey", certs["jwt_pubkey"])
    create_cloudflare_config()

    stack = SwarmFixture(str(SWARM_DIR / "plugins-combined.yml"), "production", timeout=120)
    stack.up()

    # Wait for HAProxy to discover services and apply plugin configurations
    print("\n  → Waiting for HAProxy to configure plugin backends...")
    ready = wait_for_http(
        "http://127.0.0.1/",
        headers={"Host": "website.example.com"},
        expected_status=[200],
        timeout=120,
    )
    if not ready:
        print("  ⚠ Warning: Services may not be fully configured yet")
    else:
        print("  ✓ Services are reachable through HAProxy")

    yield
    stack.down()

    print("\n  → Cleaning up Docker configs...")
    remove_swarm_config("jwt_api_pubkey")
    remove_swarm_config("cloudflare_ips")
    global _cloudflare_config_created
    _cloudflare_config_created = False


# =============================================================================
# Tests: easyhaproxy.yml + services.yml - Basic Services with SSL in Swarm
# =============================================================================

@pytest.mark.swarm
@pytest.mark.ssl
class TestSwarmBasicServices:
    """Tests for Swarm mode with basic SSL services.

    Uses easyhaproxy.yml (HAProxy) + services.yml (two SSL backends).
    EasyHAProxy discovers services via Swarm API and auto-attaches them
    to the shared overlay network.
    """

    def test_services_running(self, swarm_basic_services):
        """Verify all expected swarm services are running."""
        result = subprocess.run(
            ["docker", "service", "ls", "--format", "{{.Name}}"],
            capture_output=True, text=True, check=True
        )
        service_names = result.stdout
        assert "easyhaproxy_haproxy" in service_names, "easyhaproxy_haproxy service not found"
        assert "services_container" in service_names, "services_container service not found"
        assert "services_container2" in service_names, "services_container2 service not found"

    def test_haproxy_config(self, swarm_basic_services):
        """Verify HAProxy configuration contains backends for both swarm services."""
        from utils import extract_backend_block
        container_id = get_haproxy_container_id("easyhaproxy")
        result = subprocess.run(
            ["docker", "exec", container_id, "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True, text=True, check=True
        )
        config = result.stdout

        # Both HTTPS backends must be present
        assert "backend srv_host1_local_443" in config, "HTTPS backend for host1.local not found"
        assert "backend srv_host2_local_443" in config, "HTTPS backend for host2.local not found"

        # HTTP to HTTPS redirect must be configured
        assert "redirect scheme https" in config or "redirect prefix https://" in config, \
            "HTTP to HTTPS redirect not found in HAProxy config"

    def test_https_host1(self, swarm_basic_services):
        """Test HTTPS access to host1.local through Swarm HAProxy."""
        response = requests.get(
            "https://127.0.0.1/",
            headers={"Host": "host1.local"},
            verify=False,
            timeout=10,
        )
        assert response.status_code == 200

    def test_https_host2(self, swarm_basic_services):
        """Test HTTPS access to host2.local through Swarm HAProxy."""
        response = requests.get(
            "https://127.0.0.1/",
            headers={"Host": "host2.local"},
            verify=False,
            timeout=10,
        )
        assert response.status_code == 200

    def test_http_redirect_host1(self, swarm_basic_services):
        """Test HTTP to HTTPS permanent redirect for host1.local."""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "host1.local"},
            allow_redirects=False,
            timeout=10,
        )
        assert response.status_code == 301
        assert response.headers.get("location") == "https://host1.local/"

    def test_http_redirect_host2(self, swarm_basic_services):
        """Test HTTP to HTTPS permanent redirect for host2.local."""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "host2.local"},
            allow_redirects=False,
            timeout=10,
        )
        assert response.status_code == 301
        assert response.headers.get("location") == "https://host2.local/"

# =============================================================================
# Tests: plugins-combined.yml - Multiple Security Plugins in Swarm
# =============================================================================

@pytest.mark.swarm
@pytest.mark.plugins
class TestSwarmPluginsCombined:
    """Tests for multiple combined security plugins in Swarm mode.

    Uses plugins-combined.yml which is a self-contained stack:
    - HAProxy with Cloudflare + JWT + IP-whitelist plugins
    - website.example.com: Cloudflare IP restoration + deny_pages
    - api.example.com:     JWT validator + deny_pages
    - admin.example.com:   IP whitelist (203.0.113.0/24, 10.0.0.0/8)
    """

    def test_services_running(self, swarm_plugins_combined):
        """Verify all four services are running in the production stack."""
        result = subprocess.run(
            ["docker", "service", "ls", "--format", "{{.Name}}"],
            capture_output=True, text=True, check=True
        )
        service_names = result.stdout
        assert "production_haproxy" in service_names, "production_haproxy service not found"
        assert "production_website" in service_names, "production_website service not found"
        assert "production_api" in service_names, "production_api service not found"
        assert "production_admin" in service_names, "production_admin service not found"

    def test_website_normal_access(self, swarm_plugins_combined):
        """Test normal GET request reaches the public website (Cloudflare + deny_pages)."""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "website.example.com"},
            timeout=10,
        )
        assert response.status_code == 200

    def test_website_blocked_paths(self, swarm_plugins_combined):
        """Test deny_pages plugin blocks sensitive paths with HTTP 404."""
        blocked_paths = ["/admin", "/wp-admin", "/.env", "/config"]
        for path in blocked_paths:
            response = requests.get(
                f"http://127.0.0.1{path}",
                headers={"Host": "website.example.com"},
                timeout=10,
            )
            assert response.status_code == 404, \
                f"Expected 404 for blocked path '{path}', got {response.status_code}"

    def test_api_without_token(self, swarm_plugins_combined):
        """Test JWT validator rejects requests that have no Authorization header."""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "api.example.com"},
            timeout=10,
        )
        assert response.status_code in (401, 403), \
            f"Expected 401/403 without JWT, got {response.status_code}"
        assert "Missing Authorization HTTP header" in response.text

    def test_api_with_valid_token(self, swarm_plugins_combined, jwt_token):
        """Test JWT validator allows requests with a valid RS256 JWT token."""
        response = requests.get(
            "http://127.0.0.1/",
            headers={
                "Host": "api.example.com",
                "Authorization": f"Bearer {jwt_token}",
            },
            timeout=10,
        )
        assert response.status_code == 200

    def test_api_blocked_paths_with_token(self, swarm_plugins_combined, jwt_token):
        """Test deny_pages blocks internal API paths even with a valid JWT token."""
        blocked_paths = ["/internal", "/debug", "/metrics"]
        for path in blocked_paths:
            response = requests.get(
                f"http://127.0.0.1{path}",
                headers={
                    "Host": "api.example.com",
                    "Authorization": f"Bearer {jwt_token}",
                },
                timeout=10,
            )
            assert response.status_code == 403, \
                f"Expected 403 for blocked API path '{path}', got {response.status_code}"

    def test_admin_panel_ip_whitelist(self, swarm_plugins_combined):
        """Test IP whitelist plugin on admin panel.

        The whitelist is '203.0.113.0/24,10.0.0.0/8'.
        In Docker Swarm ingress mode, requests from the host arrive at HAProxy
        with the Docker ingress router IP (typically in 10.0.0.0/8), so the
        admin panel should be accessible.
        """
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "admin.example.com"},
            timeout=10,
        )
        # Docker Swarm ingress IPs (10.x.x.x) are in the 10.0.0.0/8 whitelist
        assert response.status_code == 200, \
            (f"Expected admin access from Docker ingress IP (in 10.0.0.0/8), "
             f"got {response.status_code}")
