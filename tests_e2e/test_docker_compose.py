"""
Pytest test suite for EasyHAProxy Docker Compose examples

These tests verify the functionality of various docker-compose configurations.
Tests are organized by compose file and can be run individually or as a suite.

Requirements:
- pytest
- requests
- PyJWT
- cryptography
- docker-compose

Usage:
    # Run all tests
    pytest test_docker_compose.py -v

    # Run specific test class
    pytest test_docker_compose.py::TestBasicSSL -v

    # Run specific test
    pytest test_docker_compose.py::TestBasicSSL::test_https_host1 -v

    # Run with markers
    pytest test_docker_compose.py -m ssl -v
"""

import subprocess
import time
import os
from pathlib import Path
import pytest
import requests
import jwt as jwt_lib
from typing import Generator
from utils import extract_backend_block, DockerComposeFixture

# Base directory for docker-compose files
BASE_DIR = Path(__file__).parent.absolute()
DOCKER_DIR = BASE_DIR / "docker"

# Track if cloudflare_ips.lst has been created in this test session
_cloudflare_ips_created = False
# Track if pebble CA cert has been downloaded in this test session
_pebble_ca_downloaded = False


def create_pebble_ca_file():
    """
    Download Pebble's test CA certificate.

    This file is required for docker-compose-acme-e2e.yml to trust Pebble's HTTPS endpoint.
    Downloads from Pebble's GitHub repository.

    Strategy:
    - First call: Always download (fresh certificate)
    - Subsequent calls: Skip if file exists (reuse from first call)
    """
    global _pebble_ca_downloaded

    pebble_ca_path = DOCKER_DIR / "pebble-ca.pem"

    # On subsequent calls, skip if file exists
    if _pebble_ca_downloaded and pebble_ca_path.exists() and pebble_ca_path.is_file():
        return

    # Download Pebble's test CA certificate
    subprocess.run(
        [
            "curl", "-sL", "-o", str(pebble_ca_path),
            "https://raw.githubusercontent.com/letsencrypt/pebble/main/test/certs/pebble.minica.pem"
        ],
        check=True
    )

    # Mark as downloaded for this test session
    _pebble_ca_downloaded = True


def create_cloudflare_ips_file():
    """
    Create cloudflare_ips.lst file with Cloudflare IP ranges and Docker network.

    This file is required by docker-compose files that use the Cloudflare plugin.
    Downloads real Cloudflare IPs and adds Docker private network for testing.

    Strategy:
    - First call: Always create (fresh download)
    - Subsequent calls: Skip if file exists (reuse from first call)
    """
    global _cloudflare_ips_created

    cloudflare_ips_path = BASE_DIR / "docker" / "cloudflare_ips.lst"

    # On subsequent calls, skip if file exists
    if _cloudflare_ips_created and cloudflare_ips_path.exists() and cloudflare_ips_path.is_file():
        return

    # Download Cloudflare IPv4 ranges
    subprocess.run(
        ["curl", "-s", "https://www.cloudflare.com/ips-v4"],
        stdout=open(cloudflare_ips_path, 'w'),
        check=True
    )
    with open(cloudflare_ips_path, 'a') as f:
        f.write("\n")

    # Download Cloudflare IPv6 ranges
    subprocess.run(
        ["curl", "-s", "https://www.cloudflare.com/ips-v6"],
        stdout=open(cloudflare_ips_path, 'a'),
        check=True
    )

    # Add Docker private network range so HAProxy treats test requests as from Cloudflare
    with open(cloudflare_ips_path, 'a') as f:
        f.write("\n")
        f.write("172.16.0.0/12\n")  # Docker bridge networks are typically in this range

    # Mark as created for this test session
    _cloudflare_ips_created = True


@pytest.fixture
def docker_compose_basic_ssl() -> Generator[None, None, None]:
    """Fixture for docker-compose.yml (Basic SSL)"""
    fixture = DockerComposeFixture(str(DOCKER_DIR / "docker-compose.yml"))
    fixture.up()
    yield
    fixture.down()


@pytest.fixture
def docker_compose_jwt_validator() -> Generator[None, None, None]:
    """Fixture for docker-compose-jwt-validator.yml"""
    fixture = DockerComposeFixture(str(DOCKER_DIR / "docker-compose-jwt-validator.yml"))
    fixture.up()
    yield
    fixture.down()


