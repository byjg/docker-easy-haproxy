---
sidebar_position: 4
sidebar_label: "Plugin Development"
---

# Plugin Development Guide

This comprehensive guide covers everything you need to know about developing plugins for EasyHAProxy. Plugins extend HAProxy configuration with custom functionality and can be integrated seamlessly with Docker, Kubernetes, and Swarm environments.

## Table of Contents

1. [Overview](#overview)
2. [Plugin Architecture](#plugin-architecture)
3. [Quick Start Guide](#quick-start-guide)
4. [API Reference](#api-reference)
5. [Advanced Examples](#advanced-examples)
6. [Best Practices](#best-practices)
7. [Testing Guidelines](#testing-guidelines)
8. [Troubleshooting](#troubleshooting)
9. [Distribution](#distribution)

---

## Overview

### What is a Plugin?

A plugin is a Python class that implements the `PluginInterface` and extends HAProxy's configuration during the discovery cycle. Plugins can:

- **Inject HAProxy configuration** - Add custom HAProxy directives (ACLs, http-request rules, etc.)
- **Modify discovery data** - Transform the easymapping structure before HAProxy config generation
- **Perform maintenance tasks** - Execute cleanup, monitoring, or integration tasks
- **Integrate with external services** - Connect to APIs, databases, or third-party systems

### Why Build a Plugin?

Build a plugin when you need to:

- Add domain-specific HAProxy configuration based on labels/annotations
- Integrate with CDNs, load balancers, or security services
- Implement custom authentication or authorization logic
- Perform scheduled maintenance or monitoring tasks
- Extend EasyHAProxy without modifying core code

### Plugin System Benefits

- **Zero code changes** - Plugins don't modify EasyHAProxy core
- **Hot reload support** - Plugins reload on each discovery cycle
- **Configuration flexibility** - Configure via YAML, environment variables, or container labels
- **Error isolation** - Plugin errors don't crash the main application (configurable)
- **Easy distribution** - Share plugins as single Python files

---

## Plugin Architecture

### Plugin Types

EasyHAProxy supports two plugin execution models:

#### 1. GLOBAL Plugins

Execute **once per discovery cycle**, regardless of discovered domains.

**Execution timing:** After discovery, before domain processing

**Use cases:**
- Cleanup tasks (removing old temp files)
- Global monitoring (health checks, metrics)
- DNS updates (updating external DNS records)
- Log rotation or archiving
- Integration with global services

**Example:** CleanupPlugin - removes old temporary files once per cycle

#### 2. DOMAIN Plugins

Execute **once per discovered domain/host**.

**Execution timing:** During domain processing, before backend config generation

**Use cases:**
- Domain-specific HAProxy rules (IP whitelisting, rate limiting)
- CDN integration (Cloudflare IP restoration)
- Path-based controls (blocking specific URLs)
- Custom headers or redirects per domain
- JWT validation or authentication

**Example:** CloudflarePlugin - restores visitor IP for each Cloudflare-enabled domain

### Plugin Lifecycle

```
1. LOAD PHASE
   ├─ PluginManager scans plugins directory
   ├─ Imports plugin modules
   ├─ Instantiates plugin classes
   └─ Categorizes by type (GLOBAL/DOMAIN)

2. CONFIGURE PHASE
   ├─ Loads configuration from YAML/env
   ├─ Calls plugin.configure(config) for each plugin
   └─ Validates configuration (plugin responsibility)

3. INITIALIZE PHASE
   ├─ Calls plugin.initialize() for each plugin
   ├─ Plugins request file system resources (directories, files)
   ├─ PluginManager processes resource requests
   └─ Creates directories and files as needed

4. EXECUTION PHASE (per discovery cycle)
   ├─ GLOBAL PLUGINS
   │  └─ Executes all global plugins once
   │
   └─ DOMAIN PLUGINS
      └─ For each discovered domain:
         └─ Executes all domain plugins

5. RESULT PROCESSING
   ├─ Collects PluginResult from each plugin
   ├─ Injects haproxy_config into backend sections
   ├─ Injects global_configs into global section
   ├─ Injects defaults_configs into defaults section
   ├─ Applies modified_easymapping if provided
   └─ Logs metadata for debugging
```

### Plugin Loading Order

1. **Builtin plugins** - Loaded from `/src/plugins/builtin/`
2. **External plugins** - Loaded from `/etc/easyhaproxy/plugins/`

Plugins are discovered automatically by filename (`*.py` excluding `__*.py`).

### Data Flow

```
Container Labels/Annotations
         ↓
Discovery (Docker/K8s/Swarm)
         ↓
parsed_object: {IP: labels}
         ↓
[GLOBAL PLUGINS] ← PluginContext (parsed_object, easymapping, env)
         ↓
easymapping: [list of domain configs]
         ↓
For each domain:
    [DOMAIN PLUGINS] ← PluginContext (domain, port, host_config, ...)
         ↓
    PluginResult → haproxy_config snippets
         ↓
HAProxy Configuration File
         ↓
HAProxy Reload
```

---

## Quick Start Guide

### Step 1: Create Plugin File

Create a new Python file in `/etc/easyhaproxy/plugins/` (or builtin location for core plugins):

```python
# /etc/easyhaproxy/plugins/my_plugin.py

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult
from functions import logger_easyhaproxy


class MyPlugin(PluginInterface):
    """My custom plugin description"""

    def __init__(self):
        # Initialize default configuration
        self.enabled = True
        self.my_setting = "default_value"

    @property
    def name(self) -> str:
        """Return unique plugin name"""
        return "my_plugin"

    @property
    def plugin_type(self) -> PluginType:
        """Return plugin type (GLOBAL or DOMAIN)"""
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        """
        Configure plugin from YAML/env/labels

        Args:
            config: Dictionary with plugin configuration
        """
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "my_setting" in config:
            self.my_setting = config["my_setting"]

    def process(self, context: PluginContext) -> PluginResult:
        """
        Process plugin logic and return result

        Args:
            context: PluginContext with execution data

        Returns:
            PluginResult with HAProxy config and metadata
        """
        if not self.enabled:
            return PluginResult()

        # Generate HAProxy configuration
        haproxy_config = f"""# My Plugin - Custom functionality
http-request set-header X-My-Header {self.my_setting}"""

        return PluginResult(
            haproxy_config=haproxy_config,
            metadata={
                "domain": context.domain,
                "setting_value": self.my_setting
            }
        )
```

### Step 2: Enable Plugin

**Via container label (Docker):**

```yaml
services:
  myapp:
    labels:
      easyhaproxy.http.host: example.com
      easyhaproxy.http.plugins: my_plugin
      easyhaproxy.http.plugin.my_plugin.my_setting: custom_value
```

**Via YAML configuration:**

```yaml
# /etc/easyhaproxy/static/config.yaml
plugins:
  enabled: [my_plugin]
  config:
    my_plugin:
      enabled: true
      my_setting: custom_value
```

**Via environment variable:**

```bash
EASYHAPROXY_PLUGINS_ENABLED=my_plugin
EASYHAPROXY_PLUGIN_MY_PLUGIN_MY_SETTING=custom_value
```

### Step 3: Test Plugin

Restart EasyHAProxy and check logs:

```bash
docker-compose restart haproxy
docker-compose logs -f haproxy | grep my_plugin
```

Expected output:
```
[INFO] Loaded external plugin: my_plugin (domain)
[DEBUG] Configured plugin: my_plugin with config: {'my_setting': 'custom_value'}
[DEBUG] Executing domain plugin: my_plugin for domain: example.com
```

---

## API Reference

### PluginInterface

Base class all plugins must inherit from.

```python
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

    def initialize(self) -> InitializationResult:
        """
        Initialize plugin resources (new in v2.0)

        Optional method to request file system resources.
        Default implementation returns empty result (no-op).

        Returns:
            InitializationResult with resource requests
        """
        return InitializationResult()

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
```

**Properties:**

- `name` - Unique identifier (used in configuration and logs)
- `plugin_type` - Execution model (`PluginType.GLOBAL` or `PluginType.DOMAIN`)

**Methods:**

- `configure(config)` - Receives plugin configuration during initialization
- `initialize()` - **[New in v2.0]** Request file system resources (optional)
- `process(context)` - Main execution logic, returns `PluginResult`

### PluginType

Enum defining plugin execution types.

```python
class PluginType(Enum):
    """Plugin execution types"""
    GLOBAL = "global"    # Execute once per discovery cycle
    DOMAIN = "domain"    # Execute per domain/host
```

### PluginContext

Container for all plugin execution data.

```python
@dataclass
class PluginContext:
    """Container for all plugin execution data"""
    parsed_object: dict              # {IP: labels} from discovery
    easymapping: list               # Current HAProxy mapping structure
    container_env: dict             # Environment configuration
    domain: Optional[str] = None    # Domain name (for DOMAIN plugins)
    port: Optional[str] = None      # Port (for DOMAIN plugins)
    host_config: Optional[dict] = None  # Domain-specific config
```

### PluginResult

Plugin execution result containing configuration and metadata.

```python
@dataclass
class PluginResult:
    """Plugin execution result"""
    haproxy_config: str = ""                     # HAProxy config snippet to inject
    modified_easymapping: Optional[list] = None  # Modified easymapping structure
    metadata: Dict[str, Any] = field(default_factory=dict)  # Plugin metadata for logging
    global_configs: list[str] = field(default_factory=list)  # [New] Global-level configs
    defaults_configs: list[str] = field(default_factory=list)  # [New] Defaults-level configs
```

**Fields:**

- `haproxy_config` - HAProxy configuration snippet (injected into backend/frontend)
- `modified_easymapping` - Modified easymapping structure (optional, advanced use)
- `metadata` - Dictionary with debugging/logging information
- `global_configs` - **[New in v2.0]** List of global-level HAProxy configs (e.g., fcgi-app definitions)
- `defaults_configs` - **[New in v2.0]** List of defaults-level HAProxy configs (e.g., log-format)

### ResourceRequest

**[New in v2.0]** Request for file system resources during plugin initialization.

```python
@dataclass
class ResourceRequest:
    """Request for file system resources"""
    resource_type: str  # "directory" or "file"
    path: str
    content: str | None = None
    overwrite: bool = False
```

### InitializationResult

**[New in v2.0]** Plugin initialization result with resource requests.

```python
@dataclass
class InitializationResult:
    """Plugin initialization result with resource requests"""
    resources: list[ResourceRequest] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## Advanced Examples

### Example 1: IP Whitelist Plugin (DOMAIN)

Restrict access to specific IP addresses per domain.

```python
import os
import sys

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
        if not self.enabled or not self.allowed_ips:
            return PluginResult()

        ips_str = " ".join(self.allowed_ips)

        haproxy_config = f"""# IP Whitelist - Only allow specific IPs
acl whitelisted_ip src {ips_str}
http-request deny deny_status {self.status_code} if !whitelisted_ip"""

        return PluginResult(
            haproxy_config=haproxy_config,
            metadata={
                "domain": context.domain,
                "allowed_ips": self.allowed_ips,
                "status_code": self.status_code
            }
        )
```

### Example 2: Cleanup Plugin (GLOBAL)

Perform cleanup tasks during each discovery cycle.

```python
import os
import sys
import glob
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult
from functions import logger_easyhaproxy


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
        if not self.enabled:
            return PluginResult()

        cleanup_actions = []

        if self.cleanup_temp_files:
            temp_dirs = ["/tmp", "/var/tmp"]
            current_time = time.time()

            for temp_dir in temp_dirs:
                if not os.path.exists(temp_dir):
                    continue
                try:
                    pattern = os.path.join(temp_dir, "easyhaproxy_*")
                    for filepath in glob.glob(pattern):
                        try:
                            file_age = current_time - os.path.getmtime(filepath)
                            if file_age > self.max_idle_time:
                                os.remove(filepath)
                                cleanup_actions.append(f"Removed old temp file: {filepath}")
                        except Exception as e:
                            logger_easyhaproxy.warning(f"Failed to remove temp file {filepath}: {e}")
                except Exception as e:
                    logger_easyhaproxy.warning(f"Failed to cleanup {temp_dir}: {e}")

        return PluginResult(
            haproxy_config="",
            metadata={
                "actions_performed": len(cleanup_actions),
                "actions": cleanup_actions
            }
        )
```

---

## Best Practices

1. **Use `initialize()` for resource setup** - Request directories/files during init, not in `process()`
2. **Use typed result fields** - Use `global_configs` and `defaults_configs` instead of metadata for config injection
3. **Handle errors gracefully** - Use try/except and return `PluginResult()` on error
4. **Validate in `configure()`** - Don't validate at `process()` time
5. **Use metadata for debugging** - Include useful info in `metadata` dict
6. **Support multiple boolean formats** - `str(config["enabled"]).lower() in ["true", "1", "yes"]`
7. **Support list and string formats** - Handle both YAML lists and comma-separated strings
8. **Use descriptive names** - Clear plugin name, ACL names, and config keys
9. **Document your plugin** - Include docstring with YAML and label examples
10. **Return empty result when disabled** - Check `self.enabled` first

---

## Testing Guidelines

### Unit Testing

```python
from plugins import PluginContext
from plugins.builtin.my_plugin import MyPlugin


class TestMyPlugin:
    def test_plugin_initialization(self):
        plugin = MyPlugin()
        assert plugin.name == "my_plugin"
        assert plugin.enabled is True

    def test_plugin_generates_config(self):
        plugin = MyPlugin()
        plugin.configure({"my_setting": "test_value"})

        context = PluginContext(
            parsed_object={},
            easymapping=[],
            container_env={},
            domain="example.com",
            port="80",
            host_config={}
        )

        result = plugin.process(context)
        assert result.haproxy_config is not None
        assert "X-My-Header test_value" in result.haproxy_config

    def test_plugin_disabled(self):
        plugin = MyPlugin()
        plugin.configure({"enabled": "false"})

        context = PluginContext(
            parsed_object={}, easymapping=[], container_env={}, domain="example.com"
        )

        result = plugin.process(context)
        assert result.haproxy_config == ""
```

---

## Troubleshooting

### Plugin Not Loading

1. File not in plugins directory: `ls -la /etc/easyhaproxy/plugins/`
2. Invalid Python syntax: `python3 -m py_compile /etc/easyhaproxy/plugins/my_plugin.py`
3. Class doesn't inherit `PluginInterface`
4. Missing required imports

### Plugin Not Executing

1. Plugin not enabled in configuration
2. Wrong plugin type for use case
3. Plugin disabled via configuration

### HAProxy Configuration Invalid

```bash
# Test configuration manually:
haproxy -c -f /etc/easyhaproxy/haproxy/haproxy.cfg
```

---

## Distribution

### Option 1: Single File

```bash
cp my_plugin.py /etc/easyhaproxy/plugins/
```

### Option 2: Docker Image with Plugin

```dockerfile
FROM byjg/easy-haproxy:latest
COPY my_plugin.py /app/src/plugins/builtin/
```

### Contributing to EasyHAProxy

1. Fork the repository
2. Add your plugin to `src/plugins/builtin/`
3. Add tests in `src/tests/test_plugins.py`
4. Add documentation in `docs/reference/plugins/`
5. Create a pull request

---

For more examples, see the builtin plugins in `/src/plugins/builtin/`:
- `cloudflare.py` - Simple DOMAIN plugin
- `fastcgi.py` - Advanced DOMAIN plugin with complex config
- `jwt_validator.py` - Security plugin with path-based logic
- `ip_whitelist.py` - Access control plugin
- `cleanup.py` - GLOBAL plugin example
