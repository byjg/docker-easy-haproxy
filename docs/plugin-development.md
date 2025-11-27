---
sidebar_position: 17
---

# Plugin Developer Guide

This guide explains how to create custom plugins for EasyHAProxy. For information on using existing plugins, see [Using Plugins](plugins.md).

## Architecture Overview

### Plugin Lifecycle

```
1. Discovery Cycle Starts
   │
2. PluginManager loads plugins
   ├─ Load builtin plugins from src/plugins/builtin/
   └─ Load external plugins from /etc/haproxy/plugins/
   │
3. PluginManager configures plugins
   ├─ Read global config (YAML/env vars)
   └─ Call plugin.configure(config)
   │
4. Parse container metadata → easymapping
   │
5. Execute GLOBAL plugins (once)
   ├─ Create PluginContext (no domain info)
   ├─ Call plugin.process(context)
   └─ Collect PluginResult
   │
6. For each discovered domain:
   ├─ Extract plugin list from labels
   ├─ Extract plugin configs from labels
   ├─ Call plugin.configure(label_config)
   ├─ Execute DOMAIN plugins
   │   ├─ Create PluginContext (with domain info)
   │   ├─ Call plugin.process(context)
   │   └─ Collect PluginResult
   └─ Store plugin HAProxy configs
   │
7. Render Jinja2 template
   ├─ Inject global plugin configs
   └─ Inject domain plugin configs per backend
   │
8. Generate final HAProxy config
```

## Built-in Plugins Reference

EasyHAProxy includes four built-in plugins that serve as both functional tools and reference implementations for plugin development.

### CloudflarePlugin (DOMAIN)

**Purpose:** Restore original visitor IP addresses when using Cloudflare CDN

**Type:** DOMAIN - Executes once per domain

**Source:** `src/plugins/builtin/cloudflare.py`

**Configuration Options:**
- `enabled` (bool) - Enable/disable plugin (default: `true`)
- `ip_list_path` (str) - Path to Cloudflare IP list file (default: `/etc/haproxy/cloudflare_ips.lst`)

**What it does:**
- Reads Cloudflare IP ranges from a file
- Checks if request comes from Cloudflare IP
- Restores original visitor IP from `CF-Connecting-IP` header

**HAProxy config generated:**
```
# Cloudflare - Restore original visitor IP
acl from_cloudflare src -f /etc/haproxy/cloudflare_ips.lst
http-request set-header X-Forwarded-For %[req.hdr(CF-Connecting-IP)] if from_cloudflare
```

