"""
Cloudflare Plugin for EasyHAProxy

This plugin restores the original visitor IP address from Cloudflare's
CF-Connecting-IP header when requests come through Cloudflare's CDN.

The plugin includes built-in Cloudflare IP ranges that are automatically
updated and written to the IP list file.

Configuration:
    - ip_list_path: Path to file containing Cloudflare IP ranges (default: /etc/haproxy/cloudflare_ips.lst)
    - use_builtin_ips: Use built-in Cloudflare IP ranges (default: true)

Example YAML config:
    plugins:
      cloudflare:
        enabled: true
        ip_list_path: /etc/haproxy/cloudflare_ips.lst
        use_builtin_ips: true

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
from functions import loggerEasyHaproxy


class CloudflarePlugin(PluginInterface):
    """Plugin to restore original visitor IP from Cloudflare"""

    # Current Cloudflare IP ranges (IPv4 and IPv6)
    # Source: https://www.cloudflare.com/ips/
    CLOUDFLARE_IPS = [
        # IPv4
        "173.245.48.0/20",
        "103.21.244.0/22",
        "103.22.200.0/22",
        "103.31.4.0/22",
        "141.101.64.0/18",
        "108.162.192.0/18",
        "190.93.240.0/20",
        "188.114.96.0/20",
        "197.234.240.0/22",
        "198.41.128.0/17",
        "162.158.0.0/15",
        "104.16.0.0/13",
        "104.24.0.0/14",
        "172.64.0.0/13",
        "131.0.72.0/22",
        # IPv6
        "2400:cb00::/32",
        "2606:4700::/32",
        "2803:f800::/32",
        "2405:b500::/32",
        "2405:8100::/32",
        "2a06:98c0::/29",
        "2c0f:f248::/32",
    ]

    def __init__(self):
        self.ip_list_path = "/etc/haproxy/cloudflare_ips.lst"
        self.enabled = True
        self.use_builtin_ips = True

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
                - use_builtin_ips: Use built-in Cloudflare IP ranges (default: true)
        """
        if "ip_list_path" in config:
            self.ip_list_path = config["ip_list_path"]

        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "use_builtin_ips" in config:
            self.use_builtin_ips = str(config["use_builtin_ips"]).lower() in ["true", "1", "yes"]

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

        # Write built-in Cloudflare IPs to file if using built-in IPs
        if self.use_builtin_ips:
            try:
                # Create directory if it doesn't exist
                ip_list_dir = os.path.dirname(self.ip_list_path)
                if ip_list_dir and not os.path.exists(ip_list_dir):
                    os.makedirs(ip_list_dir, exist_ok=True)

                # Write Cloudflare IPs to file
                with open(self.ip_list_path, 'w') as f:
                    for ip_range in self.CLOUDFLARE_IPS:
                        f.write(f"{ip_range}\n")

                loggerEasyHaproxy.info(f"Cloudflare plugin: Written {len(self.CLOUDFLARE_IPS)} IP ranges to {self.ip_list_path}")
            except Exception as e:
                loggerEasyHaproxy.warning(f"Cloudflare plugin: Failed to write IP list to {self.ip_list_path}: {e}")

        # Generate HAProxy config snippet
        haproxy_config = f"""# Cloudflare - Restore original visitor IP
acl from_cloudflare src -f {self.ip_list_path}
http-request set-header X-Forwarded-For %[req.hdr(CF-Connecting-IP)] if from_cloudflare"""

        return PluginResult(
            haproxy_config=haproxy_config,
            modified_easymapping=None,
            metadata={
                "domain": context.domain,
                "ip_list_path": self.ip_list_path,
                "use_builtin_ips": self.use_builtin_ips,
                "ip_count": len(self.CLOUDFLARE_IPS) if self.use_builtin_ips else None
            }
        )
