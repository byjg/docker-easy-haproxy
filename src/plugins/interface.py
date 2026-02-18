from abc import ABC, abstractmethod

from .types import InitializationResult, PluginContext, PluginResult, PluginType


class PluginInterface(ABC):
    """Base class all plugins must inherit"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique plugin name"""
        pass

    @property
    @abstractmethod
    def plugin_type(self) -> PluginType:
        """Return the plugin type (GLOBAL or DOMAIN)"""
        pass

    @abstractmethod
    def configure(self, config: dict) -> None:
        """
        Configure the plugin with settings from YAML/env/labels

        Args:
            config: Dictionary with plugin-specific configuration
        """
        pass

    @abstractmethod
    def process(self, context: PluginContext) -> PluginResult:
        """
        Process the plugin logic and return result

        Args:
            context: PluginContext with all necessary data

        Returns:
            PluginResult with HAProxy config snippets and/or modified data
        """
        pass

    def initialize(self) -> InitializationResult:
        """
        Initialize plugin resources. Default: no-op for backward compatibility

        Returns:
            InitializationResult with resource requests
        """
        return InitializationResult()