@pytest.fixture
def docker_compose_multi_containers() -> Generator[None, None, None]:
    """Fixture for docker-compose-multi-containers.yml"""
    fixture = DockerComposeFixture(str(DOCKER_DIR / "docker-compose-multi-containers.yml"))
    fixture.up()
    yield
    fixture.down()


@pytest.fixture
def docker_compose_php_fpm() -> Generator[None, None, None]:
    """Fixture for docker-compose-php-fpm.yml"""
    fixture = DockerComposeFixture(str(DOCKER_DIR / "docker-compose-php-fpm.yml"))
    fixture.up()
    yield
    fixture.down()


@pytest.fixture
def docker_compose_plugins_combined() -> Generator[None, None, None]:
    """Fixture for docker-compose-plugins-combined.yml"""
    # Create cloudflare_ips.lst (required by this compose file)
    create_cloudflare_ips_file()

    fixture = DockerComposeFixture(str(DOCKER_DIR / "docker-compose-plugins-combined.yml"))
    fixture.up()
    yield
    fixture.down()


@pytest.fixture
def docker_compose_ip_whitelist() -> Generator[None, None, None]:
    """Fixture for docker-compose-ip-whitelist.yml"""
    fixture = DockerComposeFixture(str(DOCKER_DIR / "docker-compose-ip-whitelist.yml"))
    fixture.up()
    yield
    fixture.down()


@pytest.fixture
def docker_compose_cloudflare() -> Generator[None, None, None]:
    """Fixture for docker-compose-cloudflare.yml"""
    # Create cloudflare_ips.lst (required by this compose file)
    create_cloudflare_ips_file()

    fixture = DockerComposeFixture(str(DOCKER_DIR / "docker-compose-cloudflare.yml"))
    fixture.up()
    yield
    fixture.down()


# =============================================================================
# Test: docker-compose.yml - Basic SSL Setup
# =============================================================================

@pytest.mark.ssl
class TestBasicSSL:
    """Tests for basic SSL setup with two virtual hosts"""

    def test_haproxy_config(self, docker_compose_basic_ssl):
        """Test HAProxy configuration has SSL and redirect configurations"""
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Test HTTPS backend for host1
        https_host1_block = extract_backend_block(config, "srv_host1_local_443")
        assert https_host1_block, "Backend srv_host1_local_443 not found"
        assert "mode http" in https_host1_block

        # Test HTTPS backend for host2
        https_host2_block = extract_backend_block(config, "srv_host2_local_443")
        assert https_host2_block, "Backend srv_host2_local_443 not found"
        assert "mode http" in https_host2_block

        # Verify SSL frontend exists and binds to port 443
        assert "frontend https_in_443" in config or "bind *:443" in config

        # Verify HTTP to HTTPS redirect
        # Check for redirect rules in HTTP frontend or backends
        assert "redirect scheme https" in config or "location: https://" in config

    def test_https_host1(self, docker_compose_basic_ssl):
        """Test HTTPS access to host1.local"""
        response = requests.get(
            "https://127.0.0.1/",
            headers={"Host": "host1.local"},
            verify=False
        )
        assert response.status_code == 200

    def test_https_host2(self, docker_compose_basic_ssl):
        """Test HTTPS access to host2.local"""
        response = requests.get(
            "https://127.0.0.1/",
            headers={"Host": "host2.local"},
            verify=False
        )
        assert response.status_code == 200

    def test_http_redirect_host1(self, docker_compose_basic_ssl):
        """Test HTTP to HTTPS redirect for host1.local"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "host1.local"},
            allow_redirects=False
        )
        assert response.status_code == 301
        assert response.headers.get("location") == "https://host1.local/"

    def test_http_redirect_host2(self, docker_compose_basic_ssl):
        """Test HTTP to HTTPS redirect for host2.local"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "host2.local"},
            allow_redirects=False
        )
        assert response.status_code == 301
        assert response.headers.get("location") == "https://host2.local/"

    def test_haproxy_stats(self, docker_compose_basic_ssl):
        """Test HAProxy stats interface"""
        from conftest import verify_haproxy_stats
        verify_haproxy_stats()


# =============================================================================
# Test: docker-compose-jwt-validator.yml - JWT Validator Plugin
# =============================================================================

