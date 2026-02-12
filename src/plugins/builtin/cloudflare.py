"""
Cloudflare Plugin for EasyHAProxy

This plugin restores the original visitor IP address from Cloudflare's
CF-Connecting-IP header when requests come through Cloudflare's CDN.

The plugin includes built-in Cloudflare IP ranges that are automatically
updated and written to the IP list file.

Configuration:
    - ip_list_path: Path to file containing Cloudflare IP ranges (default: /etc/haproxy/cloudflare_ips.lst)
    - ip_list: Base64-encoded list of IP ranges (one per line), takes precedence over ip_list_path
    - use_builtin_ips: Use built-in Cloudflare IP ranges (default: true)
    - update_log_format: Update HAProxy log format to show real visitor IP (default: true)

Example YAML config:
    plugins:
      cloudflare:
        enabled: true
        ip_list_path: /etc/haproxy/cloudflare_ips.lst
        use_builtin_ips: true
        update_log_format: true

Example Kubernetes Ingress Annotation:
    easyhaproxy.plugins: "cloudflare"
    easyhaproxy.plugin.cloudflare.ip_list: "MTAuMC4wLjAvOAoxNzIuMTYuMC4wLzEyCjE5Mi4xNjguMC4wLzE2Cg=="
    easyhaproxy.plugin.cloudflare.update_log_format: "true"

Example Container Label:
    easyhaproxy.http.plugins: "cloudflare"
    easyhaproxy.http.plugin.cloudflare.update_log_format: "true"

HAProxy Config Generated:
    # Cloudflare - Restore original visitor IP
    acl from_cloudflare src -f /etc/haproxy/cloudflare_ips.lst
    http-request set-var(txn.real_ip) req.hdr(CF-Connecting-IP) if from_cloudflare
    http-request set-header X-Forwarded-For %[var(txn.real_ip)] if from_cloudflare

Log Format (when update_log_format=true):
    Shows real visitor IP alongside connection IP for debugging
    Format: real_ip/connection_ip [timestamp] request status bytes ...
"""

import base64
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from functions import logger_easyhaproxy
from plugins import PluginContext, PluginInterface, PluginResult, PluginType


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
        self.update_log_format = True
        self.ip_list = None

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
                - ip_list: Base64-encoded list of IP ranges (one per line)
                - enabled: Whether plugin is enabled
                - use_builtin_ips: Use built-in Cloudflare IP ranges (default: true)
                - update_log_format: Update HAProxy log format to show real IP (default: true)
        """
        if "ip_list_path" in config:
            self.ip_list_path = config["ip_list_path"]

        if "ip_list" in config:
            # Decode from base64 (consistent with JWT validator pubkey parameter)
            try:
                self.ip_list = base64.b64decode(config["ip_list"]).decode('utf-8')
            except Exception as e:
                logger_easyhaproxy.warning(f"Cloudflare plugin: Failed to decode ip_list: {e}")
                self.ip_list = None

        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "use_builtin_ips" in config:
            self.use_builtin_ips = str(config["use_builtin_ips"]).lower() in ["true", "1", "yes"]

        if "update_log_format" in config:
            self.update_log_format = str(config["update_log_format"]).lower() in ["true", "1", "yes"]

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

        # Determine which IPs to write to file
        ips_to_write = None
        ip_source = None

        if self.ip_list:
            # Priority 1: Base64-encoded ip_list from annotation
            ip_lines = [line.strip() for line in self.ip_list.split('\n') if line.strip()]
            ips_to_write = ip_lines
            ip_source = "base64 ip_list"
        elif self.use_builtin_ips:
            # Priority 2: Built-in Cloudflare IPs
            ips_to_write = self.CLOUDFLARE_IPS
            ip_source = "built-in IPs"

        # Write IPs to file if we have any
        if ips_to_write:
            try:
                # Create directory if needed
                ip_list_dir = os.path.dirname(self.ip_list_path)
                if ip_list_dir and not os.path.exists(ip_list_dir):
                    os.makedirs(ip_list_dir, exist_ok=True)

                # Write IPs to file
                with open(self.ip_list_path, 'w') as f:
                    for ip_range in ips_to_write:
                        f.write(f"{ip_range}\n")

                logger_easyhaproxy.info(
                    f"Cloudflare plugin: Written {len(ips_to_write)} IP ranges "
                    f"from {ip_source} to {self.ip_list_path}"
                )
            except Exception as e:
                logger_easyhaproxy.warning(
                    f"Cloudflare plugin: Failed to write IP list to {self.ip_list_path}: {e}"
                )

        # Generate HAProxy config snippet for backend
        haproxy_config = f"""# Cloudflare - Restore original visitor IP
acl from_cloudflare src -f {self.ip_list_path}
http-request set-var(txn.real_ip) req.hdr(CF-Connecting-IP) if from_cloudflare
http-request set-header X-Forwarded-For %[var(txn.real_ip)] if from_cloudflare"""

        # Generate log format config (frontend level)
        # Industry-standard format: real_ip/proxy_ip [time] request status bytes timings
        # Based on HAProxy HTTP log format with real IP shown first
        log_format_config = None
        if self.update_log_format:
            log_format_config = """# Cloudflare - Enhanced log format showing real visitor IP
log-format "%{+Q}[var(txn.real_ip)]:-/%ci:%cp [%tr] %ft %b/%s %TR/%Tw/%Tc/%Tr/%Ta %ST %B %CC %CS %tsc %ac/%fc/%bc/%sc/%rc %sq/%bq %hr %hs %{+Q}r\""""

        return PluginResult(
            haproxy_config=haproxy_config,
            modified_easymapping=None,
            metadata={
                "domain": context.domain,
                "ip_list_path": self.ip_list_path,
                "ip_list_provided": self.ip_list is not None,
                "use_builtin_ips": self.use_builtin_ips,
                "update_log_format": self.update_log_format,
                "defaults_config": log_format_config,
                "ip_count": len(ips_to_write) if ips_to_write else None,
                "ip_source": ip_source if ips_to_write else "existing file"
            }
        )
