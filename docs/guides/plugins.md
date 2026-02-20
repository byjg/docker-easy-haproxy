---
sidebar_position: 3
sidebar_label: "Using Plugins"
---

# Using Plugins

EasyHAProxy supports a plugin system that extends HAProxy configuration with custom functionality. This guide explains how to use and configure plugins.

## What are Plugins?

Plugins automatically run during the discovery cycle and can:
- Add HAProxy configuration directives
- Perform maintenance tasks
- Modify discovery data
- Integrate with external services

## Plugin Types

### Global Plugins

Execute **once per discovery cycle** regardless of how many domains are discovered.

**Use cases:**
- Cleanup tasks
- Global monitoring
- DNS updates
- Log management

**Example:** `cleanup` plugin

### Domain Plugins

Execute **once for each discovered domain/host**.

**Use cases:**
- Domain-specific configuration
- IP restoration (Cloudflare)
- Path blocking
- Custom headers per domain

**Examples:** `cloudflare`, `deny_pages`

## Built-in Plugins

EasyHAProxy includes several built-in plugins ready to use:

- [Cloudflare](../reference/plugins/cloudflare.md) - Restore visitor IP from Cloudflare CDN
- [Cleanup](../reference/plugins/cleanup.md) - Cleanup temporary files
- [Deny Pages](../reference/plugins/deny-pages.md) - Block specific paths
- [IP Whitelist](../reference/plugins/ip-whitelist.md) - Restrict access to IPs/CIDR ranges
- [JWT Validator](../reference/plugins/jwt-validator.md) - Validate JWT tokens
- [FastCGI](../reference/plugins/fastcgi.md) - Configure PHP-FPM and FastCGI applications

## Configuration Methods

Plugins can be configured using different methods depending on your deployment environment:

### 1. Kubernetes Annotations (Ingress Resources)

Enable and configure domain plugins for specific Kubernetes ingresses:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
    # Enable plugins
    easyhaproxy.plugins: "jwt_validator,deny_pages"
    # Configure jwt_validator plugin (protect specific paths only)
    easyhaproxy.plugin.jwt_validator.algorithm: "RS256"
    easyhaproxy.plugin.jwt_validator.issuer: "https://auth.example.com/"
    easyhaproxy.plugin.jwt_validator.audience: "https://api.example.com"
    easyhaproxy.plugin.jwt_validator.pubkey_path: "/etc/easyhaproxy/jwt_keys/api_pubkey.pem"
    easyhaproxy.plugin.jwt_validator.paths: "/api/admin,/api/users"
    easyhaproxy.plugin.jwt_validator.only_paths: "false"
    # Configure deny_pages plugin
    easyhaproxy.plugin.deny_pages.paths: "/admin,/private"
    easyhaproxy.plugin.deny_pages.status_code: "403"
  name: api-ingress
  namespace: production
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - backend:
          service:
            name: api-service
            port:
              number: 8080
        pathType: ImplementationSpecific
```

**Annotation format:**
- Enable plugins: `easyhaproxy.plugins: plugin1,plugin2`
- Configure plugin: `easyhaproxy.plugin.<plugin_name>.<config_key>: value`

See the [Kubernetes guide](../getting-started/kubernetes.md) for more examples.

### 2. Container Labels (Docker/Docker Compose)

Enable and configure domain plugins for specific Docker containers:

```yaml
services:
  webapp:
    image: myapp:latest
    labels:
      easyhaproxy.http.host: example.com
      easyhaproxy.http.port: 80
      # Enable multiple plugins
      easyhaproxy.http.plugins: cloudflare,deny_pages
      # Configure deny_pages plugin
      easyhaproxy.http.plugin.deny_pages.paths: /admin,/api/internal
      easyhaproxy.http.plugin.deny_pages.status_code: 403
```

**Label format:**
- Enable plugins: `easyhaproxy.<definition>.plugins: plugin1,plugin2`
- Configure plugin: `easyhaproxy.<definition>.plugin.<plugin_name>.<config_key>: value`

**Where `<definition>` is:** `http`, `https`, `tcp`, etc.

### 3. Static YAML Configuration

Configure plugins in `/etc/easyhaproxy/static/config.yaml`:

```yaml
plugins:
  # Global settings
  abort_on_error: false  # Log and continue on errors (recommended)

  # Enable GLOBAL plugins (run once per discovery cycle)
  enabled: [cleanup]

  # Configure plugins (both global and domain plugins)
  config:
    # Global plugin configuration (cleanup runs once per cycle)
    cleanup:
      enabled: true
      max_idle_time: 600

    # Domain plugin configuration (applies to ALL domains by default)
    cloudflare:
      enabled: true           # Apply to all domains
      use_builtin_ips: true   # Use built-in Cloudflare IPs

    # Domain plugin disabled by default (enable per-domain via labels/annotations)
    deny_pages:
      enabled: false
```

**Important distinctions:**

- **Global plugins** (like `cleanup`): Run once per discovery cycle, configured here only
- **Domain plugins** (like `cloudflare`, `deny_pages`, `jwt_validator`):
  - Configuration here sets **defaults for ALL domains**
  - Can be enabled/disabled per-domain via container labels or Kubernetes annotations
  - Per-domain configuration overrides these defaults

### 4. Environment Variables

Configure plugins via environment variables. **Note:** Environment variables set system-wide defaults and cannot configure plugins per-domain.

```bash
# Enable GLOBAL plugins (run once per discovery cycle)
EASYHAPROXY_PLUGINS_ENABLED=cleanup
EASYHAPROXY_PLUGINS_ABORT_ON_ERROR=false

