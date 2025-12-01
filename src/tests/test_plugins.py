"""
Tests for EasyHAProxy Plugin System

Tests all builtin plugins:
- CloudflarePlugin (domain)
- CleanupPlugin (global)
- DenyPagesPlugin (domain)
"""

import os
import sys
import json
import tempfile
import time

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginManager, PluginContext
from plugins.builtin.cloudflare import CloudflarePlugin
from plugins.builtin.cleanup import CleanupPlugin
from plugins.builtin.deny_pages import DenyPagesPlugin
from plugins.builtin.ip_whitelist import IpWhitelistPlugin
from plugins.builtin.jwt_validator import JwtValidatorPlugin
from plugins.builtin.fastcgi import FastcgiPlugin
import easymapping


def load_fixture(file):
    """Load a test fixture"""
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", file)
    with open(fixture_path, 'r') as content_file:
        line_list = json.loads("".join(content_file.readlines()))
    return line_list


class TestCloudflarePlugin:
    """Test cases for CloudflarePlugin (DOMAIN plugin)"""

    def test_cloudflare_plugin_initialization(self):
        """Test plugin initializes with correct defaults"""
        plugin = CloudflarePlugin()
        assert plugin.name == "cloudflare"
        assert plugin.enabled is True
        assert plugin.ip_list_path == "/etc/haproxy/cloudflare_ips.lst"

    def test_cloudflare_plugin_configuration(self):
        """Test plugin configuration"""
        plugin = CloudflarePlugin()

        # Test custom IP list path
        plugin.configure({"ip_list_path": "/custom/path/cf_ips.txt"})
        assert plugin.ip_list_path == "/custom/path/cf_ips.txt"

        # Test disabling
        plugin.configure({"enabled": "false"})
        assert plugin.enabled is False

        # Test enabling with various values
        plugin.configure({"enabled": "true"})
        assert plugin.enabled is True

        plugin.configure({"enabled": "1"})
        assert plugin.enabled is True

        plugin.configure({"enabled": "yes"})
        assert plugin.enabled is True

    def test_cloudflare_plugin_generates_config(self):
        """Test plugin generates correct HAProxy config"""
        plugin = CloudflarePlugin()

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        assert "Cloudflare" in result.haproxy_config
        assert "acl from_cloudflare src -f /etc/haproxy/cloudflare_ips.lst" in result.haproxy_config
        assert "http-request set-header X-Forwarded-For %[req.hdr(CF-Connecting-IP)]" in result.haproxy_config
        assert result.metadata["domain"] == "example.com"
        assert result.metadata["ip_list_path"] == "/etc/haproxy/cloudflare_ips.lst"

    def test_cloudflare_plugin_disabled(self):
        """Test plugin returns empty config when disabled"""
        plugin = CloudflarePlugin()
        plugin.configure({"enabled": "false"})

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com"
        )

        result = plugin.process(context)
        assert result.haproxy_config == ""
        assert result.metadata == {}

    def test_cloudflare_plugin_in_haproxy_config(self):
        """Test Cloudflare plugin integration in full HAProxy config generation"""
        # Use fixture with cloudflare plugin enabled via labels
        line_list = load_fixture("services-with-cloudflare")

        result = {
            "customerrors": False,
            "certbot": {"email": "test@example.com"},
            "stats": {"port": 0}
        }

        cfg = easymapping.HaproxyConfigGenerator(result)
        haproxy_config = cfg.generate(line_list)

        # Verify Cloudflare config is in the output
        assert "Cloudflare - Restore original visitor IP" in haproxy_config
        assert "acl from_cloudflare src -f /etc/haproxy/cloudflare_ips.lst" in haproxy_config
        assert "http-request set-header X-Forwarded-For %[req.hdr(CF-Connecting-IP)]" in haproxy_config


