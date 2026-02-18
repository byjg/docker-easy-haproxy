---
sidebar_position: 16
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

**Fields:**

- `parsed_object` - Raw discovery data: `{IP: {label: value, ...}, ...}`
- `easymapping` - Current mapping structure (list of domain configurations)
- `container_env` - Environment variables and global configuration
- `domain` - Domain name (only for DOMAIN plugins)
- `port` - Port number (only for DOMAIN plugins)
- `host_config` - Domain-specific labels/annotations (only for DOMAIN plugins)

**Usage in GLOBAL plugins:**

```python
def process(self, context: PluginContext) -> PluginResult:
    # Access all discovered services
    for ip, labels in context.parsed_object.items():
        print(f"Found service at {ip}: {labels}")

    # Access global environment
    debug_mode = context.container_env.get("DEBUG", "false")
```

**Usage in DOMAIN plugins:**

```python
def process(self, context: PluginContext) -> PluginResult:
    # Access domain-specific data
    domain = context.domain  # e.g., "example.com"
    port = context.port      # e.g., "80"

    # Check domain-specific labels
    custom_label = context.host_config.get("custom_label", "default")
```

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

**Fields:**

- `resource_type` - Type of resource: `"directory"` or `"file"`
- `path` - Absolute path to create
- `content` - File content (only for `resource_type="file"`)
- `overwrite` - Whether to overwrite existing files (default: False)

**Example:**

```python
ResourceRequest(
    resource_type="directory",
    path="/etc/easyhaproxy/plugin_data"
)

ResourceRequest(
    resource_type="file",
    path="/etc/easyhaproxy/plugin_config.txt",
    content="config data",
    overwrite=True
)
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

**Fields:**

- `resources` - List of ResourceRequest objects
- `metadata` - Optional metadata about initialization

**Example:**

```python
def initialize(self) -> InitializationResult:
    return InitializationResult(
        resources=[
            ResourceRequest(resource_type="directory", path="/etc/easyhaproxy/jwt_keys")
        ]
    )
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

**Examples:**

```python
# Simple config injection (backend-level)
return PluginResult(
    haproxy_config="http-request deny deny_status 403"
)

# With metadata
return PluginResult(
    haproxy_config="acl whitelisted src 10.0.0.0/8",
    metadata={
        "domain": context.domain,
        "allowed_networks": ["10.0.0.0/8"],
        "rules_added": 1
    }
)

# With global-level config (new in v2.0)
return PluginResult(
    haproxy_config="use-fcgi-app fcgi_example_com",
    global_configs=[
        "fcgi-app fcgi_example_com\n    docroot /etc/easyhaproxy/www"
    ]
)

# With defaults-level config (new in v2.0)
return PluginResult(
    haproxy_config="acl from_cloudflare src -f /etc/easyhaproxy/cloudflare_ips.lst",
    defaults_configs=[
        'log-format "%{+Q}[var(txn.real_ip)]:-/%ci:%cp [%tr] %ft %b/%s"'
    ]
)

# No operation (plugin disabled or no action needed)
return PluginResult()
```

### PluginManager

Manages plugin loading, configuration, and execution.

```python
class PluginManager:
    """Manages plugin loading, configuration, and execution"""

    def __init__(self, plugins_dir: str | None = None, abort_on_error: bool = False):
        """
        Initialize the plugin manager

        Args:
            plugins_dir: Directory containing plugin files (defaults to
                        EASYHAPROXY_PLUGINS_DIR env var or /etc/easyhaproxy/plugins)
            abort_on_error: If True, abort on plugin errors; if False, log and continue
        """

    def load_plugins(self) -> None:
        """Discover and load plugins from the plugins directory"""

    def configure_plugins(self, plugins_config: dict) -> None:
        """Configure all loaded plugins with their settings"""

    def initialize_plugins(self) -> None:
        """[New in v2.0] Initialize all plugins and process resource requests"""

    def execute_global_plugins(self, context: PluginContext, enabled_list: Optional[List[str]] = None) -> List[PluginResult]:
        """Execute all global plugins"""

    def execute_domain_plugins(self, context: PluginContext, enabled_list: Optional[List[str]] = None) -> List[PluginResult]:
        """Execute all domain plugins for a specific domain"""
```

**Environment Variables:**

- `EASYHAPROXY_PLUGINS_DIR` - Override plugin directory (default: `/etc/easyhaproxy/plugins`)

**Note:** You typically don't interact with PluginManager directly when writing plugins. It's used by EasyHAProxy core.

---

## Advanced Examples

### Example 1: IP Whitelist Plugin (DOMAIN)

Restrict access to specific IP addresses per domain.

