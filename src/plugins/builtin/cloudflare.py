"""
Cloudflare Plugin for EasyHAProxy

This plugin restores the original visitor IP address from Cloudflare's
CF-Connecting-IP header when requests come through Cloudflare's CDN.

Configuration:
    - ip_list_path: Path to file containing Cloudflare IP ranges (default: /etc/haproxy/cloudflare_ips.lst)

Example YAML config:
    plugins:
      cloudflare:
        enabled: true
        ip_list_path: /etc/haproxy/cloudflare_ips.lst

Example Container Label:
    easyhaproxy.http.plugins: "cloudflare"

HAProxy Config Generated:
    # Cloudflare - Restore original visitor IP
    acl from_cloudflare src -f /etc/haproxy/cloudflare_ips.lst
    http-request set-header X-Forwarded-For %[req.hdr(CF-Connecting-IP)] if from_cloudflare
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult


class CloudflarePlugin(PluginInterface):
    """Plugin to restore original visitor IP from Cloudflare"""

    def __init__(self):
        self.ip_list_path = "/etc/haproxy/cloudflare_ips.lst"
        self.enabled = True

    @property
    def name(self) -> str:
        return "cloudflare"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        """
        Configure the plugin

        Args:
            config: Dictionary with configuration options
                - ip_list_path: Path to Cloudflare IP list file
                - enabled: Whether plugin is enabled
        """
        if "ip_list_path" in config:
            self.ip_list_path = config["ip_list_path"]

        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

    def process(self, context: PluginContext) -> PluginResult:
        """
        Generate HAProxy config to restore original IP from Cloudflare

        Args:
            context: Plugin execution context with domain information

        Returns:
            PluginResult with HAProxy configuration snippet
        """
        if not self.enabled:
            return PluginResult()

        # Generate HAProxy config snippet
        haproxy_config = f"""# Cloudflare - Restore original visitor IP
acl from_cloudflare src -f {self.ip_list_path}
http-request set-header X-Forwarded-For %[req.hdr(CF-Connecting-IP)] if from_cloudflare"""

        return PluginResult(
            haproxy_config=haproxy_config,
            modified_easymapping=None,
            metadata={
                "domain": context.domain,
                "ip_list_path": self.ip_list_path
            }
        )