**Usage:** See [Cloudflare Plugin documentation](plugins.md#cloudflare-plugin-domain)

### CleanupPlugin (GLOBAL)

**Purpose:** Perform cleanup tasks during discovery cycle

**Type:** GLOBAL - Executes once per discovery cycle

**Source:** `src/plugins/builtin/cleanup.py`

**Configuration Options:**
- `enabled` (bool) - Enable/disable plugin (default: `true`)
- `max_idle_time` (int) - Max file age in seconds before deletion (default: `300`)
- `cleanup_temp_files` (bool) - Enable temp file cleanup (default: `true`)

**What it does:**
- Scans `/tmp` for files prefixed with `easyhaproxy_`
- Removes files older than `max_idle_time` seconds
- Logs cleanup actions to metadata

**HAProxy config generated:** None (performs cleanup only)

**Usage:** See [Cleanup Plugin documentation](plugins.md#cleanup-plugin-global)

### DenyPagesPlugin (DOMAIN)

**Purpose:** Block access to specific paths for a domain

**Type:** DOMAIN - Executes once per domain

**Source:** `src/plugins/builtin/deny_pages.py`

**Configuration Options:**
- `enabled` (bool) - Enable/disable plugin (default: `true`)
- `paths` (str) - Comma-separated list of paths to block (e.g., `/admin,/private`)
- `status_code` (int) - HTTP status code to return (default: `403`)

**What it does:**
- Parses comma-separated list of paths
- Creates HAProxy ACL matching those paths
- Returns specified HTTP status code for matching requests

**HAProxy config generated:**
```
# Deny Pages - Block specific paths
acl denied_path path_beg /admin /private
http-request deny deny_status 403 if denied_path
```

**Usage:** See [Deny Pages Plugin documentation](plugins.md#deny-pages-plugin-domain)

### IpWhitelistPlugin (DOMAIN)

**Purpose:** Restrict domain access to specific IP addresses or CIDR ranges

**Type:** DOMAIN - Executes once per domain

**Source:** `src/plugins/builtin/ip_whitelist.py`

**Configuration Options:**
- `enabled` (bool) - Enable/disable plugin (default: `true`)
- `allowed_ips` (str) - Comma-separated list of IPs/CIDR ranges to allow (e.g., `192.168.1.0/24,10.0.0.1`)
- `status_code` (int) - HTTP status code to return for blocked IPs (default: `403`)

**What it does:**
- Parses comma-separated list of IPs and CIDR ranges
- Creates HAProxy ACL matching whitelisted IPs
- Denies all requests NOT from whitelisted IPs

**HAProxy config generated:**
```
# IP Whitelist - Only allow specific IPs
acl whitelisted_ip src 192.168.1.0/24 10.0.0.5
http-request deny deny_status 403 if !whitelisted_ip
```

**Usage:** See [IP Whitelist Plugin documentation](plugins.md#ip-whitelist-plugin-domain)

### Summary Table

| Plugin         | Type   | Purpose                      | Config Generated |
|----------------|--------|------------------------------|------------------|
| `cloudflare`   | DOMAIN | Restore original visitor IPs | ✅ Yes            |
| `cleanup`      | GLOBAL | Clean up temp files          | ❌ No             |
| `deny_pages`   | DOMAIN | Block specific paths         | ✅ Yes            |
| `ip_whitelist` | DOMAIN | Restrict to specific IPs     | ✅ Yes            |

### Learning from Built-in Plugins

**Best practices demonstrated:**

1. **CloudflarePlugin** shows:
   - Reading external files (IP list)
   - Conditional HAProxy ACLs
   - Header manipulation

2. **CleanupPlugin** shows:
   - GLOBAL plugin pattern
   - File system operations
   - Metadata-only results (no HAProxy config)

3. **DenyPagesPlugin** shows:
   - Parsing comma-separated config values
   - Configurable status codes
   - Path-based ACLs

4. **IpWhitelistPlugin** shows:
   - IP-based access control
   - Negated ACLs (`if !whitelisted_ip`)
   - CIDR range support

**View the source code:**
- [cloudflare.py](https://github.com/byjg/docker-easy-haproxy/blob/master/src/plugins/builtin/cloudflare.py)
- [cleanup.py](https://github.com/byjg/docker-easy-haproxy/blob/master/src/plugins/builtin/cleanup.py)
- [deny_pages.py](https://github.com/byjg/docker-easy-haproxy/blob/master/src/plugins/builtin/deny_pages.py)
- [ip_whitelist.py](https://github.com/byjg/docker-easy-haproxy/blob/master/src/plugins/builtin/ip_whitelist.py)

## Plugin API Reference

### PluginInterface (Abstract Base Class)

All plugins must inherit from `PluginInterface` and implement these abstract methods:

```python
from plugins import PluginInterface, PluginType, PluginContext, PluginResult

class MyPlugin(PluginInterface):
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return unique plugin identifier.

        Used for:
        - Configuration lookups
        - Enable/disable via labels
        - Logging

        Must be:
        - Unique across all plugins
        - Lowercase with underscores
        - Match filename (e.g., my_plugin.py → "my_plugin")
        """
        pass

    @property
    @abstractmethod
    def plugin_type(self) -> PluginType:
        """
        Return plugin execution type.

        Returns:
            PluginType.GLOBAL - Execute once per discovery cycle
            PluginType.DOMAIN - Execute once per domain/host
        """
        pass

    @abstractmethod
    def configure(self, config: dict) -> None:
        """
        Configure plugin with settings from YAML/env/labels.

        Called:
        - Once at startup with global config
        - Before each execution with label-specific config (domain plugins)

        Args:
            config: Dictionary with plugin configuration
                   Keys are configuration option names
                   Values are strings from YAML/env/labels

        Common pattern:
            if "enabled" in config:
                self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]
            if "my_option" in config:
                self.my_option = config["my_option"]
        """
        pass

    @abstractmethod
    def process(self, context: PluginContext) -> PluginResult:
        """
        Execute plugin logic.

        Args:
            context: PluginContext with all execution data

        Returns:
            PluginResult with HAProxy config snippets and/or metadata

        Common pattern:
            if not self.enabled:
                return PluginResult()  # Empty result when disabled

            # Generate config
            haproxy_config = "..."

            return PluginResult(
                haproxy_config=haproxy_config,
                metadata={"info": "value"}
            )
        """
        pass
```

### PluginType (Enum)

Defines when plugins execute:

```python
class PluginType(Enum):
    GLOBAL = "global"  # Execute once per discovery cycle
    DOMAIN = "domain"  # Execute once per domain/host
```

**GLOBAL plugins:**
- Execute once regardless of how many domains exist
- Receive empty domain/port/host_config in context
- Use cases: cleanup, monitoring, DNS updates

**DOMAIN plugins:**
- Execute for each discovered domain
- Receive domain-specific data in context
- Use cases: per-domain config, headers, path blocking

### PluginContext (Data Class)

Contains all data available to plugins during execution:

```python
@dataclass
class PluginContext:
    parsed_object: dict              # Discovery data: {IP: labels}
    easymapping: list               # HAProxy mapping structure
    container_env: dict             # Global environment config
    domain: Optional[str] = None    # Domain name (DOMAIN plugins only)
    port: Optional[str] = None      # Port (DOMAIN plugins only)
    host_config: Optional[dict] = None  # Host config (DOMAIN plugins only)
```

**Fields explained:**

#### `parsed_object: dict`

Container discovery data mapping IP addresses to labels.

**Example:**
```python
{
    "192.168.1.10": {
        "easyhaproxy.http.host": "example.com",
        "easyhaproxy.http.port": "80",
        "easyhaproxy.http.localport": "8080",
        "easyhaproxy.http.plugins": "cloudflare,deny_pages",
        "easyhaproxy.http.plugin.deny_pages.paths": "/admin"
    },
    "192.168.1.20": {
        "easyhaproxy.http.host": "other.com",
        "easyhaproxy.http.port": "80"
    }
}
```

**Use cases:**
- Iterate over all discovered containers
- Access container labels directly
- Global plugins analyzing all containers

#### `easymapping: list`

Parsed HAProxy configuration structure before template rendering.

**Example:**
```python
[
    {
        "port": "80",
        "mode": "http",
        "ssl-check": "",
        "hosts": {
            "example.com": {
                "containers": ["192.168.1.10:8080"],
                "balance": "roundrobin",
                "certbot": False,
                "redirect_ssl": False,
                "plugin_configs": []
            }
        },
        "redirect": {}
    }
]
```

**Use cases:**
- Analyze discovered hosts
- Modify discovery structure (advanced)

#### `container_env: dict`

Global configuration from YAML and environment variables.

**Example:**
```python
{
    "customerrors": False,
    "ssl_mode": "default",
    "certbot": {
        "email": "admin@example.com"
    },
    "stats": {
        "port": 1936,
        "username": "admin"
    },
    "plugins": {
        "enabled": ["cleanup"],
        "abort_on_error": False,
        "config": {
            "cleanup": {
                "max_idle_time": "300"
            }
        }
    }
}
```

**Use cases:**
- Access global settings
- Check certbot configuration
- Read global plugin config

#### `domain: Optional[str]`

Domain name for DOMAIN plugins. `None` for GLOBAL plugins.

**Example:** `"example.com"`

#### `port: Optional[str]`

Port for DOMAIN plugins. `None` for GLOBAL plugins.

**Example:** `"80"`, `"443"`

#### `host_config: Optional[dict]`

Host-specific configuration for DOMAIN plugins. `None` for GLOBAL plugins.

**Example:**
```python
{
    "containers": ["192.168.1.10:8080"],
    "balance": "roundrobin",
    "certbot": False,
    "redirect_ssl": False,
    "plugin_configs": []
}
```

### PluginResult (Data Class)

```
Plugin.process(context) → PluginResult
                           ├─ haproxy_config (what to add to HAProxy config)
                           ├─ modified_easymapping (optional: modify discovery data)
                           └─ metadata (optional: debug/logging info)
```

**What is PluginResult?**

`PluginResult` is a container object that your plugin returns from its `process()` method. It holds everything the plugin produced during execution.

**Why does it exist?**

Plugins need to return multiple pieces of information:
- HAProxy configuration snippets to inject
- Optional modifications to the discovery data
- Metadata for logging and debugging

Instead of returning multiple values, plugins return one `PluginResult` object containing all this information.

**How do you use it?**

Every `process()` method must return a `PluginResult`:

```python
def process(self, context: PluginContext) -> PluginResult:
    # Plugin is disabled - return empty result
    if not self.enabled:
        return PluginResult()

    # Plugin is enabled - return config
    return PluginResult(
        haproxy_config="http-request set-header X-Custom-Header 'value'",
        metadata={"info": "some debug info"}
    )
```

**PluginResult structure:**

```python
@dataclass
class PluginResult:
    haproxy_config: str = ""                     # HAProxy config to inject
    modified_easymapping: Optional[list] = None  # Modified discovery data (advanced)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Debug/logging info
```

**Common usage patterns:**

```python
# Empty result (plugin disabled or nothing to do)
return PluginResult()

# Config only (most common)
return PluginResult(
    haproxy_config="# My config\n    directive value"
)

# Config + metadata (recommended)
return PluginResult(
    haproxy_config="# My config\n    directive value",
    metadata={"domain": context.domain, "option": self.my_option}
)

# All fields (advanced)
return PluginResult(
    haproxy_config="# My config\n    directive value",
    modified_easymapping=modified_data,
    metadata={"info": "value"}
)
```

**Fields explained:**

#### `haproxy_config: str`

HAProxy configuration snippet to inject into the generated config.

**For DOMAIN plugins:** Injected into the backend section for that domain.

**Example:**
```python
haproxy_config = """# Cloudflare IP Restoration
    acl from_cloudflare src -f /etc/haproxy/cloudflare_ips.lst
    http-request set-header X-Forwarded-For %[req.hdr(CF-Connecting-IP)] if from_cloudflare"""
```

**Important:**
- Include leading spaces/tabs for proper indentation
- Add comment describing what the config does
- Use HAProxy directives that make sense for backend context (domain plugins)
- Return empty string `""` when plugin is disabled or has nothing to add

#### `modified_easymapping: Optional[list]`

Modified easymapping structure. **Advanced feature, rarely used.**

**When to use:**
- Modify discovery data before template rendering
- Add/remove hosts dynamically
- Change port mappings

**Default:** `None` (don't modify easymapping)

**Example:**
```python
# Add a new host to port 80
modified = context.easymapping.copy()
modified[0]["hosts"]["new-host.com"] = {
    "containers": ["192.168.1.30:8080"],
    "balance": "roundrobin",
    "certbot": False,
    "redirect_ssl": False,
    "plugin_configs": []
}
return PluginResult(modified_easymapping=modified)
```

#### `metadata: Dict[str, Any]`

Metadata for logging and debugging. Not used in HAProxy config.

**Example:**
```python
metadata = {
    "domain": context.domain,
    "blocked_paths": ["/admin", "/private"],
    "status_code": 403,
    "files_cleaned": 5
}
```

**Use cases:**
- Debug information
- Statistics
- Audit trail

**Logged at DEBUG level:**
```
DEBUG: Plugin deny_pages metadata: {'domain': 'example.com', 'blocked_paths': ['/admin'], 'status_code': 403}
```

## Creating a Plugin: Step-by-Step

### Step 1: Create Plugin File

Create `/etc/haproxy/plugins/my_plugin.py`:

```python
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult
from functions import loggerEasyHaproxy  # Optional: for logging
```

### Step 2: Define Plugin Class

```python
class MyPlugin(PluginInterface):
    """
    Brief description of what your plugin does.

    Configuration:
        - enabled: Enable/disable plugin (default: true)
        - my_option: Description of option

    Example:
        easyhaproxy.http.plugins: my_plugin
        easyhaproxy.http.plugin.my_plugin.my_option: value
    """

    def __init__(self):
        """Initialize plugin with default values"""
        self.enabled = True
        self.my_option = "default_value"
```

### Step 3: Implement Required Methods

```python
    @property
    def name(self) -> str:
        return "my_plugin"  # Must match filename

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN  # or PluginType.GLOBAL

    def configure(self, config: dict) -> None:
        """Parse configuration from YAML/env/labels"""
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "my_option" in config:
            self.my_option = config["my_option"]

        loggerEasyHaproxy.debug(f"Configured {self.name}: enabled={self.enabled}, my_option={self.my_option}")

    def process(self, context: PluginContext) -> PluginResult:
        """Execute plugin logic"""
        # Return empty result if disabled
        if not self.enabled:
            return PluginResult()

        # Generate HAProxy config snippet
        haproxy_config = f"""# My Plugin - Description
    http-request set-header X-My-Header "{self.my_option}\""""

        # Return result
        return PluginResult(
            haproxy_config=haproxy_config,
            metadata={
                "domain": context.domain,
                "my_option": self.my_option
            }
        )
```

### Step 4: Test Your Plugin

Enable debug logging:
```bash
EASYHAPROXY_LOG_LEVEL=DEBUG
```

Enable plugin via label:
```yaml
services:
  test:
    labels:
      easyhaproxy.http.host: test.example.com
      easyhaproxy.http.plugins: my_plugin
      easyhaproxy.http.plugin.my_plugin.my_option: custom_value
```

Check logs for:
```
INFO: Loaded external plugin: my_plugin (domain)
DEBUG: Configured my_plugin: enabled=True, my_option=custom_value
DEBUG: Executing domain plugin: my_plugin for domain: test.example.com
DEBUG: Plugin my_plugin metadata: {'domain': 'test.example.com', 'my_option': 'custom_value'}
```

## Complete Examples

### Example 1: Custom Header Plugin (DOMAIN)

Add custom headers to specific domains:

```python
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult


class CustomHeaderPlugin(PluginInterface):
    """Add custom HTTP headers to requests"""

    def __init__(self):
        self.enabled = True
        self.headers = {}  # {header_name: header_value}

    @property
    def name(self) -> str:
        return "custom_header"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        # Parse headers from config
        # Format: header1:value1,header2:value2
        if "headers" in config:
            for header_pair in config["headers"].split(","):
                if ":" in header_pair:
                    name, value = header_pair.split(":", 1)
                    self.headers[name.strip()] = value.strip()

    def process(self, context: PluginContext) -> PluginResult:
        if not self.enabled or not self.headers:
            return PluginResult()

        # Generate HAProxy directives for each header
        lines = ["# Custom Headers"]
        for name, value in self.headers.items():
            lines.append(f'    http-request set-header {name} "{value}"')

        return PluginResult(
            haproxy_config="\n".join(lines),
            metadata={"domain": context.domain, "headers": self.headers}
        )
```

**Usage:**
```yaml
labels:
  easyhaproxy.http.plugins: custom_header
  easyhaproxy.http.plugin.custom_header.headers: X-App-Name:MyApp,X-Environment:Production
```

### Example 2: Rate Limiting Plugin (DOMAIN)

Add HAProxy rate limiting per domain:

```python
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult


class RateLimitPlugin(PluginInterface):
    """Rate limit requests per domain"""

    def __init__(self):
        self.enabled = True
        self.requests_per_second = 100
        self.burst = 200

    @property
    def name(self) -> str:
        return "rate_limit"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "requests_per_second" in config:
            try:
                self.requests_per_second = int(config["requests_per_second"])
            except ValueError:
                pass

        if "burst" in config:
            try:
                self.burst = int(config["burst"])
            except ValueError:
                pass

    def process(self, context: PluginContext) -> PluginResult:
        if not self.enabled:
            return PluginResult()

        # Use HAProxy stick tables for rate limiting
        domain_safe = context.domain.replace(".", "_")

        haproxy_config = f"""# Rate Limiting - {self.requests_per_second} req/s
    stick-table type ip size 100k expire 30s store http_req_rate({self.requests_per_second}s)
    http-request track-sc0 src
    http-request deny deny_status 429 if {{ sc_http_req_rate(0) gt {self.burst} }}"""

        return PluginResult(
            haproxy_config=haproxy_config,
            metadata={
                "domain": context.domain,
                "rate_limit": self.requests_per_second,
                "burst": self.burst
            }
        )
```

**Usage:**
```yaml
labels:
  easyhaproxy.http.plugins: rate_limit
  easyhaproxy.http.plugin.rate_limit.requests_per_second: 50
  easyhaproxy.http.plugin.rate_limit.burst: 100
```

### Example 3: Maintenance Mode Plugin (GLOBAL)

Put all sites in maintenance mode:

```python
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult


class MaintenanceModePlugin(PluginInterface):
    """Enable/disable maintenance mode globally"""

    def __init__(self):
        self.enabled = False  # Disabled by default
        self.message = "Site is under maintenance"

    @property
    def name(self) -> str:
        return "maintenance_mode"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.GLOBAL

    def configure(self, config: dict) -> None:
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "message" in config:
            self.message = config["message"]

    def process(self, context: PluginContext) -> PluginResult:
        if not self.enabled:
            return PluginResult()

        # When enabled, return maintenance page for all requests
        # This would need custom error pages configured in HAProxy
        return PluginResult(
            metadata={
                "maintenance_mode": True,
                "message": self.message
            }
        )
```

## Best Practices

### 1. Error Handling

Always handle errors gracefully:

```python
def process(self, context: PluginContext) -> PluginResult:
    try:
        # Your plugin logic
        result = do_something()
        return PluginResult(haproxy_config=result)
    except Exception as e:
        loggerEasyHaproxy.error(f"Plugin {self.name} failed: {e}")
        return PluginResult()  # Return empty result on error
```

### 2. Logging

Use structured logging:

```python
from functions import loggerEasyHaproxy

# Info level for important events
loggerEasyHaproxy.info(f"Plugin {self.name} executed successfully")

# Debug level for detailed info
loggerEasyHaproxy.debug(f"Plugin {self.name} config: {self.my_option}")

# Warning for non-critical issues
loggerEasyHaproxy.warning(f"Plugin {self.name}: config missing, using default")

# Error for failures
loggerEasyHaproxy.error(f"Plugin {self.name} failed: {error}")
```

### 3. Configuration Validation

Validate configuration values:

```python
def configure(self, config: dict) -> None:
    if "timeout" in config:
        try:
            timeout = int(config["timeout"])
            if timeout < 0:
                loggerEasyHaproxy.warning(f"{self.name}: timeout must be positive, using default")
                self.timeout = 30
            else:
                self.timeout = timeout
        except ValueError:
            loggerEasyHaproxy.warning(f"{self.name}: invalid timeout value, using default")
            self.timeout = 30
```

### 4. Documentation

Document your plugin thoroughly:

```python
class MyPlugin(PluginInterface):
    """
    One-line description.

    Detailed description of what the plugin does and why you'd use it.

    Configuration Options:
        enabled (bool): Enable/disable plugin (default: true)
        option1 (str): Description of option1 (default: "value")
        option2 (int): Description of option2 (default: 100)

    Example YAML:
        plugins:
          my_plugin:
            enabled: true
            option1: custom_value
            option2: 200

    Example Container Label:
        easyhaproxy.http.plugins: my_plugin
        easyhaproxy.http.plugin.my_plugin.option1: custom_value
        easyhaproxy.http.plugin.my_plugin.option2: 200

    HAProxy Config Generated:
        # My Plugin - Description
        directive1 value
        directive2 value
    """
```

### 5. Testing

Test your plugin with various configurations:

```python
# Test 1: Plugin disabled
config = {"enabled": "false"}
plugin.configure(config)
result = plugin.process(context)
assert result.haproxy_config == ""

# Test 2: Plugin with default config
plugin = MyPlugin()
result = plugin.process(context)
assert "expected output" in result.haproxy_config

# Test 3: Plugin with custom config
config = {"my_option": "custom"}
plugin.configure(config)
result = plugin.process(context)
assert "custom" in result.haproxy_config
```

### 6. Performance

Keep plugins lightweight:

```python
# DON'T: Make external API calls in domain plugins
def process(self, context: PluginContext) -> PluginResult:
    # This runs for EVERY domain!
    data = requests.get("https://api.example.com/data")  # BAD

# DO: Cache data or use global plugins for external calls
def process(self, context: PluginContext) -> PluginResult:
    # Use cached data
    data = self.cached_data
```

## Testing Plugins

### Unit Testing

Create tests in `src/tests/test_my_plugin.py`:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginContext
from plugins.my_plugin import MyPlugin


def test_plugin_initialization():
    plugin = MyPlugin()
    assert plugin.name == "my_plugin"
    assert plugin.enabled is True


def test_plugin_configuration():
    plugin = MyPlugin()
    plugin.configure({"enabled": "false", "my_option": "custom"})
    assert plugin.enabled is False
    assert plugin.my_option == "custom"


def test_plugin_generates_config():
    plugin = MyPlugin()
    context = PluginContext(
        parsed_object={},
        easymapping=[],
        container_env={},
        domain="example.com",
        port="80",
        host_config={}
    )

    result = plugin.process(context)
    assert "X-My-Header" in result.haproxy_config
    assert result.metadata["domain"] == "example.com"


def test_plugin_disabled():
    plugin = MyPlugin()
    plugin.configure({"enabled": "false"})

    context = PluginContext(
        parsed_object={},
        easymapping=[],
        container_env={},
        domain="example.com"
    )

    result = plugin.process(context)
    assert result.haproxy_config == ""
```

Run tests:
```bash
pytest src/tests/test_my_plugin.py -v
```

## Troubleshooting

### Plugin Not Loading

**Check logs:**
```
ERROR: Failed to load plugin from /etc/haproxy/plugins/my_plugin.py: <error>
```

**Common causes:**
- Syntax errors in Python code
- Missing imports
- Class doesn't inherit from `PluginInterface`
- `__init__.py` in plugins directory (remove it)

### Plugin Not Executing

**Check logs:**
```
DEBUG: Executing domain plugin: my_plugin for domain: example.com
```

**If missing:**
- Plugin not enabled in labels/YAML/env
- Plugin name mismatch
- Plugin returned by `name` property doesn't match

### Configuration Not Working

**Enable debug logging:**
```bash
EASYHAPROXY_LOG_LEVEL=DEBUG
```

**Check:**
```
DEBUG: Configured my_plugin: enabled=True, option=value
```

**Verify precedence:**
1. Container labels (highest)
2. YAML config
3. Environment variables (lowest)

## Further Reading

- [Using Plugins](plugins.md) - How to use existing plugins
- [Built-in Plugin Source Code](https://github.com/byjg/docker-easy-haproxy/tree/master/src/plugins/builtin) - Examples to learn from
- [HAProxy Configuration Manual](http://docs.haproxy.org/2.8/configuration.html) - HAProxy directive reference

## Support

For issues or questions:
- GitHub Issues: https://github.com/byjg/docker-easy-haproxy/issues
- Documentation: https://byjg.github.io/docker-easy-haproxy