```python
"""
IP Whitelist Plugin for EasyHAProxy

This plugin restricts access to a domain to only specific IP addresses or CIDR ranges.
It runs as a DOMAIN plugin (once per domain).

Configuration:
    - enabled: Enable/disable the plugin (default: true)
    - allowed_ips: Comma-separated list of IPs/CIDR ranges to allow
    - status_code: HTTP status code to return for blocked IPs (default: 403)

Example YAML config:
    plugins:
      ip_whitelist:
        enabled: true
        allowed_ips: "192.168.1.0/24,10.0.0.1,172.16.0.0/16"
        status_code: 403

Example Container Label:
    easyhaproxy.http.plugins: "ip_whitelist"
    easyhaproxy.http.plugin.ip_whitelist.allowed_ips: "192.168.1.0/24,10.0.0.1"
    easyhaproxy.http.plugin.ip_whitelist.status_code: 403

HAProxy Config Generated:
    # IP Whitelist - Only allow specific IPs
    acl whitelisted_ip src 192.168.1.0/24 10.0.0.1
    http-request deny deny_status 403 if !whitelisted_ip
"""

import os
import sys

# Add parent directory to path for imports
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
        """
        Configure the plugin

        Args:
            config: Dictionary with configuration options
                - enabled: Whether plugin is enabled
                - allowed_ips: Comma-separated list of IPs/CIDR ranges
                - status_code: HTTP status code to return for denied requests
        """
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
        """
        Generate HAProxy config to whitelist specific IPs

        Args:
            context: Plugin execution context with domain information

        Returns:
            PluginResult with HAProxy configuration snippet
        """
        if not self.enabled or not self.allowed_ips:
            return PluginResult()

        # Create space-separated list of IPs for ACL
        ips_str = " ".join(self.allowed_ips)

        # Generate HAProxy config snippet
        haproxy_config = f"""# IP Whitelist - Only allow specific IPs
acl whitelisted_ip src {ips_str}
http-request deny deny_status {self.status_code} if !whitelisted_ip"""

        return PluginResult(
            haproxy_config=haproxy_config,
            modified_easymapping=None,
            metadata={
                "domain": context.domain,
                "allowed_ips": self.allowed_ips,
                "status_code": self.status_code
            }
        )
```

### Example 2: FastCGI Plugin (DOMAIN)

Configure FastCGI parameters for PHP-FPM and other FastCGI applications.

```python
"""
FastCGI Plugin for EasyHAProxy

This plugin generates HAProxy fcgi-app configuration for PHP-FPM and other FastCGI applications.
It runs as a DOMAIN plugin (once per domain).

The plugin creates:
    1. A top-level fcgi-app section with CGI parameter definitions
    2. A use-fcgi-app directive in the backend

Configuration:
    - enabled: Enable/disable the plugin (default: true)
    - document_root: Document root path (default: /etc/easyhaproxy/www)
    - script_filename: Pattern for SCRIPT_FILENAME (default: %[path])
    - index_file: Default index file (default: index.php)
    - path_info: Enable PATH_INFO support (default: true)
    - custom_params: Dictionary of custom FastCGI parameters (optional)

Example YAML config:
    plugins:
      fastcgi:
        enabled: true
        document_root: /etc/easyhaproxy/www
        index_file: index.php
        path_info: true

Example Container Label:
    easyhaproxy.http.plugins: "fastcgi"
    easyhaproxy.http.plugin.fastcgi.document_root: /var/www/myapp
    easyhaproxy.http.plugin.fastcgi.index_file: index.php
    easyhaproxy.http.plugin.fastcgi.path_info: true
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult
from functions import logger_easyhaproxy


class FastcgiPlugin(PluginInterface):
    """Plugin to configure FastCGI parameters for PHP-FPM"""

    def __init__(self):
        self.enabled = True
        self.document_root = "/etc/easyhaproxy/www"
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
            fcgi_app_lines.append(f"    path-info ^(/.+\\.php)(/.*)?$")

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
            global_configs=[fcgi_app_definition]  # For top-level injection (new in v2.0)
        )
```

### Example 3: JWT Validator Plugin (DOMAIN)

Validate JWT tokens using HAProxy's built-in JWT functionality with path-based validation.