class TestCleanupPlugin:
    """Test cases for CleanupPlugin (GLOBAL plugin)"""

    def test_cleanup_plugin_initialization(self):
        """Test plugin initializes with correct defaults"""
        plugin = CleanupPlugin()
        assert plugin.name == "cleanup"
        assert plugin.enabled is True
        assert plugin.max_idle_time == 300
        assert plugin.cleanup_temp_files is True

    def test_cleanup_plugin_configuration(self):
        """Test plugin configuration"""
        plugin = CleanupPlugin()

        # Test max_idle_time
        plugin.configure({"max_idle_time": "600"})
        assert plugin.max_idle_time == 600

        # Test cleanup_temp_files
        plugin.configure({"cleanup_temp_files": "false"})
        assert plugin.cleanup_temp_files is False

        # Test enabled
        plugin.configure({"enabled": "false"})
        assert plugin.enabled is False

    def test_cleanup_plugin_processes_files(self):
        """Test plugin cleans up old temp files"""
        plugin = CleanupPlugin()
        plugin.configure({"max_idle_time": "1"})  # 1 second

        # Create a temp file
        with tempfile.NamedTemporaryFile(prefix="easyhaproxy_", delete=False) as tmp:
            temp_file = tmp.name

        # Wait for file to age
        time.sleep(2)

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={}
        )

        # Run cleanup
        result = plugin.process(context)

        # Verify file was removed
        assert not os.path.exists(temp_file)
        assert result.haproxy_config == ""
        assert result.metadata["actions_performed"] >= 0

    def test_cleanup_plugin_disabled(self):
        """Test plugin does nothing when disabled"""
        plugin = CleanupPlugin()
        plugin.configure({"enabled": "false"})

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={}
        )

        result = plugin.process(context)
        assert result.haproxy_config == ""
        assert result.metadata == {}

    def test_cleanup_plugin_in_haproxy_config(self):
        """Test Cleanup plugin integration (should not affect config output)"""
        line_list = load_fixture("services")

        # Enable cleanup plugin
        result = {
            "customerrors": False,
            "certbot": {"email": "test@example.com"},
            "stats": {"port": 0},
            "plugins": {
                "enabled": ["cleanup"],
                "config": {
                    "cleanup": {
                        "max_idle_time": "300"
                    }
                }
            }
        }

        cfg = easymapping.HaproxyConfigGenerator(result)
        haproxy_config = cfg.generate(line_list)

        # Cleanup plugin should not add any HAProxy config
        assert "cleanup" not in haproxy_config.lower()
        # But the config should still be valid
        assert "backend certbot_backend" in haproxy_config


class TestDenyPagesPlugin:
    """Test cases for DenyPagesPlugin (DOMAIN plugin)"""

    def test_deny_pages_plugin_initialization(self):
        """Test plugin initializes with correct defaults"""
        plugin = DenyPagesPlugin()
        assert plugin.name == "deny_pages"
        assert plugin.enabled is True
        assert plugin.paths == []
        assert plugin.status_code == 403

    def test_deny_pages_plugin_configuration(self):
        """Test plugin configuration"""
        plugin = DenyPagesPlugin()

        # Test paths
        plugin.configure({"paths": "/admin,/private,/internal"})
        assert plugin.paths == ["/admin", "/private", "/internal"]

        # Test status code
        plugin.configure({"status_code": "404"})
        assert plugin.status_code == 404

        # Test enabled
        plugin.configure({"enabled": "false"})
        assert plugin.enabled is False

    def test_deny_pages_plugin_generates_config(self):
        """Test plugin generates correct HAProxy config"""
        plugin = DenyPagesPlugin()
        plugin.configure({
            "paths": "/admin,/private",
            "status_code": "403"
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        assert "Deny Pages" in result.haproxy_config
        assert "acl denied_path path_beg /admin /private" in result.haproxy_config
        assert "http-request deny deny_status 403 if denied_path" in result.haproxy_config
        assert result.metadata["domain"] == "example.com"
        assert result.metadata["blocked_paths"] == ["/admin", "/private"]
        assert result.metadata["status_code"] == 403

    def test_deny_pages_plugin_disabled(self):
        """Test plugin returns empty config when disabled"""
        plugin = DenyPagesPlugin()
        plugin.configure({"enabled": "false", "paths": "/admin"})

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com"
        )

        result = plugin.process(context)
        assert result.haproxy_config == ""

    def test_deny_pages_plugin_no_paths(self):
        """Test plugin returns empty config when no paths configured"""
        plugin = DenyPagesPlugin()

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com"
        )

        result = plugin.process(context)
        assert result.haproxy_config == ""

    def test_deny_pages_plugin_in_haproxy_config(self):
        """Test Deny Pages plugin integration in full HAProxy config generation"""
        # Use fixture with deny_pages plugin enabled via labels
        line_list = load_fixture("services-with-deny-pages")

        result = {
            "customerrors": False,
            "certbot": {"email": "test@example.com"},
            "stats": {"port": 0}
        }

        cfg = easymapping.HaproxyConfigGenerator(result)
        haproxy_config = cfg.generate(line_list)

        # Verify Deny Pages config is in the output
        assert "Deny Pages - Block specific paths" in haproxy_config
        assert "acl denied_path path_beg /admin /wp-admin" in haproxy_config
        assert "http-request deny deny_status 404 if denied_path" in haproxy_config


