import importlib.util
import os
import sys

from functions import Consts, logger_easyhaproxy

from .interface import PluginInterface
from .types import PluginContext, PluginResult, PluginType


class PluginManager:
    """Manages plugin loading, configuration, and execution"""

    def __init__(self, plugins_dir: str | None = None, abort_on_error: bool = False):
        """
        Initialize the plugin manager

        Args:
            plugins_dir: Directory containing plugin files (defaults to EASYHAPROXY_PLUGINS_DIR env var or /etc/easyhaproxy/plugins)
            abort_on_error: If True, abort on plugin errors; if False, log and continue
        """
        self.plugins_dir = plugins_dir or os.getenv(
            "EASYHAPROXY_PLUGINS_DIR",
            Consts.base_path + "/plugins"
        )
        self.abort_on_error = abort_on_error
        self.plugins: dict[str, PluginInterface] = {}
        self.global_plugins: list[PluginInterface] = []
        self.domain_plugins: list[PluginInterface] = []
        self.logger = logger_easyhaproxy

    def load_plugins(self) -> None:
        """
        Discover and load plugins from the plugins directory
        Loads both builtin plugins and external plugins
        """
        # Load builtin plugins first
        builtin_dir = os.path.join(os.path.dirname(__file__), "builtin")
        self._load_plugins_from_directory(builtin_dir, "builtin")

        # Load external plugins from /etc/easyhaproxy/plugins
        if os.path.exists(self.plugins_dir):
            self._load_plugins_from_directory(self.plugins_dir, "external")
        else:
            self.logger.debug(f"Plugin directory {self.plugins_dir} does not exist, skipping external plugins")

    def _load_plugins_from_directory(self, directory: str, source: str) -> None:
        """
        Load plugins from a specific directory

        Args:
            directory: Path to directory containing plugins
            source: Source identifier ("builtin" or "external")
        """
        if not os.path.exists(directory):
            return

        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                filepath = os.path.join(directory, filename)
                module_name = f"plugins.{source}.{filename[:-3]}"

                try:
                    # Load module from file
                    spec = importlib.util.spec_from_file_location(module_name, filepath)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)

                        # Find plugin classes in module
                        for item_name in dir(module):
                            item = getattr(module, item_name)
                            if (isinstance(item, type) and
                                issubclass(item, PluginInterface) and
                                item is not PluginInterface):
                                # Instantiate plugin
                                plugin = item()
                                self.plugins[plugin.name] = plugin

                                # Categorize by type
                                if plugin.plugin_type == PluginType.GLOBAL:
                                    self.global_plugins.append(plugin)
                                elif plugin.plugin_type == PluginType.DOMAIN:
                                    self.domain_plugins.append(plugin)

                                self.logger.debug(f"Loaded {source} plugin: {plugin.name} ({plugin.plugin_type.value})")

                except Exception as e:
                    self._handle_error(f"Failed to load plugin from {filepath}: {str(e)}")

    def configure_plugins(self, plugins_config: dict) -> None:
        """
        Configure all loaded plugins with their settings

        Args:
            plugins_config: Plugin configuration from YAML/env
                          Format: {"plugin_name": {"key": "value"}, ...}
        """
        for plugin_name, plugin in self.plugins.items():
            try:
                # Get plugin-specific config
                plugin_cfg = plugins_config.get(plugin_name, {})

                # Also check "config" sub-key for env var configs
                if "config" in plugins_config and plugin_name in plugins_config["config"]:
                    plugin_cfg.update(plugins_config["config"][plugin_name])

                # Configure plugin
                plugin.configure(plugin_cfg)
                self.logger.debug(f"Configured plugin: {plugin_name} with config: {plugin_cfg}")

            except Exception as e:
                self._handle_error(f"Failed to configure plugin '{plugin_name}': {str(e)}")

    def initialize_plugins(self) -> None:
        """Initialize all plugins and process their resource requests"""
        for plugin_name, plugin in self.plugins.items():
            try:
                result = plugin.initialize()
                self._process_initialization_result(plugin_name, result)
            except Exception as e:
                self._handle_error(f"Plugin '{plugin_name}' initialization failed: {e}")

    def _process_initialization_result(self, plugin_name: str, result) -> None:
        """
        Process plugin initialization requests

        Args:
            plugin_name: Name of the plugin
            result: InitializationResult with resource requests
        """
        for resource in result.resources:
            if resource.resource_type == "directory":
                os.makedirs(resource.path, exist_ok=True)
                self.logger.debug(f"Plugin '{plugin_name}' created directory: {resource.path}")
            elif resource.resource_type == "file":
                if resource.overwrite or not os.path.exists(resource.path):
                    with open(resource.path, 'w') as f:
                        f.write(resource.content or "")
                    self.logger.debug(f"Plugin '{plugin_name}' created file: {resource.path}")

    def execute_global_plugins(self, context: PluginContext, enabled_list: list[str] | None = None) -> list[PluginResult]:
        """
        Execute all global plugins

        Args:
            context: PluginContext with execution data
            enabled_list: Optional list of plugin names to execute. If None, execute all.

        Returns:
            List of PluginResult from each plugin
        """
        results = []

        for plugin in self.global_plugins:
            # Check if plugin is in enabled list (if provided)
            if enabled_list is not None and plugin.name not in enabled_list:
                continue

            try:
                self.logger.debug(f"Executing global plugin: {plugin.name}")
                result = plugin.process(context)
                results.append(result)

                if result.metadata:
                    self.logger.debug(f"Plugin {plugin.name} metadata: {result.metadata}")

            except Exception as e:
                self._handle_error(f"Global plugin '{plugin.name}' failed: {str(e)}")

        return results

    def execute_domain_plugins(self, context: PluginContext, enabled_list: list[str] | None = None) -> list[PluginResult]:
        """
        Execute all domain plugins for a specific domain

        Args:
            context: PluginContext with domain-specific data
            enabled_list: Optional list of plugin names to execute. If None, execute all.

        Returns:
            List of PluginResult from each plugin
        """
        results = []

        for plugin in self.domain_plugins:
            # Check if plugin is in enabled list (if provided)
            if enabled_list is not None and plugin.name not in enabled_list:
                continue

            try:
                self.logger.debug(f"Executing domain plugin: {plugin.name} for domain: {context.domain}")
                result = plugin.process(context)
                results.append(result)

                if result.metadata:
                    self.logger.debug(f"Plugin {plugin.name} metadata: {result.metadata}")

            except Exception as e:
                self._handle_error(f"Domain plugin '{plugin.name}' failed for domain '{context.domain}': {str(e)}")

        return results

    def _handle_error(self, message: str) -> None:
        """
        Handle plugin errors according to abort_on_error setting

        Args:
            message: Error message to log
        """
        if self.abort_on_error:
            self.logger.error(message)
            raise RuntimeError(message)
        else:
            self.logger.warning(message)