```python
"""
JWT Validator Plugin for EasyHAProxy

This plugin validates JWT tokens using HAProxy's built-in JWT functionality.
It runs as a DOMAIN plugin (once per domain).

Configuration:
    - enabled: Enable/disable the plugin (default: true)
    - algorithm: JWT signing algorithm (default: RS256)
    - issuer: Expected JWT issuer (optional, set to "none"/"null" to skip validation)
    - audience: Expected JWT audience (optional, set to "none"/"null" to skip validation)
    - pubkey_path: Path to public key file (required if pubkey not provided)
    - pubkey: Public key content as base64-encoded string (required if pubkey_path not provided)
    - paths: List of paths that require JWT validation (optional, if not set ALL domain is protected)
    - only_paths: If true, only specified paths are accessible; if false (default), only specified paths require JWT validation

Path Validation Logic:
    - No paths configured: ALL requests to the domain require JWT validation (default behavior)
    - Paths configured + only_paths=false: Only specified paths require JWT validation, others pass through
    - Paths configured + only_paths=true: Only specified paths are accessible (with JWT), all others are denied

Example YAML config:
    plugins:
      jwt_validator:
        enabled: true
        algorithm: RS256
        issuer: https://myaccount.auth0.com/
        audience: https://api.mywebsite.com
        pubkey_path: /etc/easyhaproxy/jwt_keys/pubkey.pem
        paths:
          - /api/admin
          - /api/sensitive
        only_paths: false

Example Container Label:
    easyhaproxy.http.plugins: "jwt_validator"
    easyhaproxy.http.plugin.jwt_validator.algorithm: RS256
    easyhaproxy.http.plugin.jwt_validator.issuer: https://auth.example.com/
    easyhaproxy.http.plugin.jwt_validator.audience: https://api.example.com
    easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/easyhaproxy/jwt_keys/api_pubkey.pem
    easyhaproxy.http.plugin.jwt_validator.paths: /api/admin,/api/sensitive
    easyhaproxy.http.plugin.jwt_validator.only_paths: true
"""

import base64
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import (
    InitializationResult,
    PluginInterface,
    PluginType,
    PluginContext,
    PluginResult,
    ResourceRequest
)
from functions import Functions, logger_easyhaproxy


class JwtValidatorPlugin(PluginInterface):
    """Plugin to validate JWT tokens"""

    def __init__(self):
        self.enabled = True
        self.algorithm = "RS256"
        self.issuer = None  # Optional
        self.audience = None  # Optional
        self.pubkey_path = None  # Path to public key file
        self.pubkey = None  # Public key content (alternative to pubkey_path)
        self.paths = []  # List of paths that require JWT validation
        self.only_paths = False  # If true, only specified paths are accessible
        # Make JWT_KEYS_DIR configurable via environment variable
        self.jwt_keys_dir = os.getenv("EASYHAPROXY_JWT_KEYS_DIR", "/etc/easyhaproxy/jwt_keys")

    @property
    def name(self) -> str:
        return "jwt_validator"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        """
        Configure the plugin

        Args:
            config: Dictionary with configuration options
                - enabled: Whether plugin is enabled
                - algorithm: JWT signing algorithm (default: RS256)
                - issuer: Expected JWT issuer (optional)
                - audience: Expected JWT audience (optional)
                - pubkey_path: Path to public key file
                - pubkey: Public key content as base64-encoded string
                - paths: List of paths that require JWT validation (optional)
                - only_paths: If true, only specified paths are accessible (default: false)
        """
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "algorithm" in config:
            self.algorithm = config["algorithm"]

        # Parse issuer (optional - if not set, issuer validation is skipped)
        if "issuer" in config:
            issuer = str(config["issuer"]).strip()
            if issuer:  # Only set if not empty
                self.issuer = issuer

        # Parse audience (optional - if not set, audience validation is skipped)
        if "audience" in config:
            audience = str(config["audience"]).strip()
            if audience:  # Only set if not empty
                self.audience = audience

        # Public key configuration
        if "pubkey_path" in config:
            self.pubkey_path = config["pubkey_path"]

        if "pubkey" in config:
            # Decode from base64 (consistent with sslcert parameter)
            self.pubkey = base64.b64decode(config["pubkey"]).decode('ascii')

        # Path configuration
        if "paths" in config:
            paths_config = config["paths"]
            if isinstance(paths_config, list):
                self.paths = [str(p).strip() for p in paths_config if str(p).strip()]
            elif isinstance(paths_config, str):
                # Support comma-separated paths for container labels
                self.paths = [p.strip() for p in paths_config.split(",") if p.strip()]
            else:
                self.paths = []

        if "only_paths" in config:
            self.only_paths = str(config["only_paths"]).lower() in ["true", "1", "yes"]

    def initialize(self) -> InitializationResult:
        """
        Initialize plugin resources - create JWT keys directory (new in v2.0)

        Returns:
            InitializationResult with directory creation request
        """
        return InitializationResult(
            resources=[
                ResourceRequest(resource_type="directory", path=self.jwt_keys_dir)
            ]
        )

    def process(self, context: PluginContext) -> PluginResult:
        """
        Generate HAProxy config to validate JWT tokens

        Args:
            context: Plugin execution context with domain information

        Returns:
            PluginResult with HAProxy configuration snippet
        """
        if not self.enabled:
            return PluginResult()

        # Determine public key file path
        if self.pubkey_path:
            pubkey_file = self.pubkey_path
        elif self.pubkey:
            # Generate path for pubkey based on domain
            domain_safe = context.domain.replace(".", "_").replace(":", "_")
            pubkey_file = f"{self.jwt_keys_dir}/{domain_safe}_pubkey.pem"

            # Write the public key file (defensive - normally created by initialize())
            try:
                os.makedirs(self.jwt_keys_dir, exist_ok=True)
                Functions.save(pubkey_file, self.pubkey)
                logger_easyhaproxy.debug(f"Wrote JWT public key to {pubkey_file} for domain {context.domain}")
            except (PermissionError, OSError) as e:
                logger_easyhaproxy.debug(f"Could not write JWT public key file: {e}")
        else:
            logger_easyhaproxy.warning(f"JWT validator plugin for {context.domain}: No pubkey or pubkey_path configured")
            return PluginResult()

        # Build HAProxy configuration
        lines = ["# JWT Validator - Validate JWT tokens"]

        # Determine path condition suffix
        path_condition = ""
        if self.paths:
            # Define ACL for protected paths
            lines.append("")
            lines.append("# Define paths that require JWT validation")
            for path in self.paths:
                lines.append(f"acl jwt_protected_path path_beg {path}")
            lines.append("")

            if self.only_paths:
                # Deny all paths that are not in the protected list
                lines.append("# Deny access to paths not in the protected list")
                lines.append("http-request deny content-type 'text/html' string 'Access denied' unless jwt_protected_path")
                lines.append("")
                # All remaining requests are on protected paths, no condition needed
                path_condition = ""
            else:
                # Only validate JWT on protected paths
                path_condition = " if jwt_protected_path"

        # Check for Authorization header
        lines.append(f"http-request deny content-type 'text/html' string 'Missing Authorization HTTP header' unless {{ req.hdr(authorization) -m found }}{path_condition}")

        # Extract JWT parts
        lines.append("")
        lines.append("# Extract JWT header and payload")
        lines.append(f"http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg'){path_condition}")
        lines.append(f"http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss'){path_condition}")
        lines.append(f"http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud'){path_condition}")
        lines.append(f"http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int'){path_condition}")

        # Validate JWT
        lines.append("")
        lines.append("# Validate JWT")
        lines.append(f"http-request deny content-type 'text/html' string 'Unsupported JWT signing algorithm' unless {{ var(txn.alg) -m str {self.algorithm} }}{path_condition}")

        # Validate issuer (if configured)
        if self.issuer:
            lines.append(f"http-request deny content-type 'text/html' string 'Invalid JWT issuer' unless {{ var(txn.iss) -m str {self.issuer} }}{path_condition}")

        # Validate audience (if configured)
        if self.audience:
            lines.append(f"http-request deny content-type 'text/html' string 'Invalid JWT audience' unless {{ var(txn.aud) -m str {self.audience} }}{path_condition}")

        # Validate signature
        lines.append(f"http-request deny content-type 'text/html' string 'Invalid JWT signature' unless {{ http_auth_bearer,jwt_verify(txn.alg,\"{pubkey_file}\") -m int 1 }}{path_condition}")

        # Validate expiration
        lines.append("")
        lines.append("# Validate expiration")
        lines.append(f"http-request set-var(txn.now) date(){path_condition}")
        lines.append(f"http-request deny content-type 'text/html' string 'JWT has expired' if {{ var(txn.exp),sub(txn.now) -m int lt 0 }}{path_condition}")

        haproxy_config = "\n".join(lines)

        # Build metadata
        metadata = {
            "domain": context.domain,
            "algorithm": self.algorithm,
            "pubkey_file": pubkey_file,
            "validates_issuer": self.issuer is not None,
            "validates_audience": self.audience is not None,
            "path_validation": len(self.paths) > 0,
            "only_paths": self.only_paths
        }

        if self.issuer:
            metadata["issuer"] = self.issuer
        if self.audience:
            metadata["audience"] = self.audience
        if self.pubkey:
            metadata["pubkey_content"] = self.pubkey
        if self.paths:
            metadata["paths"] = self.paths

        return PluginResult(
            haproxy_config=haproxy_config,
            modified_easymapping=None,
            metadata=metadata
        )
```

