---
sidebar_position: 17
---

# EasyHAProxy Plugin System - Developer Guide

## Overview

The EasyHAProxy plugin system allows you to extend HAProxy configuration generation with custom functionality. Plugins are invoked during the discovery cycle and can inject HAProxy configuration snippets or modify the discovery data.

## Plugin Types

### GLOBAL Plugins
- **Execution**: Once per discovery cycle
- **Use Cases**: Cleanup tasks, global configuration, monitoring, DNS updates
- **Example**: `CleanupPlugin`

### DOMAIN Plugins
- **Execution**: Once for each discovered domain/host
- **Use Cases**: Domain-specific configuration, IP restoration, path blocking, custom headers
- **Example**: `CloudflarePlugin`, `DenyPagesPlugin`

## Creating a Custom Plugin

### 1. Plugin Structure

Create a Python file in `/etc/haproxy/plugins/` or `/scripts/plugins/builtin/`:

```python
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult


class MyCustomPlugin(PluginInterface):
    """Your plugin description"""

    def __init__(self):
        # Initialize plugin state
        self.enabled = True
        self.my_config_value = "default"

    @property
    def name(self) -> str:
        """Return unique plugin name"""
        return "my_custom_plugin"

    @property
    def plugin_type(self) -> PluginType:
        """Return GLOBAL or DOMAIN"""
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        """
        Configure plugin from YAML/env/labels

        Args:
            config: Configuration dictionary
        """
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "my_config_value" in config:
            self.my_config_value = config["my_config_value"]

    def process(self, context: PluginContext) -> PluginResult:
        """
        Process plugin logic

        Args:
            context: PluginContext with execution data

        Returns:
            PluginResult with HAProxy config and/or metadata
        """
        if not self.enabled:
            return PluginResult()

        # Generate HAProxy configuration snippet
        haproxy_config = """# My Custom Plugin
    # Add your HAProxy directives here
    http-request set-header X-Custom-Header "value"
    """

        return PluginResult(
            haproxy_config=haproxy_config,
            modified_easymapping=None,  # Optional: modify discovery data
            metadata={"info": "my metadata"}  # Optional: logging info
        )
```

### 2. Plugin Context Data

The `PluginContext` object provides:

```python
@dataclass
class PluginContext:
    parsed_object: dict        # {IP: labels} from container discovery
    easymapping: list         # Current HAProxy mapping structure
    container_env: dict       # Environment configuration
    domain: Optional[str]     # Domain name (DOMAIN plugins only)
    port: Optional[str]       # Port (DOMAIN plugins only)
    host_config: Optional[dict]  # Domain config (DOMAIN plugins only)
```

**Example parsed_object:**
```python
{
    "192.168.1.10": {
        "easyhaproxy.http.host": "example.com",
        "easyhaproxy.http.port": "80",
        "easyhaproxy.http.localport": "8080"
    }
}
```

**Example easymapping:**
```python
[
    {
        "port": "80",
        "mode": "http",
        "hosts": {
            "example.com": {
                "containers": ["192.168.1.10:8080"],
                "certbot": False,
                "balance": "roundrobin"
            }
        }
    }
]
```

### 3. Plugin Configuration

Plugins can be configured via:

#### YAML (`/etc/haproxy/static/config.yaml`):
```yaml
plugins:
  my_custom_plugin:
    enabled: true
    my_config_value: "custom"
```

#### Environment Variables:
```bash
EASYHAPROXY_PLUGINS_ENABLED=my_custom_plugin
EASYHAPROXY_PLUGIN_MY_CUSTOM_PLUGIN_MY_CONFIG_VALUE=custom
```

#### Container Labels:
```yaml
labels:
  easyhaproxy.http.plugins: "my_custom_plugin"
  easyhaproxy.http.plugin.my_custom_plugin.my_config_value: "custom"
```

## Built-in Plugins

### CloudflarePlugin (DOMAIN)
- **Purpose**: Restore original visitor IP from Cloudflare headers
- **Config**: `ip_list_path` - Path to Cloudflare IP list
- **Location**: `/scripts/plugins/builtin/cloudflare.py`

### CleanupPlugin (GLOBAL)
- **Purpose**: Cleanup temporary files during discovery
- **Config**: `max_idle_time`, `cleanup_temp_files`
- **Location**: `/scripts/plugins/builtin/cleanup.py`

### DenyPagesPlugin (DOMAIN)
- **Purpose**: Block access to specific paths
- **Config**: `paths`, `status_code`
- **Location**: `/scripts/plugins/builtin/deny_pages.py`

## Plugin Lifecycle

```
Discovery Cycle
  ├─ Container/Service Discovery
  ├─ Parse Metadata → easymapping
  ├─ Execute GLOBAL plugins (once)
  ├─ For each domain:
  │   ├─ Execute DOMAIN plugins
  │   └─ Store plugin configs
  ├─ Render Jinja2 template with plugin snippets
  └─ Generate final HAProxy config
```

## Error Handling

### Default Behavior (Log and Continue)
```yaml
plugins:
  abort_on_error: false  # Default
```
- Plugin errors are logged as warnings
- Discovery cycle continues
- HAProxy config generation proceeds

### Abort on Error
```yaml
plugins:
  abort_on_error: true
```
- Plugin errors stop the discovery cycle
- Previous HAProxy config remains active
- Useful for critical plugins

## Best Practices

1. **Keep It Simple**: Plugins should do one thing well
2. **Error Handling**: Use try/except and return empty PluginResult on errors
3. **Logging**: Use `from functions import loggerEasyHaproxy` for logging
4. **Configuration**: Provide sensible defaults
5. **Documentation**: Add docstrings explaining configuration options
6. **Testing**: Test your plugin with various configurations

## Debugging

Enable debug logging:
```bash
EASYHAPROXY_LOG_LEVEL=DEBUG
```

Check plugin loading:
```
# Look for log messages:
Loaded builtin plugin: cloudflare (domain)
Loaded external plugin: my_plugin (global)
```

## Examples

### Example 1: Add Custom Header (DOMAIN)

```python
class CustomHeaderPlugin(PluginInterface):
    def __init__(self):
        self.header_name = "X-Custom"
        self.header_value = "value"

    @property
    def name(self) -> str:
        return "custom_header"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        self.header_name = config.get("header_name", self.header_name)
        self.header_value = config.get("header_value", self.header_value)

    def process(self, context: PluginContext) -> PluginResult:
        return PluginResult(
            haproxy_config=f'http-request set-header {self.header_name} "{self.header_value}"'
        )
```

### Example 2: DNS Update (GLOBAL)

```python
class DNSUpdatePlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "dns_update"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.GLOBAL

    def configure(self, config: dict) -> None:
        self.dns_server = config.get("dns_server", "8.8.8.8")

    def process(self, context: PluginContext) -> PluginResult:
        # Update DNS records based on discovered hosts
        for ip, labels in context.parsed_object.items():
            # Your DNS update logic here
            pass

        return PluginResult(metadata={"dns_updates": "completed"})
```

## Support

For issues or questions:
- GitHub: https://github.com/byjg/docker-easy-haproxy
- Documentation: https://byjg.github.io/docker-easy-haproxy