class TestIpWhitelistPlugin:
    """Test cases for IpWhitelistPlugin (DOMAIN plugin)"""

    def test_ip_whitelist_plugin_initialization(self):
        """Test plugin initializes with correct defaults"""
        plugin = IpWhitelistPlugin()
        assert plugin.name == "ip_whitelist"
        assert plugin.enabled is True
        assert plugin.allowed_ips == []
        assert plugin.status_code == 403

    def test_ip_whitelist_plugin_configuration(self):
        """Test plugin configuration"""
        plugin = IpWhitelistPlugin()

        # Test allowed IPs
        plugin.configure({"allowed_ips": "192.168.1.0/24,10.0.0.1,172.16.0.0/16"})
        assert plugin.allowed_ips == ["192.168.1.0/24", "10.0.0.1", "172.16.0.0/16"]

        # Test status code
        plugin.configure({"status_code": "404"})
        assert plugin.status_code == 404

        # Test enabled
        plugin.configure({"enabled": "false"})
        assert plugin.enabled is False

    def test_ip_whitelist_plugin_generates_config(self):
        """Test plugin generates correct HAProxy config"""
        plugin = IpWhitelistPlugin()
        plugin.configure({
            "allowed_ips": "192.168.1.0/24,10.0.0.1",
            "status_code": "403"
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        assert "IP Whitelist" in result.haproxy_config
        assert "acl whitelisted_ip src 192.168.1.0/24 10.0.0.1" in result.haproxy_config
        assert "http-request deny deny_status 403 if !whitelisted_ip" in result.haproxy_config
        assert result.metadata["domain"] == "example.com"
        assert result.metadata["allowed_ips"] == ["192.168.1.0/24", "10.0.0.1"]
        assert result.metadata["status_code"] == 403

    def test_ip_whitelist_plugin_disabled(self):
        """Test plugin returns empty config when disabled"""
        plugin = IpWhitelistPlugin()
        plugin.configure({"enabled": "false", "allowed_ips": "192.168.1.0/24"})

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com"
        )

        result = plugin.process(context)
        assert result.haproxy_config == ""
        assert result.metadata == {}

    def test_ip_whitelist_plugin_no_ips(self):
        """Test plugin returns empty config when no IPs configured"""
        plugin = IpWhitelistPlugin()

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com"
        )

        result = plugin.process(context)
        assert result.haproxy_config == ""

    def test_ip_whitelist_plugin_in_haproxy_config(self):
        """Test IP Whitelist plugin integration in full HAProxy config generation"""
        # Use fixture with ip_whitelist plugin enabled via labels
        line_list = load_fixture("services-with-ip-whitelist")

        result = {
            "customerrors": False,
            "certbot": {"email": "test@example.com"},
            "stats": {"port": 0}
        }

        cfg = easymapping.HaproxyConfigGenerator(result)
        haproxy_config = cfg.generate(line_list)

        # Verify IP Whitelist config is in the output
        assert "IP Whitelist - Only allow specific IPs" in haproxy_config
        assert "acl whitelisted_ip src 192.168.1.0/24 10.0.0.5" in haproxy_config
        assert "http-request deny deny_status 403 if !whitelisted_ip" in haproxy_config