### Example 4: Cleanup Plugin (GLOBAL)

Perform cleanup tasks during each discovery cycle.

```python
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

import os
import sys
import glob
import time

# Add parent directory to path for imports
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
```

---

## Environment Variables

**New in v2.0:** Plugins can use environment variables for configuration.

### Core Environment Variables

- `EASYHAPROXY_PLUGINS_DIR` - Override plugin directory (default: `/etc/easyhaproxy/plugins`)
- `EASYHAPROXY_PLUGINS_ENABLED` - Comma-separated list of enabled plugins
- `EASYHAPROXY_PLUGINS_ABORT_ON_ERROR` - Abort on plugin errors (default: `false`)

### Plugin-Specific Environment Variables

- `EASYHAPROXY_PLUGIN_<PLUGIN_NAME>_<CONFIG_KEY>` - Configure plugin settings

**Example:**
```bash
EASYHAPROXY_PLUGINS_ENABLED=jwt_validator,cloudflare
EASYHAPROXY_PLUGIN_JWT_VALIDATOR_ALGORITHM=RS256
EASYHAPROXY_PLUGIN_JWT_VALIDATOR_ISSUER=https://auth.example.com/
EASYHAPROXY_JWT_KEYS_DIR=/custom/path/jwt_keys  # Plugin-defined env var
```