@pytest.mark.jwt
class TestJWTValidator:
    """Tests for JWT validator plugin"""

    def test_haproxy_config(self, docker_compose_jwt_validator):
        """Test HAProxy configuration has JWT validator rules in the correct backend"""
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Extract the specific backend block
        backend_block = extract_backend_block(config, "srv_api_local_80")
        assert backend_block, "Backend srv_api_local_80 not found"

        # Verify JWT validator plugin comment
        assert "# JWT Validator - Validate JWT tokens" in backend_block

        # Verify JWT validation rules
        assert "http-request deny content-type 'text/html' string 'Missing Authorization HTTP header'" in backend_block
        assert "http_auth_bearer,jwt_header_query('$.alg')" in backend_block
        assert "http_auth_bearer,jwt_payload_query('$.iss')" in backend_block
        assert "http_auth_bearer,jwt_payload_query('$.aud')" in backend_block

        # Verify algorithm check
        assert "var(txn.alg) -m str RS256" in backend_block

        # Verify issuer and audience checks
        assert "var(txn.iss) -m str https://auth.example.com/" in backend_block
        assert "var(txn.aud) -m str https://api.example.com" in backend_block

        # Verify JWT signature verification
        assert 'jwt_verify(txn.alg,"/etc/easyhaproxy/jwt_keys/api_pubkey.pem")' in backend_block

        # Verify expiration check
        assert "JWT has expired" in backend_block

    def test_without_token(self, docker_compose_jwt_validator):
        """Test API access without JWT token (should fail)"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "api.local"}
        )
        assert response.status_code == 403
        assert "Missing Authorization HTTP header" in response.text

    def test_with_valid_token(self, docker_compose_jwt_validator, jwt_token):
        """Test API access with valid JWT token (should succeed)"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={
                "Host": "api.local",
                "Authorization": f"Bearer {jwt_token}"
            }
        )
        assert response.status_code == 200

    def test_haproxy_stats(self, docker_compose_jwt_validator):
        """Test HAProxy stats interface"""
        from conftest import verify_haproxy_stats
        verify_haproxy_stats()


# =============================================================================
# Test: docker-compose-multi-containers.yml - Load Balancing
# =============================================================================

@pytest.mark.loadbalancing
class TestMultiContainers:
    """Tests for load balancing with multiple container replicas"""

    def test_haproxy_config(self, docker_compose_multi_containers):
        """Test HAProxy configuration has multiple backend servers for load balancing"""
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Extract the specific backend block
        backend_block = extract_backend_block(config, "srv_www_helloworld_com_19901")
        assert backend_block, "Backend srv_www_helloworld_com_19901 not found"

        # Verify round-robin load balancing
        assert "balance roundrobin" in backend_block

        # Verify multiple servers are configured
        server_lines = [line for line in backend_block.split('\n') if line.strip().startswith('server srv-')]
        assert len(server_lines) >= 2, f"Expected at least 2 servers, found {len(server_lines)}"

        # Verify both servers have check and weight
        for server_line in server_lines:
            assert "check" in server_line
            assert "weight" in server_line

    def test_load_balancing(self, docker_compose_multi_containers):
        """Test round-robin load balancing across replicas"""
        container_ids = set()
        for _ in range(6):
            response = requests.get(
                "http://localhost:19901/",
                headers={"Host": "www.helloworld.com"}
            )
            assert response.status_code == 200
            container_ids.add(response.text.strip())

        # Should see at least 2 different container IDs
        assert len(container_ids) >= 2

    def test_domain_redirect(self, docker_compose_multi_containers):
        """Test domain redirect functionality"""
        response = requests.get(
            "http://localhost:19901/",
            headers={"Host": "google.helloworld.com"},
            allow_redirects=False
        )
        assert response.status_code == 301
        assert response.headers.get("location") == "www.google.com/"


# =============================================================================
# Test: docker-compose-php-fpm.yml - PHP-FPM FastCGI Plugin
# =============================================================================

