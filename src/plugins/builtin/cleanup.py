"""
Cleanup Plugin for EasyHAProxy

This plugin performs cleanup tasks during each discovery cycle.
It runs as a GLOBAL plugin (once per cycle).

Configuration:
    - enabled: Enable/disable the plugin (default: true)
    - max_idle_time: Maximum idle time before cleanup in seconds (default: 300)
    - cleanup_temp_files: Clean up temporary files (default: true)

Example YAML config:
    plugins:
      cleanup:
        enabled: true
        max_idle_time: 300
        cleanup_temp_files: true

Example Environment Variable:
    EASYHAPROXY_PLUGINS_ENABLED=cleanup
    EASYHAPROXY_PLUGIN_CLEANUP_MAX_IDLE_TIME=600
"""

import glob
import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from functions import logger_easyhaproxy
from plugins import PluginContext, PluginInterface, PluginResult, PluginType


class CleanupPlugin(PluginInterface):
    """Plugin to perform cleanup tasks during discovery cycle"""

    def __init__(self):
        self.enabled = True
        self.max_idle_time = 300  # 5 minutes
        self.cleanup_temp_files = True

    @property
    def name(self) -> str:
        return "cleanup"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.GLOBAL

    def configure(self, config: dict) -> None:
        """
        Configure the plugin

        Args:
            config: Dictionary with configuration options
                - enabled: Whether plugin is enabled
                - max_idle_time: Maximum idle time in seconds
                - cleanup_temp_files: Whether to clean up temp files
        """
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "max_idle_time" in config:
            try:
                self.max_idle_time = int(config["max_idle_time"])
            except ValueError:
                logger_easyhaproxy.warning(f"Invalid max_idle_time value: {config['max_idle_time']}, using default")

        if "cleanup_temp_files" in config:
            self.cleanup_temp_files = str(config["cleanup_temp_files"]).lower() in ["true", "1", "yes"]

    def process(self, context: PluginContext) -> PluginResult:
        """
        Perform cleanup tasks

        Args:
            context: Plugin execution context

        Returns:
            PluginResult with metadata about cleanup actions
        """
        if not self.enabled:
            return PluginResult()

        cleanup_actions = []

        # Cleanup temporary files
        if self.cleanup_temp_files:
            temp_dirs = ["/tmp", "/var/tmp"]
            current_time = time.time()

            for temp_dir in temp_dirs:
                if not os.path.exists(temp_dir):
                    continue

                try:
                    # Find old EasyHAProxy temp files
                    pattern = os.path.join(temp_dir, "easyhaproxy_*")
                    for filepath in glob.glob(pattern):
                        try:
                            file_age = current_time - os.path.getmtime(filepath)
                            if file_age > self.max_idle_time:
                                os.remove(filepath)
                                cleanup_actions.append(f"Removed old temp file: {filepath}")
                                logger_easyhaproxy.debug(f"Cleanup plugin: Removed {filepath}")
                        except Exception as e:
                            logger_easyhaproxy.warning(f"Failed to remove temp file {filepath}: {e}")
                except Exception as e:
                    logger_easyhaproxy.warning(f"Failed to cleanup {temp_dir}: {e}")

        # Log cleanup summary
        if cleanup_actions:
            logger_easyhaproxy.info(f"Cleanup plugin: Performed {len(cleanup_actions)} cleanup action(s)")

        return PluginResult(
            haproxy_config="",  # No HAProxy config needed for cleanup
            modified_easymapping=None,
            metadata={
                "actions_performed": len(cleanup_actions),
                "actions": cleanup_actions
            }
        )
