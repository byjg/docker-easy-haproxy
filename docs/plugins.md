---
sidebar_position: 16
---

# Plugins

EasyHAProxy supports a flexible plugin system that allows you to extend HAProxy configuration with custom functionality. Plugins are automatically invoked during the discovery cycle and can inject HAProxy configuration directives or modify discovery data.

## Plugin Types

### Global Plugins
Global plugins execute **once per discovery cycle**, regardless of how many domains are discovered. They're ideal for:
- Cleanup tasks
- Global monitoring
- DNS updates
- Log management

### Domain Plugins
Domain plugins execute **once for each discovered domain/host**. They're ideal for:
- Domain-specific configuration
- IP restoration (e.g., Cloudflare)
- Path blocking
- Custom headers per domain

## Built-in Plugins

### Cloudflare (Domain Plugin)

Restores the original visitor IP address from Cloudflare's `CF-Connecting-IP` header when requests come through Cloudflare's CDN.

**Configuration:**
```yaml
# /etc/haproxy/static/config.yaml
plugins:
  cloudflare:
    enabled: true
    ip_list_path: /etc/haproxy/cloudflare_ips.lst
```

**Container Label:**
```yaml
services:
  myapp:
    labels:
      easyhaproxy.http.host: example.com
      easyhaproxy.http.plugins: cloudflare
```

**Environment Variable:**
```bash
EASYHAPROXY_PLUGINS_ENABLED=cloudflare
EASYHAPROXY_PLUGIN_CLOUDFLARE_IP_LIST_PATH=/etc/haproxy/cloudflare_ips.lst
```

### Cleanup (Global Plugin)

Performs cleanup tasks during each discovery cycle, such as removing old temporary files.

**Configuration:**
```yaml
# /etc/haproxy/static/config.yaml
plugins:
  cleanup:
    enabled: true
    max_idle_time: 300  # seconds
    cleanup_temp_files: true
```

**Environment Variable:**
```bash
EASYHAPROXY_PLUGINS_ENABLED=cleanup
EASYHAPROXY_PLUGIN_CLEANUP_MAX_IDLE_TIME=600
```

### Deny Pages (Domain Plugin)

Blocks access to specific paths for a domain.

**Configuration:**
```yaml
# /etc/haproxy/static/config.yaml
plugins:
  deny_pages:
    enabled: true
    paths: /admin,/private,/internal
    status_code: 403
```

**Container Label:**
```yaml
services:
  myapp:
    labels:
      easyhaproxy.http.host: example.com
      easyhaproxy.http.plugins: deny_pages
      easyhaproxy.http.plugin.deny_pages.paths: /admin,/private
      easyhaproxy.http.plugin.deny_pages.status_code: 403
```

## Configuration Methods

Plugins can be configured using three methods. Configuration from YAML takes precedence over environment variables.

### 1. Static YAML Configuration

Configure plugins in `/etc/haproxy/static/config.yaml`:

```yaml
plugins:
  # Global settings
  abort_on_error: false  # Log and continue on plugin errors (default)

  # Plugin-specific configuration
  cloudflare:
    enabled: true
    ip_list_path: /etc/haproxy/cloudflare_ips.lst

  cleanup:
    enabled: true
    max_idle_time: 300

  deny_pages:
    enabled: false  # Disable globally, can still be enabled per domain
```

### 2. Environment Variables

Configure plugins via environment variables:

```bash
# Global settings
EASYHAPROXY_PLUGINS_ABORT_ON_ERROR=false
EASYHAPROXY_PLUGINS_ENABLED=cloudflare,cleanup

# Plugin-specific configuration
EASYHAPROXY_PLUGIN_CLOUDFLARE_ENABLED=true
EASYHAPROXY_PLUGIN_CLOUDFLARE_IP_LIST_PATH=/etc/haproxy/cloudflare_ips.lst
EASYHAPROXY_PLUGIN_CLEANUP_MAX_IDLE_TIME=600
```

### 3. Container Labels (Domain Plugins Only)

Enable domain plugins for specific containers:

```yaml
services:
  webapp:
    image: myapp:latest
    labels:
      easyhaproxy.http.host: example.com
      easyhaproxy.http.plugins: cloudflare,deny_pages
      easyhaproxy.http.plugin.deny_pages.paths: /admin,/api/internal
```

## Error Handling

### Log and Continue (Default)

