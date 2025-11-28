"""
IP Whitelist Plugin for EasyHAProxy

This plugin restricts access to a domain to only specific IP addresses or CIDR ranges.
It runs as a DOMAIN plugin (once per domain).

Configuration:
    - enabled: Enable/disable the plugin (default: true)
    - allowed_ips: Comma-separated list of IPs/CIDR ranges to allow
    - status_code: HTTP status code to return for blocked IPs (default: 403)

Example YAML config:
    plugins:
      ip_whitelist:
        enabled: true
        allowed_ips: "192.168.1.0/24,10.0.0.1,172.16.0.0/16"
        status_code: 403

Example Container Label:
    easyhaproxy.http.plugins: "ip_whitelist"
    easyhaproxy.http.plugin.ip_whitelist.allowed_ips: "192.168.1.0/24,10.0.0.1"
    easyhaproxy.http.plugin.ip_whitelist.status_code: 403

HAProxy Config Generated:
    # IP Whitelist - Only allow specific IPs
    acl whitelisted_ip src 192.168.1.0/24 10.0.0.1
    http-request deny deny_status 403 if !whitelisted_ip
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult


class IpWhitelistPlugin(PluginInterface):
    """Plugin to restrict access to specific IP addresses"""

    def __init__(self):
        self.enabled = True
        self.allowed_ips = []
        self.status_code = 403

    @property
    def name(self) -> str:
        return "ip_whitelist"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        """
        Configure the plugin

        Args:
            config: Dictionary with configuration options
                - enabled: Whether plugin is enabled
                - allowed_ips: Comma-separated list of IPs/CIDR ranges
                - status_code: HTTP status code to return for denied requests
        """
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "allowed_ips" in config:
            ips_str = str(config["allowed_ips"])
            self.allowed_ips = [ip.strip() for ip in ips_str.split(",") if ip.strip()]

        if "status_code" in config:
            try:
                self.status_code = int(config["status_code"])
            except ValueError:
                self.status_code = 403

    def process(self, context: PluginContext) -> PluginResult:
        """
        Generate HAProxy config to whitelist specific IPs

        Args:
            context: Plugin execution context with domain information

        Returns:
            PluginResult with HAProxy configuration snippet
        """
        if not self.enabled or not self.allowed_ips:
            return PluginResult()

        # Create space-separated list of IPs for ACL
        ips_str = " ".join(self.allowed_ips)

        # Generate HAProxy config snippet
        haproxy_config = f"""# IP Whitelist - Only allow specific IPs
acl whitelisted_ip src {ips_str}
http-request deny deny_status {self.status_code} if !whitelisted_ip"""

        return PluginResult(
            haproxy_config=haproxy_config,
            modified_easymapping=None,
            metadata={
                "domain": context.domain,
                "allowed_ips": self.allowed_ips,
                "status_code": self.status_code
            }
        )
