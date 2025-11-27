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

        # Verify plugin types
        assert len(manager.global_plugins) == 1  # cleanup
        assert len(manager.domain_plugins) == 2  # cloudflare, deny_pages

        # Verify plugin instances
        assert manager.plugins["cloudflare"].name == "cloudflare"
        assert manager.plugins["cleanup"].name == "cleanup"
        assert manager.plugins["deny_pages"].name == "deny_pages"

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