### Plugin Resource Directories

**New in v2.0:** Plugins can make their resource directories configurable via environment variables.

**Example:**
```python
class MyPlugin(PluginInterface):
    def __init__(self):
        # Make resource directory configurable
        self.data_dir = os.getenv("EASYHAPROXY_MY_PLUGIN_DATA_DIR", "/etc/easyhaproxy/my_plugin_data")

    def initialize(self) -> InitializationResult:
        return InitializationResult(
            resources=[
                ResourceRequest(resource_type="directory", path=self.data_dir)
            ]
        )
```

---

## Best Practices

### 1. Use Plugin Initialization for Resource Setup

**[New in v2.0]** Use the `initialize()` method to request file system resources.

**Do:**
```python
def initialize(self) -> InitializationResult:
    return InitializationResult(
        resources=[
            ResourceRequest(resource_type="directory", path=self.data_dir)
        ]
    )

def process(self, context: PluginContext) -> PluginResult:
    # Directory already exists, just use it
    filepath = os.path.join(self.data_dir, "data.txt")
    with open(filepath, 'w') as f:
        f.write("data")
```

**Don't:**
```python
def process(self, context: PluginContext) -> PluginResult:
    # Creating directories in process() is inefficient
    os.makedirs(self.data_dir, exist_ok=True)  # Called on every execution!
    filepath = os.path.join(self.data_dir, "data.txt")
```

### 2. Use Typed Result Fields for Config Injection

**[New in v2.0]** Use `global_configs` and `defaults_configs` fields instead of metadata.

**Do:**
```python
return PluginResult(
    haproxy_config="use-fcgi-app fcgi_example",
    global_configs=["fcgi-app fcgi_example\n    docroot /var/www"],
    defaults_configs=['log-format "..."']
)
```

**Don't:**
```python
# Deprecated: Don't put config in metadata
return PluginResult(
    haproxy_config="use-fcgi-app fcgi_example",
    metadata={
        "fcgi_app_definition": "fcgi-app fcgi_example\n    docroot /var/www"  # Wrong!
    }
)
```

### 3. Error Handling

Always handle errors gracefully to avoid breaking HAProxy configuration.

**Do:**
```python
def configure(self, config: dict) -> None:
    if "port" in config:
        try:
            self.port = int(config["port"])
        except ValueError:
            logger_easyhaproxy.warning(f"Invalid port value: {config['port']}, using default")
            self.port = 8080
```

**Don't:**
```python
def configure(self, config: dict) -> None:
    self.port = int(config["port"])  # Crashes if not an integer!
```

### 4. Configuration Validation

Validate configuration during `configure()` phase, not during `process()`.

**Do:**
```python
def configure(self, config: dict) -> None:
    if "allowed_ips" in config:
        ips_str = str(config["allowed_ips"])
        self.allowed_ips = [ip.strip() for ip in ips_str.split(",") if ip.strip()]

        # Validate IPs
        if not self.allowed_ips:
            logger_easyhaproxy.warning("IP whitelist plugin: No valid IPs configured")
            self.enabled = False
```

**Don't:**
```python
def process(self, context: PluginContext) -> PluginResult:
    # Too late - validation should happen during configure()
    if not self.allowed_ips:
        raise ValueError("No IPs configured")
```

### 5. Use Metadata for Debugging

Include useful debugging information in metadata.

```python
return PluginResult(
    haproxy_config=config_snippet,
    metadata={
        "domain": context.domain,
        "rules_generated": 5,
        "algorithm": self.algorithm,
        "validation_enabled": True,
        "paths_protected": self.paths
    }
)
```

### 6. Handle Boolean Configuration

Support multiple boolean formats (true/false, 1/0, yes/no).

```python
def configure(self, config: dict) -> None:
    if "enabled" in config:
        self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]
```

### 7. Support Multiple Configuration Formats

Support both list and comma-separated string formats for lists.