@pytest.mark.php
class TestPHPFPM:
    """Tests for PHP-FPM FastCGI plugin"""

    def test_haproxy_config(self, docker_compose_php_fpm):
        """Test HAProxy configuration has FastCGI plugin configuration"""
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Extract the specific backend block
        backend_block = extract_backend_block(config, "srv_phpapp_local_80")
        assert backend_block, "Backend srv_phpapp_local_80 not found"

        # Verify FastCGI app is used
        assert "use-fcgi-app fcgi_phpapp_local" in backend_block

        # Verify server uses fcgi protocol
        assert "proto fcgi" in backend_block

        # Verify port 9000 (PHP-FPM default)
        assert ":9000" in backend_block

        # Now check for fcgi-app configuration (not in backend, but in global config)
        assert "fcgi-app fcgi_phpapp_local" in config

        # Extract fcgi-app block
        fcgi_lines = []
        in_fcgi = False
        for line in config.split('\n'):
            if line.startswith('fcgi-app fcgi_phpapp_local'):
                in_fcgi = True
            elif in_fcgi:
                if line.startswith(('fcgi-app ', 'frontend ', 'backend ', 'listen ')):
                    break
                fcgi_lines.append(line)

        fcgi_block = '\n'.join(fcgi_lines)

        # Verify FastCGI plugin configuration
        assert "docroot /var/www/html" in fcgi_block
        assert "index index.php" in fcgi_block
        assert "path-info" in fcgi_block

    def test_main_page(self, docker_compose_php_fpm):
        """Test main PHP page"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "phpapp.local"}
        )
        assert response.status_code == 200
        assert "PHP-FPM with EasyHAProxy" in response.text

    def test_phpinfo(self, docker_compose_php_fpm):
        """Test PHP info page"""
        response = requests.get(
            "http://127.0.0.1/info.php",
            headers={"Host": "phpapp.local"}
        )
        assert response.status_code == 200
        assert "phpinfo()" in response.text

    def test_path_info_routing(self, docker_compose_php_fpm):
        """Test PATH_INFO routing for RESTful URLs"""
        response = requests.get(
            "http://127.0.0.1/test-path-info.php/users/123",
            headers={"Host": "phpapp.local"}
        )
        assert response.status_code == 200
        assert "PATH_INFO" in response.text
        assert "/users/123" in response.text

    def test_haproxy_stats(self, docker_compose_php_fpm):
        """Test HAProxy stats interface"""
        from conftest import verify_haproxy_stats
        verify_haproxy_stats()


# =============================================================================
# Test: docker-compose-plugins-combined.yml - Multiple Plugins Combined
# =============================================================================

@pytest.mark.plugins
class TestPluginsCombined:
    """Tests for multiple plugins combined"""

    def test_haproxy_config(self, docker_compose_plugins_combined):
        """Test HAProxy configuration has all plugin configurations in correct backends"""
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Test website backend (Cloudflare + deny_pages)
        website_block = extract_backend_block(config, "srv_website_local_80")
        assert website_block, "Backend srv_website_local_80 not found"
        assert "# Cloudflare - Restore original visitor IP" in website_block
        assert "acl from_cloudflare src -f /etc/easyhaproxy/cloudflare_ips.lst" in website_block
        assert "# Deny Pages - Block specific paths" in website_block
        assert "acl denied_path path_beg /admin /wp-admin /wp-login.php /.env /config" in website_block
        assert "http-request deny deny_status 404 if denied_path" in website_block

        # Test API backend (JWT validator + deny_pages)
        api_block = extract_backend_block(config, "srv_api_local_80")
        assert api_block, "Backend srv_api_local_80 not found"
        assert "# JWT Validator - Validate JWT tokens" in api_block
        assert "Missing Authorization HTTP header" in api_block
        assert "jwt_verify" in api_block
        assert "# Deny Pages - Block specific paths" in api_block
        assert "acl denied_path path_beg /internal /debug /metrics" in api_block
        assert "http-request deny deny_status 403 if denied_path" in api_block

        # Test admin backend (IP whitelist)
        admin_block = extract_backend_block(config, "srv_admin_local_80")
        assert admin_block, "Backend srv_admin_local_80 not found"
        assert "# IP Whitelist - Only allow specific IPs" in admin_block
        assert "acl whitelisted_ip src" in admin_block
        assert "http-request deny deny_status 403 if !whitelisted_ip" in admin_block

    def test_website_normal_access(self, docker_compose_plugins_combined):
        """Test normal access to public website"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "website.local"}
        )
        assert response.status_code == 200

    def test_website_blocked_paths(self, docker_compose_plugins_combined):
        """Test blocked paths on public website"""
        blocked_paths = ["/admin", "/wp-admin", "/.env", "/config"]
        for path in blocked_paths:
            response = requests.get(
                f"http://127.0.0.1{path}",
                headers={"Host": "website.local"}
            )
            assert response.status_code == 404

    def test_api_without_token(self, docker_compose_plugins_combined):
        """Test API without JWT token"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "api.local"}
        )
        assert response.status_code == 403
        assert "Missing Authorization HTTP header" in response.text

    def test_api_with_valid_token(self, docker_compose_plugins_combined, jwt_token):
        """Test API with valid JWT token"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={
                "Host": "api.local",
                "Authorization": f"Bearer {jwt_token}"
            }
        )
        assert response.status_code == 200

    def test_api_blocked_paths_with_token(self, docker_compose_plugins_combined, jwt_token):
        """Test blocked paths on API even with valid JWT"""
        blocked_paths = ["/internal", "/debug", "/metrics"]
        for path in blocked_paths:
            response = requests.get(
                f"http://127.0.0.1{path}",
                headers={
                    "Host": "api.local",
                    "Authorization": f"Bearer {jwt_token}"
                }
            )
            assert response.status_code == 403

    def test_admin_panel_localhost(self, docker_compose_plugins_combined):
        """Test admin panel from localhost (should be allowed)"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "admin.local"}
        )
        assert response.status_code == 200

    def test_haproxy_stats(self, docker_compose_plugins_combined):
        """Test HAProxy stats interface"""
        from conftest import verify_haproxy_stats
        verify_haproxy_stats()


# =============================================================================
# Test: docker-compose-ip-whitelist.yml - IP Whitelist Plugin
# =============================================================================

@pytest.mark.security
class TestIPWhitelist:
    """Tests for IP whitelist plugin"""

    def test_haproxy_config(self, docker_compose_ip_whitelist):
        """Test HAProxy configuration has IP whitelist rules in the correct backend"""
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Extract the specific backend block
        backend_block = extract_backend_block(config, "srv_admin_local_80")
        assert backend_block, "Backend srv_admin_local_80 not found"

        # Verify IP whitelist plugin comment is in this backend
        assert "# IP Whitelist - Only allow specific IPs" in backend_block

        # Verify ACL for whitelisted IPs is in this backend
        assert "acl whitelisted_ip src" in backend_block

        # Extract the ACL line to verify IPs
        acl_line = [line for line in backend_block.split('\n') if 'acl whitelisted_ip src' in line][0]
        assert "127.0.0.1" in acl_line
        assert "192.168.0.0/16" in acl_line
        assert "10.0.0.0/8" in acl_line
        assert "172.16.0.0/12" in acl_line

        # Verify deny rule for non-whitelisted IPs is in this backend
        assert "http-request deny deny_status 403 if !whitelisted_ip" in backend_block

    def test_localhost_allowed(self, docker_compose_ip_whitelist):
        """Test access from localhost (should be allowed)"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "admin.local"}
        )
        assert response.status_code == 200
        assert "Admin Panel" in response.text

    def test_haproxy_stats(self, docker_compose_ip_whitelist):
        """Test HAProxy stats interface"""
        from conftest import verify_haproxy_stats
        verify_haproxy_stats()


