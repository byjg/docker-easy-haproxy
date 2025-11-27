"""
Deny Pages Plugin for EasyHAProxy

This plugin blocks access to specific paths for a domain.
It runs as a DOMAIN plugin (once per domain).

Configuration:
    - enabled: Enable/disable the plugin (default: true)
    - paths: Comma-separated list of paths to deny (e.g., "/admin,/private")
    - status_code: HTTP status code to return (default: 403)

Example YAML config:
    plugins:
      deny_pages:
        enabled: true
        paths: "/admin,/private,/internal"
        status_code: 403

Example Container Label:
    easyhaproxy.http.plugins: "deny_pages"
    easyhaproxy.http.plugin.deny_pages.paths: "/admin,/private"

HAProxy Config Generated:
    # Deny Pages - Block specific paths
    acl denied_path path_beg /admin /private
    http-request deny deny_status 403 if denied_path
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult


class DenyPagesPlugin(PluginInterface):
    """Plugin to deny access to specific paths"""

    def __init__(self):
        self.enabled = True
        self.paths = []
        self.status_code = 403

    @property
    def name(self) -> str:
        return "deny_pages"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        """
        Configure the plugin

        Args:
            config: Dictionary with configuration options
                - enabled: Whether plugin is enabled
                - paths: Comma-separated list of paths to deny
                - status_code: HTTP status code to return
        """
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "paths" in config:
            paths_str = str(config["paths"])
            self.paths = [p.strip() for p in paths_str.split(",") if p.strip()]

        if "status_code" in config:
            try:
                self.status_code = int(config["status_code"])
            except ValueError:
                self.status_code = 403

    def process(self, context: PluginContext) -> PluginResult:
        """
        Generate HAProxy config to deny specific paths

        Args:
            context: Plugin execution context with domain information

        Returns:
            PluginResult with HAProxy configuration snippet
        """
        if not self.enabled or not self.paths:
            return PluginResult()

        # Create path list for ACL
        paths_str = " ".join(self.paths)

        # Generate HAProxy config snippet
        haproxy_config = f"""# Deny Pages - Block specific paths
    acl denied_path path_beg {paths_str}
    http-request deny deny_status {self.status_code} if denied_path"""

        return PluginResult(
            haproxy_config=haproxy_config,
            modified_easymapping=None,
            metadata={
                "domain": context.domain,
                "blocked_paths": self.paths,
                "status_code": self.status_code
            }
        )