# Configure GLOBAL plugins
EASYHAPROXY_PLUGIN_CLEANUP_ENABLED=true
EASYHAPROXY_PLUGIN_CLEANUP_MAX_IDLE_TIME=600

# Configure DOMAIN plugins (sets defaults for ALL domains)
EASYHAPROXY_PLUGIN_CLOUDFLARE_ENABLED=true
EASYHAPROXY_PLUGIN_CLOUDFLARE_USE_BUILTIN_IPS=true
```

**Variable format:**
- Enable global plugins: `EASYHAPROXY_PLUGINS_ENABLED=plugin1,plugin2`
- Configure plugin: `EASYHAPROXY_PLUGIN_<PLUGIN_NAME>_<CONFIG_KEY>=value`

## Common Use Cases

### Protect API with JWT Authentication

**Secure entire API domain:**

```yaml
services:
  api:
    labels:
      easyhaproxy.http.host: api.example.com
      easyhaproxy.http.plugins: jwt_validator
      easyhaproxy.http.plugin.jwt_validator.issuer: https://auth0.myapp.com/
      easyhaproxy.http.plugin.jwt_validator.audience: https://api.example.com
      easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/easyhaproxy/jwt_keys/api_pubkey.pem
    volumes:
      - ./auth_pubkey.pem:/etc/easyhaproxy/jwt_keys/api_pubkey.pem:ro
```

### Restrict Admin Panel to Office IPs

```yaml
labels:
  easyhaproxy.http.host: admin.example.com
  easyhaproxy.http.plugins: ip_whitelist
  easyhaproxy.http.plugin.ip_whitelist.allowed_ips: 203.0.113.0/24,198.51.100.42
```

### Protect Admin Paths

Block access to WordPress admin and other sensitive paths:

```yaml
labels:
  easyhaproxy.http.host: wordpress.example.com
  easyhaproxy.http.plugins: deny_pages
  easyhaproxy.http.plugin.deny_pages.paths: /wp-admin,/wp-login.php,/.env
  easyhaproxy.http.plugin.deny_pages.status_code: 404
```

### Cloudflare IP Restoration

```yaml
labels:
  easyhaproxy.http.host: myapp.com
  easyhaproxy.http.plugins: cloudflare
```

### Multiple Plugins Together

```yaml
labels:
  easyhaproxy.http.host: secure-app.com
  easyhaproxy.http.plugins: cloudflare,deny_pages
  easyhaproxy.http.plugin.deny_pages.paths: /admin,/config
  easyhaproxy.http.plugin.deny_pages.status_code: 403
```

### Automatic Cleanup

```yaml
# /etc/easyhaproxy/static/config.yaml
plugins:
  enabled: [cleanup]
  config:
    cleanup:
      enabled: true
      max_idle_time: 3600  # 1 hour
```

## Error Handling

### Log and Continue (Recommended)

By default, plugin errors are logged as warnings and discovery continues:

```yaml
plugins:
  abort_on_error: false  # Default
```

### Abort on Error

Stop discovery cycle if any plugin fails:

```yaml
plugins:
  abort_on_error: true
```

## Troubleshooting

### Enable Debug Logging

```bash
EASYHAPROXY_LOG_LEVEL=DEBUG
```

**Look for:**
```
INFO: Loaded builtin plugin: cloudflare (domain)
INFO: Loaded builtin plugin: cleanup (global)
DEBUG: Executing domain plugin: cloudflare for domain: example.com
DEBUG: Plugin cloudflare metadata: {'domain': 'example.com', 'ip_list_path': '/etc/easyhaproxy/cloudflare_ips.lst'}
```

### Plugin Not Loading

**Check:**
1. Plugin file exists in `/etc/easyhaproxy/plugins/` or builtin directory
2. Python syntax is valid
3. Plugin class inherits from `PluginInterface`
4. Check logs for load errors

### Configuration Not Applied

**Check precedence order:**

For Kubernetes deployments:
1. Ingress annotations (highest)
2. YAML configuration
3. Environment variables (lowest)

For Docker deployments:
1. Container labels (highest)
2. YAML configuration
3. Environment variables (lowest)

## Best Practices

1. **Start with log-and-continue mode** - Use `abort_on_error: false` until you're confident plugins are stable
2. **Use container labels for domain-specific config** - Easier to manage per-service
3. **Use YAML/env for global config** - Better for global plugins and defaults
4. **Enable debug logging during testing** - Helps identify configuration issues
5. **Test plugin changes in staging first** - Avoid production surprises

## Limitations

- Plugins must be written in Python
- Domain plugins execute for each domain, so keep them lightweight
- Plugins cannot modify the Jinja2 template structure directly
- Plugin errors in abort mode prevent all configuration updates

## Creating Custom Plugins

Want to create your own plugins? See the [Plugin Developer Guide](plugin-development.md) for detailed instructions on building custom plugins that extend EasyHAProxy functionality.

## Further Reading

- [Plugin Developer Guide](plugin-development.md) - Create custom plugins
- [Container Labels](../reference/container-labels.md) - Label configuration reference
- [Environment Variables](../reference/environment-variables.md) - Environment variable reference
- [Static Configuration](../getting-started/static.md) - YAML configuration reference
- [Kubernetes Guide](../getting-started/kubernetes.md) - Using plugins with Kubernetes
