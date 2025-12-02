---
sidebar_position: 16
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

- [Cloudflare](Plugins/cloudflare.md) - Restore visitor IP from Cloudflare CDN
- [Cleanup](Plugins/cleanup.md) - Cleanup temporary files
- [Deny Pages](Plugins/deny-pages.md) - Block specific paths
- [IP Whitelist](Plugins/ip-whitelist.md) - Restrict access to IPs/CIDR ranges
- [JWT Validator](Plugins/jwt-validator.md) - Validate JWT tokens
- [FastCGI](Plugins/fastcgi.md) - Configure PHP-FPM and FastCGI applications

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
    easyhaproxy.plugin.jwt_validator.pubkey_path: "/etc/haproxy/jwt_keys/api_pubkey.pem"
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

See the [Kubernetes guide](kubernetes.md#using-plugins-with-kubernetes) for more examples.

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

Configure plugins in `/etc/haproxy/static/config.yaml`:

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

**Scope limitations:**
- **Global plugins**: Environment variables configure the single instance
- **Domain plugins**: Environment variables set defaults for ALL domains
- **Per-domain configuration**: Use container labels (Docker) or annotations (Kubernetes) instead

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
      easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
    volumes:
      - ./auth_pubkey.pem:/etc/haproxy/jwt_keys/api_pubkey.pem:ro
```

**Protect only admin/sensitive endpoints:**

```yaml
services:
  api:
    labels:
      easyhaproxy.http.host: api.example.com
      easyhaproxy.http.plugins: jwt_validator
      easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
      easyhaproxy.http.plugin.jwt_validator.paths: /api/admin,/api/users,/api/billing
      easyhaproxy.http.plugin.jwt_validator.only_paths: false
    volumes:
      - ./auth_pubkey.pem:/etc/haproxy/jwt_keys/api_pubkey.pem:ro
# /api/health, /api/docs, etc. remain publicly accessible
```

**Restrict API to only allow specific endpoints:**

```yaml
services:
  api:
    labels:
      easyhaproxy.http.host: api.example.com
      easyhaproxy.http.plugins: jwt_validator
      easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
      easyhaproxy.http.plugin.jwt_validator.paths: /api/v1,/api/v2
      easyhaproxy.http.plugin.jwt_validator.only_paths: true
    volumes:
      - ./auth_pubkey.pem:/etc/haproxy/jwt_keys/api_pubkey.pem:ro
# All paths except /api/v1 and /api/v2 are denied
```

### Restrict Admin Panel to Office IPs

Protect admin panel by only allowing access from office network:

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

Restore original visitor IPs for applications behind Cloudflare:

```yaml
labels:
  easyhaproxy.http.host: myapp.com
  easyhaproxy.http.plugins: cloudflare
```

### Multiple Plugins Together

Combine multiple plugins for one domain:

```yaml
labels:
  easyhaproxy.http.host: secure-app.com
  easyhaproxy.http.plugins: cloudflare,deny_pages
  easyhaproxy.http.plugin.deny_pages.paths: /admin,/config
  easyhaproxy.http.plugin.deny_pages.status_code: 403
```

### Automatic Cleanup

Keep your system clean with automatic temp file removal:

```yaml
# /etc/haproxy/static/config.yaml
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

**When to use:** Most situations. Ensures a failing plugin doesn't prevent HAProxy updates.

**Behavior:**
- Plugin errors logged as warnings
- Discovery cycle continues
- Other plugins still execute
- HAProxy config is generated without the failed plugin

### Abort on Error

Stop discovery cycle if any plugin fails:

```yaml
plugins:
  abort_on_error: true
```

**When to use:** Critical plugins where failure should halt deployment.

**Behavior:**
- Plugin error stops discovery
- Previous HAProxy config remains active
- No configuration changes until issue is resolved

## Troubleshooting

### Enable Debug Logging

See detailed plugin execution information:

```bash
EASYHAPROXY_LOG_LEVEL=DEBUG
```

**Look for:**
```
INFO: Loaded builtin plugin: cloudflare (domain)
INFO: Loaded builtin plugin: cleanup (global)
DEBUG: Executing domain plugin: cloudflare for domain: example.com
DEBUG: Plugin cloudflare metadata: {'domain': 'example.com', 'ip_list_path': '/etc/haproxy/cloudflare_ips.lst'}
```

### Plugin Not Loading

**Check:**
1. Plugin file exists in `/etc/haproxy/plugins/` or builtin directory
2. Python syntax is valid
3. Plugin class inherits from `PluginInterface`
4. Check logs for load errors

### Plugin Not Executing

**For domain plugins:**
1. Check container has label: `easyhaproxy.http.plugins: plugin_name`
2. Verify plugin name is correct (case-sensitive)
3. Enable debug logging

**For global plugins:**
1. Check YAML config: `plugins.enabled: [plugin_name]`
2. Or env var: `EASYHAPROXY_PLUGINS_ENABLED=plugin_name`
3. Enable debug logging

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

Per-ingress/per-container settings override global configuration.

### Plugin Output Missing

**Verify:**
1. Plugin is enabled (`enabled: true`)
2. Plugin configuration is correct
3. Plugin's `process()` method returns valid `PluginResult`
4. Check debug logs for plugin execution

## Best Practices

1. **Start with log-and-continue mode** - Use `abort_on_error: false` until you're confident plugins are stable
2. **Use container labels for domain-specific config** - Easier to manage per-service
3. **Use YAML/env for global config** - Better for global plugins and defaults
4. **Enable debug logging during testing** - Helps identify configuration issues
5. **Test plugin changes in staging first** - Avoid production surprises
6. **Keep plugin configurations simple** - Use defaults when possible

## Limitations

- Plugins must be written in Python
- Domain plugins execute for each domain, so keep them lightweight
- Plugins cannot modify the Jinja2 template structure directly
- Plugin errors in abort mode prevent all configuration updates

## Creating Custom Plugins

Want to create your own plugins? See the [Plugin Developer Guide](plugin-development.md) for detailed instructions on building custom plugins that extend EasyHAProxy functionality.

## Further Reading

- [Plugin Developer Guide](plugin-development.md) - Create custom plugins
- [Container Labels](container-labels.md) - Label configuration reference
- [Environment Variables](environment-variable.md) - Environment variable reference
- [Static Configuration](static.md) - YAML configuration reference
- [Kubernetes Guide](kubernetes.md) - Using plugins with Kubernetes