```python
def configure(self, config: dict) -> None:
    if "paths" in config:
        paths_config = config["paths"]
        if isinstance(paths_config, list):
            self.paths = [str(p).strip() for p in paths_config if str(p).strip()]
        elif isinstance(paths_config, str):
            # Support comma-separated paths for container labels
            self.paths = [p.strip() for p in paths_config.split(",") if p.strip()]
        else:
            self.paths = []
```

### 8. Use Descriptive Names

Use clear, descriptive names for plugins, configuration keys, and ACLs.

**Do:**
```python
@property
def name(self) -> str:
    return "jwt_validator"  # Clear and descriptive

# In generated config:
acl jwt_protected_path path_beg /api
```

**Don't:**
```python
@property
def name(self) -> str:
    return "jv"  # Too cryptic

# In generated config:
acl p1 path_beg /api  # What is p1?
```

### 9. Document Your Plugin

Include comprehensive docstrings with configuration examples.

```python
"""
Plugin Name for EasyHAProxy

Brief description of what the plugin does.

Configuration:
    - option1: Description (default: value)
    - option2: Description (default: value)

Example YAML config:
    plugins:
      plugin_name:
        option1: value1
        option2: value2

Example Container Label:
    easyhaproxy.http.plugins: "plugin_name"
    easyhaproxy.http.plugin.plugin_name.option1: value1
"""
```

### 10. Return Empty Result When Disabled

Always check `enabled` flag and return empty result early.

```python
def process(self, context: PluginContext) -> PluginResult:
    if not self.enabled:
        return PluginResult()

    # Plugin logic here...
```

### 11. Use Logger Appropriately

Use appropriate log levels for different messages.

```python
from functions import logger_easyhaproxy

# For debugging
logger_easyhaproxy.debug(f"Processing domain: {context.domain}")

# For informational messages
logger_easyhaproxy.info(f"Loaded plugin configuration: {self.name}")

# For warnings (non-fatal issues)
logger_easyhaproxy.warning(f"Invalid configuration value, using default")

# For errors (fatal issues)
logger_easyhaproxy.error(f"Failed to load required file: {filepath}")
```

### 12. Make Domain-Safe Identifiers

Replace special characters when generating HAProxy identifiers.

```python
# Replace dots and colons with underscores for valid HAProxy identifier
domain_safe = context.domain.replace(".", "_").replace(":", "_")
fcgi_app_name = f"fcgi_{domain_safe}"

# example.com:8080 → fcgi_example_com_8080
```

---

## Testing Guidelines

### Unit Testing

Create unit tests for your plugin in `/src/tests/test_plugins.py`.

```python
"""Test cases for MyPlugin"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginContext
from plugins.builtin.my_plugin import MyPlugin


class TestMyPlugin:
    """Test cases for MyPlugin (DOMAIN plugin)"""

    def test_plugin_initialization(self):
        """Test plugin initializes with correct defaults"""
        plugin = MyPlugin()
        assert plugin.name == "my_plugin"
        assert plugin.enabled is True
        assert plugin.my_setting == "default_value"

    def test_plugin_configuration(self):
        """Test plugin configuration"""
        plugin = MyPlugin()

        # Test custom setting
        plugin.configure({"my_setting": "custom_value"})
        assert plugin.my_setting == "custom_value"

        # Test disabling
        plugin.configure({"enabled": "false"})
        assert plugin.enabled is False

        # Test enabling with various values
        plugin.configure({"enabled": "true"})
        assert plugin.enabled is True

        plugin.configure({"enabled": "1"})
        assert plugin.enabled is True

    def test_plugin_generates_config(self):
        """Test plugin generates correct HAProxy config"""
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
        assert "My Plugin" in result.haproxy_config
        assert "X-My-Header test_value" in result.haproxy_config
        assert result.metadata["domain"] == "example.com"
        assert result.metadata["setting_value"] == "test_value"

    def test_plugin_disabled(self):
        """Test plugin returns empty config when disabled"""
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
        assert result.metadata == {}
```

### Integration Testing

Test your plugin in a real environment.

**Create test fixture:**

```bash
# Create test service configuration
mkdir -p /home/jg/Projects/opensource/github/byjg/docker-easy-haproxy/src/tests/fixtures/services-my-plugin
```

**Create expected output:**

```bash
# Create expected HAProxy configuration
cat > /home/jg/Projects/opensource/github/byjg/docker-easy-haproxy/src/tests/expected/services-my-plugin.txt << 'EOF'
# Generated HAProxy configuration with my_plugin enabled
backend be_example_com_80
    # My Plugin - Custom functionality
    http-request set-header X-My-Header custom_value
EOF
```

**Run tests:**

```bash
cd /home/jg/Projects/opensource/github/byjg/docker-easy-haproxy/src
python -m pytest tests/test_plugins.py::TestMyPlugin -v
```

### Manual Testing