By default, plugin errors are logged as warnings and the discovery cycle continues:

```yaml
plugins:
  abort_on_error: false  # Default
```

This ensures that a failing plugin doesn't prevent HAProxy configuration updates.

### Abort on Error

For critical plugins, you can stop the discovery cycle on errors:

```yaml
plugins:
  abort_on_error: true
```

With this setting, any plugin error will halt configuration generation and the previous HAProxy config remains active until the issue is resolved.

## Custom Plugins

You can create custom plugins by placing Python files in `/etc/haproxy/plugins/`.

### Simple Custom Plugin Example

Create `/etc/haproxy/plugins/custom_header.py`:

```python
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult


class CustomHeaderPlugin(PluginInterface):
    def __init__(self):
        self.enabled = True
        self.header_name = "X-Custom-App"
        self.header_value = "EasyHAProxy"

    @property
    def name(self) -> str:
        return "custom_header"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]
        if "header_name" in config:
            self.header_name = config["header_name"]
        if "header_value" in config:
            self.header_value = config["header_value"]

    def process(self, context: PluginContext) -> PluginResult:
        if not self.enabled:
            return PluginResult()

        haproxy_config = f'http-request set-header {self.header_name} "{self.header_value}"'

        return PluginResult(
            haproxy_config=haproxy_config,
            metadata={"domain": context.domain}
        )
```

### Enable Your Custom Plugin

**YAML:**
```yaml
plugins:
  custom_header:
    enabled: true
    header_name: X-My-Header
    header_value: MyValue
```

**Container Label:**
```yaml
labels:
  easyhaproxy.http.plugins: custom_header
  easyhaproxy.http.plugin.custom_header.header_value: CustomValue
```

## Plugin Development

For detailed information on developing plugins, see the [Plugin Developer Guide](plugin-development.md).

Key points:
- Plugins must inherit from `PluginInterface`
- Implement required methods: `name`, `plugin_type`, `configure`, `process`
- Return `PluginResult` with HAProxy config snippets
- Use `loggerEasyHaproxy` for logging
- Handle errors gracefully

## Use Cases

### 1. Cloudflare IP Restoration

Restore original visitor IPs when using Cloudflare:

```yaml
plugins:
  cloudflare:
    enabled: true
```

Requires Cloudflare IP list at `/etc/haproxy/cloudflare_ips.lst`. See [Cloudflare documentation](https://support.cloudflare.com/hc/en-us/articles/200170786-Restoring-original-visitor-IPs).

### 2. Path Protection

Block sensitive paths from public access:

```yaml
labels:
  easyhaproxy.http.host: myapp.com
  easyhaproxy.http.plugins: deny_pages
  easyhaproxy.http.plugin.deny_pages.paths: /admin,/config,/debug
```

### 3. Automatic Cleanup

Keep your system clean:

```yaml
plugins:
  cleanup:
    enabled: true
    max_idle_time: 3600  # 1 hour
```

### 4. Custom Authentication

Create a plugin to add basic auth:

```python
def process(self, context: PluginContext) -> PluginResult:
    return PluginResult(
        haproxy_config="""http-request auth realm MyApp unless { http_auth(user_list) }"""
    )
```

## Debugging

Enable debug logging to see plugin execution:

```bash
EASYHAPROXY_LOG_LEVEL=DEBUG
```

Look for log messages:
```
INFO: Loaded builtin plugin: cloudflare (domain)
DEBUG: Executing domain plugin: cloudflare for domain: example.com
DEBUG: Plugin cloudflare metadata: {'domain': 'example.com'}
```

## Best Practices

1. **Test plugins independently** before deploying to production
2. **Use log-and-continue mode** unless a plugin is critical
3. **Keep plugin logic simple** - one plugin should do one thing well
4. **Document configuration options** in plugin docstrings
5. **Handle errors gracefully** - return empty PluginResult on errors
6. **Use sensible defaults** so plugins work out of the box

## Limitations

- Plugins are Python-only (no shell scripts)
- Plugins cannot modify the HAProxy template structure
- Domain plugins are executed for each domain, so keep them lightweight
- Plugin errors in abort mode will halt configuration updates

## Further Reading

- [Plugin Developer Guide](plugin-development.md)
- [Container Labels](container-labels.md)
- [Environment Variables](environment-variable.md)
- [Static Configuration](static.md)
