"""
FastCGI Plugin for EasyHAProxy

This plugin generates HAProxy fcgi-app configuration for PHP-FPM and other FastCGI applications.
It runs as a DOMAIN plugin (once per domain).

The plugin creates:
    1. A top-level fcgi-app section with CGI parameter definitions
    2. A use-fcgi-app directive in the backend

Configuration:
    - enabled: Enable/disable the plugin (default: true)
    - document_root: Document root path (default: /var/www/html)
    - script_filename: Pattern for SCRIPT_FILENAME (default: %[path])
    - index_file: Default index file (default: index.php)
    - path_info: Enable PATH_INFO support (default: true)
    - custom_params: Dictionary of custom FastCGI parameters (optional)

Example YAML config:
    plugins:
      fastcgi:
        enabled: true
        document_root: /var/www/html
        index_file: index.php
        path_info: true

Example Container Label:
    easyhaproxy.http.plugins: "fastcgi"
    easyhaproxy.http.plugin.fastcgi.document_root: /var/www/myapp
    easyhaproxy.http.plugin.fastcgi.index_file: index.php
    easyhaproxy.http.plugin.fastcgi.path_info: true

Example Kubernetes Annotation:
    easyhaproxy.plugins: "fastcgi"
    easyhaproxy.plugin.fastcgi.document_root: /var/www/myapp
    easyhaproxy.plugin.fastcgi.index_file: index.php
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginContext, PluginInterface, PluginResult, PluginType


class FastcgiPlugin(PluginInterface):
    """Plugin to configure FastCGI parameters for PHP-FPM"""

    def __init__(self):
        self.enabled = True
        self.document_root = "/var/www/html"
        self.script_filename = "%[path]"
        self.index_file = "index.php"
        self.path_info = True
        self.custom_params = {}

    @property
    def name(self) -> str:
        return "fastcgi"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        """
        Configure the plugin

        Args:
            config: Dictionary with configuration options
                - enabled: Whether plugin is enabled
                - document_root: Document root path
                - script_filename: Pattern for SCRIPT_FILENAME
                - index_file: Default index file
                - path_info: Enable PATH_INFO support
                - custom_params: Dictionary of custom FastCGI parameters
        """
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "document_root" in config:
            self.document_root = config["document_root"]

        if "script_filename" in config:
            self.script_filename = config["script_filename"]

        if "index_file" in config:
            self.index_file = config["index_file"]

        if "path_info" in config:
            self.path_info = str(config["path_info"]).lower() in ["true", "1", "yes"]

        if "custom_params" in config:
            self.custom_params = config["custom_params"]

    def process(self, context: PluginContext) -> PluginResult:
        """
        Process the plugin and generate FastCGI configuration

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with HAProxy FastCGI configuration
        """
        if not self.enabled:
            return PluginResult()

        # Generate a unique fcgi-app name based on the domain
        # Replace dots and colons with underscores for valid HAProxy identifier
        domain_safe = context.domain.replace(".", "_").replace(":", "_")
        fcgi_app_name = f"fcgi_{domain_safe}"

        # Generate the use-fcgi-app directive for the backend
        backend_config = f"use-fcgi-app {fcgi_app_name}"

        # Generate the fcgi-app section (to be inserted at top level)
        fcgi_app_lines = [f"fcgi-app {fcgi_app_name}"]
        fcgi_app_lines.append(f"    docroot {self.document_root}")
        fcgi_app_lines.append(f"    index {self.index_file}")

        # PATH_INFO support
        if self.path_info:
            fcgi_app_lines.append("    path-info ^(/.+\\.php)(/.*)?$")

        # Set SCRIPT_FILENAME if customized
        if self.script_filename and self.script_filename != "%[path]":
            fcgi_app_lines.append(f"    set-param SCRIPT_FILENAME {self.script_filename}")

        # Custom parameters
        if self.custom_params:
            for param_name, param_value in self.custom_params.items():
                fcgi_app_lines.append(f"    set-param {param_name.upper()} {param_value}")

        fcgi_app_definition = "\n".join(fcgi_app_lines)

        # Build metadata
        metadata = {
            "domain": context.domain,
            "fcgi_app_name": fcgi_app_name,
            "document_root": self.document_root,
            "index_file": self.index_file,
            "path_info": self.path_info,
            "custom_params_count": len(self.custom_params)
        }

        return PluginResult(
            haproxy_config=backend_config,  # use-fcgi-app directive for the backend
            modified_easymapping=None,
            metadata=metadata,
            global_configs=[fcgi_app_definition]  # For top-level injection
        )