Test your plugin with a live container:

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    image: nginx:latest
    labels:
      easyhaproxy.http.host: test.example.com
      easyhaproxy.http.port: 80
      easyhaproxy.http.plugins: my_plugin
      easyhaproxy.http.plugin.my_plugin.my_setting: test_value

  haproxy:
    build: .
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./my_plugin.py:/etc/easyhaproxy/plugins/my_plugin.py
    environment:
      - EASYHAPROXY_DISCOVER=docker
```

**Verify plugin loading:**

```bash
docker-compose up -d
docker-compose logs haproxy | grep my_plugin
```

Expected output:
```
[INFO] Loaded external plugin: my_plugin (domain)
[DEBUG] Configured plugin: my_plugin with config: {'my_setting': 'test_value'}
[DEBUG] Executing domain plugin: my_plugin for domain: test.example.com
```

**Verify generated configuration:**

```bash
docker-compose exec haproxy cat /etc/easyhaproxy/haproxy/haproxy.cfg | grep -A 5 "My Plugin"
```

---

## Troubleshooting

### Plugin Not Loading

**Symptom:** Plugin not appearing in logs.

**Possible causes:**

1. **File not in plugins directory**
   ```bash
   ls -la /etc/easyhaproxy/plugins/
   # Ensure my_plugin.py exists
   ```

2. **Invalid Python syntax**
   ```bash
   python3 -m py_compile /etc/easyhaproxy/plugins/my_plugin.py
   # Check for syntax errors
   ```

3. **Class doesn't inherit PluginInterface**
   ```python
   # Wrong:
   class MyPlugin:
       pass

   # Correct:
   class MyPlugin(PluginInterface):
       pass
   ```

4. **Missing required imports**
   ```python
   # Add this at the top of your plugin:
   import os
   import sys
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   from plugins import PluginInterface, PluginType, PluginContext, PluginResult
   ```

### Plugin Not Executing

**Symptom:** Plugin loads but doesn't execute.

**Possible causes:**

1. **Plugin not enabled in configuration**
   ```yaml
   # Add to config.yaml:
   plugins:
     enabled: [my_plugin]
   ```

2. **Wrong plugin type for use case**
   - GLOBAL plugins don't receive domain context
   - DOMAIN plugins execute per domain, not globally

3. **Plugin disabled via configuration**
   ```python
   # Check enabled flag:
   if not self.enabled:
       return PluginResult()  # Plugin is disabled
   ```

### Configuration Not Applied

**Symptom:** Plugin executes but configuration not applied.

**Possible causes:**

1. **Configuration key mismatch**
   ```yaml
   # Wrong:
   plugins:
     config:
       my-plugin:  # Hyphen instead of underscore
         my_setting: value

   # Correct:
   plugins:
     config:
       my_plugin:  # Must match plugin.name
         my_setting: value
   ```

2. **Configuration not parsed in configure()**
   ```python
   def configure(self, config: dict) -> None:
       # Make sure to check for your config key:
       if "my_setting" in config:
           self.my_setting = config["my_setting"]
   ```

### HAProxy Configuration Invalid

**Symptom:** HAProxy fails to reload with syntax error.

**Possible causes:**

1. **Invalid HAProxy syntax in generated config**
   ```bash
   # Test configuration manually:
   haproxy -c -f /etc/easyhaproxy/haproxy/haproxy.cfg
   ```

2. **Missing quotes or escaping**
   ```python
   # Wrong:
   config = f"http-request set-header X-Value {value}"

   # Correct (if value contains spaces):
   config = f"http-request set-header X-Value \"{value}\""
   ```

3. **Invalid ACL names**
   ```python
   # Wrong (contains special characters):
   acl_name = f"acl_{context.domain}"  # example.com → acl_example.com (dot invalid)

   # Correct:
   acl_name = f"acl_{context.domain.replace('.', '_')}"  # example_com
   ```

### Plugin Errors

**Symptom:** Plugin crashes or throws exceptions.

**Debug steps:**

1. **Enable debug logging**
   ```bash
   # Set environment variable:
   EASYHAPROXY_LOG_LEVEL=DEBUG
   ```

2. **Add debug statements**
   ```python
   def process(self, context: PluginContext) -> PluginResult:
       logger_easyhaproxy.debug(f"Plugin {self.name} processing domain: {context.domain}")
       logger_easyhaproxy.debug(f"Plugin config: enabled={self.enabled}, setting={self.my_setting}")
       # ... rest of plugin logic
   ```

3. **Check abort_on_error setting**
   ```python
   # In PluginManager initialization:
   # abort_on_error=False (default) - logs errors and continues
   # abort_on_error=True - crashes on errors for debugging
   ```

4. **Wrap risky operations**
   ```python
   def process(self, context: PluginContext) -> PluginResult:
       try:
           # Risky operation
           result = self.do_something_risky()
       except Exception as e:
           logger_easyhaproxy.error(f"Plugin {self.name} error: {str(e)}")
           return PluginResult()  # Return empty result on error
   ```

### Metadata Not Appearing in Logs

**Symptom:** Plugin metadata not visible in logs.

**Solution:**

1. **Enable debug logging**
   ```bash
   EASYHAPROXY_LOG_LEVEL=DEBUG
   ```

2. **Ensure metadata is returned**
   ```python
   return PluginResult(
       haproxy_config=config,
       metadata={
           "domain": context.domain,
           "setting": self.my_setting
       }
   )
   ```

---

## Distribution

### Sharing Your Plugin

#### Option 1: Single File Distribution

Share your plugin as a single `.py` file:

```bash
# Users copy the file to their plugins directory:
cp my_plugin.py /etc/easyhaproxy/plugins/
```

**Advantages:**
- Simple distribution
- No installation required
- Works immediately

**Best for:** Simple plugins without dependencies

#### Option 2: GitHub Repository

Create a GitHub repository with installation instructions:

```
my-easyhaproxy-plugin/
├── README.md
├── my_plugin.py
├── tests/
│   └── test_my_plugin.py
└── examples/
    ├── docker-compose.yml
    └── config.yaml