class TestJwtValidatorPlugin:
    """Test cases for JwtValidatorPlugin (DOMAIN plugin)"""

    def test_jwt_validator_plugin_initialization(self):
        """Test plugin initializes with correct defaults"""
        plugin = JwtValidatorPlugin()
        assert plugin.name == "jwt_validator"
        assert plugin.enabled is True
        assert plugin.algorithm == "RS256"
        assert plugin.issuer is None
        assert plugin.audience is None
        assert plugin.pubkey_path is None
        assert plugin.pubkey is None

    def test_jwt_validator_plugin_configuration(self):
        """Test plugin configuration"""
        plugin = JwtValidatorPlugin()

        # Test basic config
        plugin.configure({
            "algorithm": "RS512",
            "issuer": "https://auth.example.com/",
            "audience": "https://api.example.com",
            "pubkey_path": "/etc/haproxy/keys/api.pem"
        })
        assert plugin.algorithm == "RS512"
        assert plugin.issuer == "https://auth.example.com/"
        assert plugin.audience == "https://api.example.com"
        assert plugin.pubkey_path == "/etc/haproxy/keys/api.pem"

        # Test empty values skip validation (use fresh plugin)
        plugin2 = JwtValidatorPlugin()
        plugin2.configure({
            "issuer": "",
            "audience": ""
        })
        assert plugin2.issuer is None
        assert plugin2.audience is None

        # Test not providing issuer/audience at all (use fresh plugin)
        plugin2b = JwtValidatorPlugin()
        plugin2b.configure({
            "algorithm": "RS256",
            "pubkey_path": "/etc/haproxy/keys/api.pem"
        })
        assert plugin2b.issuer is None
        assert plugin2b.audience is None

        # Test enabled (use fresh plugin)
        plugin3 = JwtValidatorPlugin()
        plugin3.configure({"enabled": "false"})
        assert plugin3.enabled is False

    def test_jwt_validator_plugin_generates_config_with_path(self):
        """Test plugin generates correct HAProxy config using pubkey_path"""
        plugin = JwtValidatorPlugin()
        plugin.configure({
            "algorithm": "RS256",
            "issuer": "https://auth.example.com/",
            "audience": "https://api.example.com",
            "pubkey_path": "/etc/haproxy/jwt_keys/api_pubkey.pem"
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="api.example.com",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        assert "JWT Validator" in result.haproxy_config
        assert "Missing Authorization HTTP header" in result.haproxy_config
        assert "http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg')" in result.haproxy_config
        assert "http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss')" in result.haproxy_config
        assert "http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud')" in result.haproxy_config
        assert "http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int')" in result.haproxy_config
        assert "var(txn.alg) -m str RS256" in result.haproxy_config
        assert "var(txn.iss) -m str https://auth.example.com/" in result.haproxy_config
        assert "var(txn.aud) -m str https://api.example.com" in result.haproxy_config
        assert 'jwt_verify(txn.alg,"/etc/haproxy/jwt_keys/api_pubkey.pem")' in result.haproxy_config
        assert "JWT has expired" in result.haproxy_config
        assert result.metadata["domain"] == "api.example.com"
        assert result.metadata["algorithm"] == "RS256"
        assert result.metadata["validates_issuer"] is True
        assert result.metadata["validates_audience"] is True

    def test_jwt_validator_plugin_generates_config_with_pubkey_content(self):
        """Test plugin generates correct HAProxy config using pubkey content (base64-encoded)"""
        plugin = JwtValidatorPlugin()
        # Base64-encoded version of "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqh...\n-----END PUBLIC KEY-----"
        pubkey_base64 = "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQklqQU5CZ2txaC4uLgotLS0tLUVORCBQVUJMSUMgS0VZLS0tLS0="
        plugin.configure({
            "algorithm": "RS256",
            "pubkey": pubkey_base64
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="api.example.com",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        assert "JWT Validator" in result.haproxy_config
        assert "/etc/haproxy/jwt_keys/api_example_com_pubkey.pem" in result.haproxy_config
        # Verify the decoded content is stored in metadata
        assert result.metadata["pubkey_content"] == "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqh...\n-----END PUBLIC KEY-----"

    def test_jwt_validator_plugin_no_issuer_audience_validation(self):
        """Test plugin skips issuer/audience validation when not configured"""
        plugin = JwtValidatorPlugin()
        plugin.configure({
            "pubkey_path": "/etc/haproxy/jwt_keys/api_pubkey.pem"
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="api.example.com",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        assert "Invalid JWT issuer" not in result.haproxy_config
        assert "Invalid JWT audience" not in result.haproxy_config
        assert result.metadata["validates_issuer"] is False
        assert result.metadata["validates_audience"] is False

    def test_jwt_validator_plugin_disabled(self):
        """Test plugin returns empty config when disabled"""
        plugin = JwtValidatorPlugin()
        plugin.configure({
            "enabled": "false",
            "pubkey_path": "/etc/haproxy/jwt_keys/api_pubkey.pem"
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="api.example.com"
        )

        result = plugin.process(context)
        assert result.haproxy_config == ""
        assert result.metadata == {}

    def test_jwt_validator_plugin_no_pubkey(self):
        """Test plugin returns empty config when no pubkey configured"""
        plugin = JwtValidatorPlugin()

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="api.example.com"
        )

        result = plugin.process(context)
        assert result.haproxy_config == ""

    def test_jwt_validator_plugin_in_haproxy_config(self):
        """Test JWT Validator plugin integration in full HAProxy config generation"""
        line_list = load_fixture("services-with-jwt-validator")

        result = {
            "customerrors": False,
            "certbot": {"email": "test@example.com"},
            "stats": {"port": 0}
        }

        cfg = easymapping.HaproxyConfigGenerator(result)
        haproxy_config = cfg.generate(line_list)

        # Verify JWT Validator config is in the output
        assert "JWT Validator - Validate JWT tokens" in haproxy_config
        assert "Missing Authorization HTTP header" in haproxy_config
        assert "http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg')" in haproxy_config
        assert "jwt_verify" in haproxy_config

    def test_jwt_validator_plugin_with_paths_only_paths_false(self):
        """Test plugin with paths configured and only_paths=false"""
        plugin = JwtValidatorPlugin()
        plugin.configure({
            "pubkey_path": "/etc/haproxy/jwt_keys/api_pubkey.pem",
            "paths": ["/api/admin", "/api/sensitive"],
            "only_paths": "false"
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="api.example.com",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        # Check that ACLs are defined for paths
        assert "acl jwt_protected_path path_beg /api/admin" in result.haproxy_config
        assert "acl jwt_protected_path path_beg /api/sensitive" in result.haproxy_config
        # Check that validation rules have "if jwt_protected_path" condition
        assert "unless { req.hdr(authorization) -m found } if jwt_protected_path" in result.haproxy_config
        assert "http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg') if jwt_protected_path" in result.haproxy_config
        # Check that "Access denied" for non-protected paths is NOT present (only_paths=false)
        assert "Access denied" not in result.haproxy_config
        # Check metadata
        assert result.metadata["path_validation"] is True
        assert result.metadata["only_paths"] is False
        assert result.metadata["paths"] == ["/api/admin", "/api/sensitive"]

    def test_jwt_validator_plugin_with_paths_only_paths_true(self):
        """Test plugin with paths configured and only_paths=true"""
        plugin = JwtValidatorPlugin()
        plugin.configure({
            "pubkey_path": "/etc/haproxy/jwt_keys/api_pubkey.pem",
            "paths": ["/api/public"],
            "only_paths": "true"
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="api.example.com",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        # Check that ACL is defined for path
        assert "acl jwt_protected_path path_beg /api/public" in result.haproxy_config
        # Check that "Access denied" for non-protected paths IS present (only_paths=true)
        assert "http-request deny content-type 'text/html' string 'Access denied' unless jwt_protected_path" in result.haproxy_config
        # Check that validation rules do NOT have "if jwt_protected_path" (since all non-protected paths are denied)
        assert "unless { req.hdr(authorization) -m found } if jwt_protected_path" not in result.haproxy_config
        # The rules should not have any condition suffix when only_paths=true
        assert "http-request deny content-type 'text/html' string 'Missing Authorization HTTP header' unless { req.hdr(authorization) -m found }" in result.haproxy_config
        # Check metadata
        assert result.metadata["path_validation"] is True
        assert result.metadata["only_paths"] is True
        assert result.metadata["paths"] == ["/api/public"]

    def test_jwt_validator_plugin_paths_from_comma_separated_string(self):
        """Test plugin parses comma-separated paths from container labels"""
        plugin = JwtValidatorPlugin()
        plugin.configure({
            "pubkey_path": "/etc/haproxy/jwt_keys/api_pubkey.pem",
            "paths": "/api/admin,/api/sensitive,/api/protected"
        })

        assert plugin.paths == ["/api/admin", "/api/sensitive", "/api/protected"]

    def test_jwt_validator_plugin_paths_from_list(self):
        """Test plugin parses paths from list (YAML config)"""
        plugin = JwtValidatorPlugin()
        plugin.configure({
            "pubkey_path": "/etc/haproxy/jwt_keys/api_pubkey.pem",
            "paths": ["/api/admin", "/api/sensitive"]
        })

        assert plugin.paths == ["/api/admin", "/api/sensitive"]

    def test_jwt_validator_plugin_no_paths_protects_all(self):
        """Test plugin protects all paths when paths is not configured"""
        plugin = JwtValidatorPlugin()
        plugin.configure({
            "pubkey_path": "/etc/haproxy/jwt_keys/api_pubkey.pem"
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="api.example.com",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        # Check that no ACL is defined
        assert "acl jwt_protected_path" not in result.haproxy_config
        # Check that validation rules do NOT have any condition suffix (all paths protected)
        assert "unless { req.hdr(authorization) -m found } if jwt_protected_path" not in result.haproxy_config
        assert "http-request deny content-type 'text/html' string 'Missing Authorization HTTP header' unless { req.hdr(authorization) -m found }" in result.haproxy_config
        # Check metadata
        assert result.metadata["path_validation"] is False


class TestFastcgiPlugin:
    """Test cases for FastcgiPlugin"""

    def test_fastcgi_plugin_initialization(self):
        """Test plugin initializes with correct defaults"""
        plugin = FastcgiPlugin()

        assert plugin.name == "fastcgi"
        assert plugin.enabled is True
        assert plugin.document_root == "/var/www/html"
        assert plugin.index_file == "index.php"
        assert plugin.path_info is True
        assert plugin.custom_params == {}

    def test_fastcgi_plugin_configuration(self):
        """Test plugin configuration"""
        plugin = FastcgiPlugin()
        plugin.configure({
            "document_root": "/var/www/myapp",
            "index_file": "app.php",
            "path_info": "false"
        })

        assert plugin.document_root == "/var/www/myapp"
        assert plugin.index_file == "app.php"
        assert plugin.path_info is False

    def test_fastcgi_plugin_generates_config(self):
        """Test plugin generates correct HAProxy config"""
        plugin = FastcgiPlugin()
        plugin.configure({
            "document_root": "/var/www/html",
            "index_file": "index.php"
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="phpapp.local",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        assert "use-fcgi-app fcgi_phpapp_local" in result.haproxy_config

        # Check fcgi-app definition in metadata
        assert "fcgi_app_definition" in result.metadata
        fcgi_app_def = result.metadata["fcgi_app_definition"]
        assert "fcgi-app fcgi_phpapp_local" in fcgi_app_def
        assert "docroot /var/www/html" in fcgi_app_def
        assert "index index.php" in fcgi_app_def
        assert result.metadata["document_root"] == "/var/www/html"
        assert result.metadata["index_file"] == "index.php"

    def test_fastcgi_plugin_custom_params(self):
        """Test plugin with custom FastCGI parameters"""
        plugin = FastcgiPlugin()
        plugin.configure({
            "custom_params": {
                "CUSTOM_VAR": "custom_value",
                "APP_ENV": "production"
            }
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="phpapp.local",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is not None
        assert "use-fcgi-app fcgi_phpapp_local" in result.haproxy_config

        # Check custom params in fcgi-app definition in metadata
        assert "fcgi_app_definition" in result.metadata
        fcgi_app_def = result.metadata["fcgi_app_definition"]
        assert "set-param CUSTOM_VAR custom_value" in fcgi_app_def
        assert "set-param APP_ENV production" in fcgi_app_def
        assert result.metadata["custom_params_count"] == 2

    def test_fastcgi_plugin_disabled(self):
        """Test plugin returns empty config when disabled"""
        plugin = FastcgiPlugin()
        plugin.configure({"enabled": "false"})

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="phpapp.local",
            port="80",
            host_config={}
        )

        result = plugin.process(context)

        assert result.haproxy_config is None or result.haproxy_config == ""


class TestPluginManager:
    """Test cases for PluginManager"""

    def test_plugin_manager_loads_builtin_plugins(self):
        """Test that plugin manager loads all builtin plugins"""
        manager = PluginManager()
        manager.load_plugins()

        # Verify all builtin plugins are loaded
        assert "cloudflare" in manager.plugins
        assert "cleanup" in manager.plugins
        assert "deny_pages" in manager.plugins
        assert "ip_whitelist" in manager.plugins
        assert "jwt_validator" in manager.plugins
        assert "fastcgi" in manager.plugins

        # Verify plugin types
        assert len(manager.global_plugins) == 1  # cleanup
        assert len(manager.domain_plugins) == 5  # cloudflare, deny_pages, ip_whitelist, jwt_validator, fastcgi

        # Verify plugin instances
        assert manager.plugins["cloudflare"].name == "cloudflare"
        assert manager.plugins["cleanup"].name == "cleanup"
        assert manager.plugins["deny_pages"].name == "deny_pages"
        assert manager.plugins["ip_whitelist"].name == "ip_whitelist"
        assert manager.plugins["jwt_validator"].name == "jwt_validator"

    def test_plugin_manager_executes_global_plugins(self):
        """Test plugin manager executes global plugins correctly"""
        manager = PluginManager()
        manager.load_plugins()

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={}
        )

        # Execute only cleanup plugin
        results = manager.execute_global_plugins(context, enabled_list=["cleanup"])

        assert len(results) == 1
        assert results[0].haproxy_config == ""  # Cleanup doesn't generate config

    def test_plugin_manager_executes_domain_plugins(self):
        """Test plugin manager executes domain plugins correctly"""
        manager = PluginManager()
        manager.load_plugins()

        # Configure deny_pages
        manager.configure_plugins({
            "deny_pages": {
                "paths": "/admin,/private",
                "status_code": "403"
            }
        })

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com",
            port="80",
            host_config={}
        )

        # Execute both domain plugins
        results = manager.execute_domain_plugins(context, enabled_list=["cloudflare", "deny_pages"])

        assert len(results) == 2

        # Verify configs were generated
        configs = [r.haproxy_config for r in results if r.haproxy_config]
        assert len(configs) == 2

        # Verify both plugin outputs
        all_config = "\n".join(configs)
        assert "Cloudflare" in all_config
        assert "Deny Pages" in all_config

    def test_plugin_manager_empty_enabled_list(self):
        """Test that empty enabled list means no plugins execute"""
        manager = PluginManager()
        manager.load_plugins()

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com"
        )

        # Execute with empty list - should execute nothing
        results = manager.execute_domain_plugins(context, enabled_list=[])
        assert len(results) == 0

        results = manager.execute_global_plugins(context, enabled_list=[])
        assert len(results) == 0


class TestMultiplePluginsCombined:
    """Test cases for multiple plugins working together"""

    def test_multiple_plugins_in_haproxy_config(self):
        """Test multiple plugins working together in HAProxy config"""
        # Use fixture with both plugins enabled via labels
        line_list = load_fixture("services-with-multiple-plugins")

        # Enable cleanup plugin globally
        result = {
            "customerrors": False,
            "certbot": {"email": "test@example.com"},
            "stats": {"port": 0},
            "plugins": {
                "enabled": ["cleanup"],
                "config": {
                    "cleanup": {
                        "max_idle_time": "600"
                    }
                }
            }
        }

        cfg = easymapping.HaproxyConfigGenerator(result)
        haproxy_config = cfg.generate(line_list)

        # Verify both domain plugins are in the output
        assert "Cloudflare - Restore original visitor IP" in haproxy_config
        assert "Deny Pages - Block specific paths" in haproxy_config
        assert "acl from_cloudflare" in haproxy_config
        assert "acl denied_path path_beg /admin /private" in haproxy_config

        # Cleanup doesn't add to config
        assert "cleanup" not in haproxy_config.lower()

    def test_plugins_order_in_output(self):
        """Test that plugins maintain consistent order in output"""
        # Use fixture with both plugins enabled via labels
        line_list = load_fixture("services-with-multiple-plugins")

        result = {
            "customerrors": False,
            "certbot": {"email": "test@example.com"},
            "stats": {"port": 0}
        }

        cfg = easymapping.HaproxyConfigGenerator(result)
        haproxy_config = cfg.generate(line_list)

        # Find positions of plugin configs
        cloudflare_pos = haproxy_config.find("Cloudflare")
        deny_pages_pos = haproxy_config.find("Deny Pages")

        # Both should be present
        assert cloudflare_pos != -1
        assert deny_pages_pos != -1

        # They should appear in backend sections (not in global/defaults)
        assert cloudflare_pos > haproxy_config.find("backend srv_")
        assert deny_pages_pos > haproxy_config.find("backend srv_")