# =============================================================================
# Test: docker-compose-cloudflare.yml - Cloudflare IP Restoration Plugin
# =============================================================================

@pytest.mark.cloudflare
class TestCloudflare:
    """Tests for Cloudflare IP restoration plugin"""

    def test_haproxy_config(self, docker_compose_cloudflare):
        """Test HAProxy configuration has Cloudflare plugin rules in the correct backend"""
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Extract the specific backend block
        backend_block = extract_backend_block(config, "srv_myapp_local_80")
        assert backend_block, "Backend srv_myapp_local_80 not found"

        # Verify Cloudflare plugin comment
        assert "# Cloudflare - Restore original visitor IP" in backend_block

        # Verify ACL for Cloudflare IPs
        assert "acl from_cloudflare src -f /etc/easyhaproxy/cloudflare_ips.lst" in backend_block

        # Verify transaction variable for real IP
        assert "http-request set-var(txn.real_ip) req.hdr(CF-Connecting-IP) if from_cloudflare" in backend_block

        # Verify X-Forwarded-For header restoration with transaction variable
        assert "http-request set-header X-Forwarded-For %[var(txn.real_ip)] if from_cloudflare" in backend_block

    def test_normal_request(self, docker_compose_cloudflare):
        """
        Test normal request without CF-Connecting-IP header

        When a request comes from a Cloudflare IP (Docker network is in cloudflare_ips.lst)
        but has NO CF-Connecting-IP header, the X-Forwarded-For will be empty because
        HAProxy tries to extract from a non-existent header. This is expected behavior.
        """
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "myapp.local"}
        )
        assert response.status_code == 200
        data = response.json()
        assert 'headers' in data
        assert 'x_forwarded_for' in data

        # Verify X-Forwarded-For is empty (not a translated IP)
        # Request comes from "Cloudflare IP" (Docker network) but has no CF-Connecting-IP
        x_forwarded_for = data['x_forwarded_for']
        assert x_forwarded_for == '', \
            f"Expected X-Forwarded-For to be empty (no CF-Connecting-IP provided), got '{x_forwarded_for}'"

        # Verify client_ip is the HAProxy container IP (backend sees connection from HAProxy)
        client_ip = data['client_ip']
        assert client_ip.startswith('172.'), \
            f"Expected client_ip to be HAProxy container IP (172.x.x.x), got '{client_ip}'"

    def test_cloudflare_ip_translation(self, docker_compose_cloudflare):
        """
        Test that Cloudflare plugin actually translates CF-Connecting-IP to X-Forwarded-For

        This test verifies the Cloudflare plugin correctly:
        1. Detects requests from Cloudflare IPs (127.0.0.1 is in cloudflare_ips.lst)
        2. Extracts the CF-Connecting-IP header value
        3. Sets X-Forwarded-For header to that value
        4. Backend receives the correct translated IP
        """
        test_ip = "203.0.113.50"
        response = requests.get(
            "http://127.0.0.1/",
            headers={
                "Host": "myapp.local",
                "CF-Connecting-IP": test_ip
            }
        )
        assert response.status_code == 200

        # Parse JSON response from header-echo server
        data = response.json()

        # VERIFY: X-Forwarded-For was set to the CF-Connecting-IP value
        assert data['x_forwarded_for'] == test_ip, \
            f"Expected X-Forwarded-For to be '{test_ip}', got '{data['x_forwarded_for']}'. " \
            f"Cloudflare IP translation is NOT working!"

        # Verify client_ip is still the HAProxy container IP (connection doesn't change)
        client_ip = data['client_ip']
        assert client_ip.startswith('172.'), \
            f"Expected client_ip to be HAProxy container IP (172.x.x.x), got '{client_ip}'"

    def test_haproxy_stats(self, docker_compose_cloudflare):
        """Test HAProxy stats interface"""
        from conftest import verify_haproxy_stats
        verify_haproxy_stats()