```

**Installation:**
```bash
# Users download and install:
wget https://raw.githubusercontent.com/user/my-plugin/main/my_plugin.py -O /etc/easyhaproxy/plugins/my_plugin.py
```

#### Option 3: Docker Image with Plugin

Create a custom EasyHAProxy image with your plugin included:

```dockerfile
FROM byjg/easy-haproxy:latest

# Copy plugin to builtin directory
COPY my_plugin.py /app/src/plugins/builtin/

# Optional: Add default configuration
COPY plugin_config.yaml /etc/easyhaproxy/static/config.yaml
```

**Build and distribute:**
```bash
docker build -t my-org/easy-haproxy-with-plugin:latest .
docker push my-org/easy-haproxy-with-plugin:latest
```

### Documentation

Include comprehensive documentation with your plugin:

```markdown
# My Plugin for EasyHAProxy

Brief description of what your plugin does.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

### Docker
\`\`\`bash
wget https://example.com/my_plugin.py -O /etc/easyhaproxy/plugins/my_plugin.py
\`\`\`

### Kubernetes
\`\`\`yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: haproxy-plugins
data:
  my_plugin.py: |
    # Plugin content here
\`\`\`

## Configuration

### Options

- `enabled` (boolean, default: true) - Enable/disable plugin
- `option1` (string, default: "value") - Description

### Examples

#### Docker Compose
\`\`\`yaml
services:
  web:
    labels:
      easyhaproxy.http.plugins: my_plugin
      easyhaproxy.http.plugin.my_plugin.option1: value
\`\`\`

#### YAML Config
\`\`\`yaml
plugins:
  my_plugin:
    enabled: true
    option1: value
\`\`\`

## Troubleshooting

Common issues and solutions.

## License

MIT
```

### Version Control

Use semantic versioning for your plugin:

```python
class MyPlugin(PluginInterface):
    """
    My Plugin for EasyHAProxy

    Version: 1.0.0
    Author: Your Name
    License: MIT
    """

    VERSION = "1.0.0"
```

### Contributing to EasyHAProxy

To contribute your plugin to the EasyHAProxy core:

1. **Fork the repository**
   ```bash
   git clone https://github.com/byjg/docker-easy-haproxy.git
   ```

2. **Add your plugin to builtin/**
   ```bash
   cp my_plugin.py src/plugins/builtin/
   ```

3. **Add tests**
   ```bash
   # Add test class to src/tests/test_plugins.py
   ```

4. **Update documentation**
   ```bash
   # Add plugin to docs/plugins.md
   ```

5. **Create pull request**
   - Describe plugin functionality
   - Include usage examples
   - Show test results

---

## Conclusion

You now have a comprehensive understanding of the EasyHAProxy plugin system. Key takeaways:

- **Plugin Types:** GLOBAL (once per cycle) vs DOMAIN (per domain)
- **Plugin Lifecycle:** Load → Configure → Execute → Result
- **API:** PluginInterface, PluginContext, PluginResult
- **Best Practices:** Error handling, validation, logging, testing
- **Distribution:** Single file, GitHub, or Docker image

For more examples, see the builtin plugins in `/src/plugins/builtin/`:
- `cloudflare.py` - Simple DOMAIN plugin
- `fastcgi.py` - Advanced DOMAIN plugin with complex config
- `jwt_validator.py` - Security plugin with path-based logic
- `ip_whitelist.py` - Access control plugin
- `cleanup.py` - GLOBAL plugin example

Happy plugin development!
