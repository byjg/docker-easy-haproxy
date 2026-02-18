from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PluginType(Enum):
    """Plugin execution types"""
    GLOBAL = "global"    # Execute once per discovery cycle
    DOMAIN = "domain"    # Execute per domain/host


@dataclass
class PluginContext:
    """Container for all plugin execution data"""
    parsed_object: dict              # {IP: labels} from discovery
    easymapping: list               # Current HAProxy mapping structure
    container_env: dict             # Environment configuration
    domain: str | None = None    # Domain name (for DOMAIN plugins)
    port: str | None = None      # Port (for DOMAIN plugins)
    host_config: dict | None = None  # Domain-specific config


@dataclass
class ResourceRequest:
    """Request for file system resources"""
    resource_type: str  # "directory" or "file"
    path: str
    content: str | None = None
    overwrite: bool = False


@dataclass
class InitializationResult:
    """Plugin initialization result with resource requests"""
    resources: list[ResourceRequest] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResult:
    """Plugin execution result"""
    haproxy_config: str = ""                     # HAProxy config snippet to inject
    modified_easymapping: list | None = None  # Modified easymapping structure
    metadata: dict[str, Any] = field(default_factory=dict)  # Plugin metadata for logging
    global_configs: list[str] = field(default_factory=list)  # HAProxy global-level configs
    defaults_configs: list[str] = field(default_factory=list)  # HAProxy defaults-level configs