# =============================================================================
# Test: docker-compose-changed-label.yml - Custom Label Prefix
# =============================================================================

@pytest.fixture
def docker_compose_changed_label() -> Generator[None, None, None]:
    """Fixture for docker-compose-changed-label.yml"""
    fixture = DockerComposeFixture(str(DOCKER_DIR / "docker-compose-changed-label.yml"))
    fixture.up()
    yield
    fixture.down()


@pytest.mark.custom_label
class TestChangedLabel:
    """Tests for docker-compose-changed-label.yml - Custom label prefix"""

    def test_haproxy_config(self, docker_compose_changed_label):
        """Test HAProxy configuration with custom label prefix"""
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Verify HTTPS backend exists
        assert "backend srv_host1_local_443" in config

        # Verify SSL configuration (frontend with SSL)
        assert "bind *:443" in config
        assert "ssl crt" in config

        # Verify HTTP backend exists
        assert "backend srv_host1_local_80" in config

        # Verify HTTP to HTTPS redirect is configured
        assert "redirect prefix https://host1.local code 301" in config

    def test_https_access(self, docker_compose_changed_label):
        """Test HTTPS access to host1.local"""
        response = requests.get(
            "https://127.0.0.1/",
            headers={"Host": "host1.local"},
            verify=False  # Self-signed certificate
        )
        assert response.status_code == 200
        # byjg/static-httpserver returns a "Coming Soon" page
        assert "soon" in response.text.lower() or "coming" in response.text.lower()

    def test_http_redirect(self, docker_compose_changed_label):
        """Test HTTP to HTTPS redirect"""
        response = requests.get(
            "http://127.0.0.1/",
            headers={"Host": "host1.local"},
            allow_redirects=False
        )
        # The redirect uses 301 (permanent) as configured in the labels
        assert response.status_code == 301
        assert response.headers["Location"] == "https://host1.local/"

    def test_custom_label_prefix(self, docker_compose_changed_label):
        """Verify custom label prefix 'haproxy' is being used"""
        # Get container ID for static-httpserver
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", "ancestor=byjg/static-httpserver"],
            capture_output=True,
            text=True,
            check=True
        )
        container_id = result.stdout.strip()
        assert container_id, "Container not found"

        # Inspect container labels
        result = subprocess.run(
            ["docker", "inspect", container_id],
            capture_output=True,
            text=True,
            check=True
        )

        # Verify labels start with "haproxy." not "easyhaproxy."
        assert '"haproxy.http.host":' in result.stdout or '"haproxy.http.host"' in result.stdout
        assert '"haproxy.https.host":' in result.stdout or '"haproxy.https.host"' in result.stdout

    def test_haproxy_stats(self, docker_compose_changed_label):
        """Test HAProxy stats interface"""
        from conftest import verify_haproxy_stats
        verify_haproxy_stats()


# =============================================================================
# Test: docker-compose-acme-e2e.yml - ACME/Certbot with Pebble
# =============================================================================

@pytest.fixture
def docker_compose_acme() -> Generator[None, None, None]:
    """Fixture for docker-compose-acme-e2e.yml - ACME/Certbot E2E test"""
    volume_name = "docker_certbot-certs"

    # Download Pebble CA certificate (only once per test session)
    create_pebble_ca_file()

    # Clean up volume from previous test runs (ensures fresh start)
    subprocess.run(
        ["docker", "volume", "rm", volume_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL  # Ignore error if volume doesn't exist
    )

    fixture = DockerComposeFixture(str(DOCKER_DIR / "docker-compose-acme-e2e.yml"), startup_wait=0)
    fixture.up()
    yield
    fixture.down()

    # Clean up volume after test
    subprocess.run(
        ["docker", "volume", "rm", volume_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


@pytest.mark.acme
class TestACME:
    """Tests for docker-compose-acme-e2e.yml - ACME/Certbot with Pebble test server"""

    def test_haproxy_config(self, docker_compose_acme):
        """Test HAProxy configuration has ACME challenge routing"""
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "cat", "/etc/easyhaproxy/haproxy/haproxy.cfg"],
            capture_output=True,
            text=True,
            check=True
        )
        config = result.stdout

        # Verify ACME challenge ACL exists
        assert 'acl is_certbot_test_local_80 path_beg /.well-known/acme-challenge/' in config, \
            "ACME challenge ACL not found in HAProxy config"

        # Verify routing to certbot_backend
        assert 'use_backend certbot_backend if is_certbot_test_local_80' in config, \
            "ACME challenge routing rule not found"

        # Verify certbot_backend definition
        assert 'backend certbot_backend' in config, \
            "certbot_backend not defined"
        assert 'server certbot 127.0.0.1:2080' in config, \
            "certbot backend server not configured correctly"

        # Verify SSL redirect bypasses ACME challenges
        # Find redirect rule and verify it excludes certbot ACL
        lines = config.split('\n')
        for line in lines:
            if 'http-request redirect scheme https' in line and 'test_local' in line:
                assert '!is_certbot_test_local_80' in line, \
                    "SSL redirect should bypass ACME challenges"
                break

    def test_acme_challenge_routing(self, docker_compose_acme):
        """Test that HTTP requests to /.well-known/acme-challenge/ route to certbot backend"""
        # Request to ACME challenge path
        # We expect a 404 from certbot standalone server (no actual challenge file)
        # This confirms routing works - backend server would return different response
        response = requests.get(
            'http://localhost/.well-known/acme-challenge/test-token-12345',
            headers={'Host': 'test.local'},
            allow_redirects=False
        )

        # Should NOT redirect to HTTPS (ACME challenges must be HTTP)
        assert response.status_code != 301 and response.status_code != 302, \
            "ACME challenge path should not redirect to HTTPS"

        # Expected: 404 or connection error from certbot (not running during challenge)
        # What we're verifying is that it doesn't return backend's response
        assert response.status_code in [404, 502, 503], \
            f"Expected 404/502/503 from certbot backend, got {response.status_code}"

    def test_certificate_issuance(self, docker_compose_acme):
        """Test that Pebble successfully issues a certificate"""
        # Wait for certificate issuance (Certbot runs in background loop)
        # Typical time: 10-15 seconds from container start
        max_wait = 30
        check_interval = 2
        has_success = False

        for attempt in range(max_wait // check_interval):
            result = subprocess.run(
                ["docker", "logs", "docker-haproxy-1"],
                capture_output=True,
                text=True
            )
            logs = result.stdout + result.stderr

            # Look for certbot success messages
            # Certbot outputs: "Successfully received certificate"
            has_success = "Successfully received certificate" in logs or \
                         "Certificate not yet due for renewal" in logs or \
                         "Cert not yet due for renewal" in logs

            if has_success:
                break

            # Wait before next check
            time.sleep(check_interval)

        # If not successful after waiting, check for Pebble connection
        if not has_success:
            # Check if we can at least connect to Pebble
            has_pebble_connection = "pebble:14000/dir" in logs or "pebble:14000" in logs
            assert has_pebble_connection, \
                f"HAProxy cannot connect to Pebble ACME server after {max_wait}s. Check docker network.\nLogs:\n{logs[-2000:]}"

        # Verify merged certificate file exists
        # EasyHAProxy merges cert+key from /etc/easyhaproxy/certs/live/ to /etc/easyhaproxy/certs/certbot/{domain}.pem
        merged_cert_path = "/etc/easyhaproxy/certs/certbot/test.local.pem"
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "test", "-f", merged_cert_path],
            capture_output=True
        )
        assert result.returncode == 0, \
            f"Merged certificate file not found at {merged_cert_path}. " \
            f"Certificate issuance or merging may have failed. Check logs: docker logs docker-haproxy-1"

        # Verify merged certificate is valid (contains both cert and key)
        result = subprocess.run(
            ["docker", "exec", "docker-haproxy-1", "cat", merged_cert_path],
            capture_output=True,
            text=True,
            check=True
        )
        cert_content = result.stdout
        assert '-----BEGIN CERTIFICATE-----' in cert_content, \
            f"{merged_cert_path} does not contain a certificate"
        assert '-----END CERTIFICATE-----' in cert_content, \
            f"{merged_cert_path} certificate is incomplete"
        assert '-----BEGIN PRIVATE KEY-----' in cert_content or '-----BEGIN RSA PRIVATE KEY-----' in cert_content, \
            f"{merged_cert_path} does not contain a private key"

    def test_https_with_issued_cert(self, docker_compose_acme):
        """Test HTTPS works with Pebble-issued certificate"""
        # Pebble issues real certificates, but from a test CA
        # Browsers won't trust them, but the TLS handshake should work
        response = requests.get(
            'https://localhost/',
            headers={'Host': 'test.local'},
            verify=False  # Pebble uses test CA not trusted by system
        )

        # Should get 200 from backend server
        assert response.status_code == 200, \
            f"Expected 200 OK, got {response.status_code}"

        # Verify it's the backend server responding (static-httpserver)
        assert "soon" in response.text.lower() or "coming" in response.text.lower(), \
            "Response doesn't match expected backend server content"

    def test_http_to_https_redirect_with_acme_bypass(self, docker_compose_acme):
        """Test HTTP redirects to HTTPS but ACME challenges bypass redirect"""
        # Regular HTTP request (not ACME challenge) should redirect
        response = requests.get(
            'http://localhost/',
            headers={'Host': 'test.local'},
            allow_redirects=False
        )

        assert response.status_code == 301, \
            f"Expected HTTP 301 redirect, got {response.status_code}"
        assert response.headers['Location'].startswith('https://'), \
            f"Expected redirect to HTTPS, got {response.headers['Location']}"

        # ACME challenge path should NOT redirect (tested in test_acme_challenge_routing)


# =============================================================================
# Helper functions for manual testing
# =============================================================================

def run_manual_test(compose_file: str, test_function):
    """
    Helper function to run a test manually without pytest

    Example:
        def my_test():
            response = requests.get("http://localhost/")
            assert response.status_code == 200

        run_manual_test("docker-compose.yml", my_test)
    """
    fixture = DockerComposeFixture(compose_file)
    try:
        fixture.up()
        test_function()
        print("✅ Test passed!")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
    finally:
        fixture.down()


if __name__ == "__main__":
    print("This is a pytest test suite. Run with: pytest test_docker_compose.py -v")
    print("\nAvailable test classes:")
    print("  - TestBasicSSL: Basic SSL setup tests")
    print("  - TestJWTValidator: JWT validator plugin tests")
    print("  - TestMultiContainers: Load balancing tests")
    print("  - TestPHPFPM: PHP-FPM FastCGI tests")
    print("  - TestPluginsCombined: Combined plugins tests")
    print("  - TestIPWhitelist: IP whitelist plugin tests")
    print("  - TestCloudflare: Cloudflare IP restoration plugin tests")
    print("  - TestChangedLabel: Custom label prefix tests")
    print("  - TestACME: ACME/Certbot certificate issuance with Pebble test server")