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

### Cloudflare Plugin (Domain)

Restores the original visitor IP address when requests come through Cloudflare's CDN.

**Why use it:** Cloudflare replaces the visitor's IP with its own. This plugin restores the original IP from the `CF-Connecting-IP` header.

**Configuration options:**
- `enabled` - Enable/disable plugin (default: `true`)
- `ip_list_path` - Path to Cloudflare IP list (default: `/etc/haproxy/cloudflare_ips.lst`)

**Enable via container label:**
```yaml
services:
  myapp:
    labels:
      easyhaproxy.http.host: example.com
      easyhaproxy.http.plugins: cloudflare
```

**Custom IP list path:**
```yaml
labels:
  easyhaproxy.http.plugins: cloudflare
  easyhaproxy.http.plugin.cloudflare.ip_list_path: /custom/path/cf_ips.lst
```

**HAProxy config generated:**
```
# Cloudflare - Restore original visitor IP
acl from_cloudflare src -f /etc/haproxy/cloudflare_ips.lst
http-request set-header X-Forwarded-For %[req.hdr(CF-Connecting-IP)] if from_cloudflare
```

**Required:** Download Cloudflare IP list from [Cloudflare documentation](https://support.cloudflare.com/hc/en-us/articles/200170786).

### Cleanup Plugin (Global)

Performs cleanup tasks during each discovery cycle, such as removing old temporary files.

**Why use it:** Prevents disk space issues by automatically cleaning up temporary files created by EasyHAProxy.

**Configuration options:**
- `enabled` - Enable/disable plugin (default: `true`)
- `max_idle_time` - Maximum age in seconds before deleting files (default: `300`)
- `cleanup_temp_files` - Enable temp file cleanup (default: `true`)

**Enable via YAML:**
```yaml
# /etc/haproxy/static/config.yaml
plugins:
  enabled: [cleanup]
  config:
    cleanup:
      max_idle_time: 600
      cleanup_temp_files: true
```

**Enable via environment variable:**
```bash
EASYHAPROXY_PLUGINS_ENABLED=cleanup
EASYHAPROXY_PLUGIN_CLEANUP_MAX_IDLE_TIME=600
```

### Deny Pages Plugin (Domain)

Blocks access to specific paths for a domain, returning a configurable HTTP status code.

**Why use it:** Protect admin panels, internal APIs, or debugging endpoints from public access.

**Configuration options:**
- `enabled` - Enable/disable plugin (default: `true`)
- `paths` - Comma-separated list of paths to block (e.g., `/admin,/private`)
- `status_code` - HTTP status code to return (default: `403`)

**Enable via container label:**
```yaml
services:
  webapp:
    labels:
      easyhaproxy.http.host: example.com
      easyhaproxy.http.plugins: deny_pages
      easyhaproxy.http.plugin.deny_pages.paths: /admin,/private,/debug
      easyhaproxy.http.plugin.deny_pages.status_code: 404
```

**HAProxy config generated:**
```
# Deny Pages - Block specific paths
acl denied_path path_beg /admin /private /debug
http-request deny deny_status 404 if denied_path
```

### IP Whitelist Plugin (Domain)

Restricts access to a domain to only specific IP addresses or CIDR ranges.

**Why use it:** Restrict access to internal tools, admin panels, or staging environments to only trusted IP addresses.

**Configuration options:**
- `enabled` - Enable/disable plugin (default: `true`)
- `allowed_ips` - Comma-separated list of IPs/CIDR ranges to allow (e.g., `192.168.1.0/24,10.0.0.1`)
- `status_code` - HTTP status code to return for blocked IPs (default: `403`)

**Enable via container label:**
```yaml
services:
  admin:
    labels:
      easyhaproxy.http.host: admin.example.com
      easyhaproxy.http.plugins: ip_whitelist
      easyhaproxy.http.plugin.ip_whitelist.allowed_ips: 192.168.1.0/24,10.0.0.5
      easyhaproxy.http.plugin.ip_whitelist.status_code: 403
```

**HAProxy config generated:**
```
# IP Whitelist - Only allow specific IPs
acl whitelisted_ip src 192.168.1.0/24 10.0.0.5
http-request deny deny_status 403 if !whitelisted_ip
```

**Important:** This blocks ALL IPs except those in the whitelist. Make sure to include your own IP!

### JWT Validator Plugin (Domain)

Validates JWT (JSON Web Token) authentication tokens using HAProxy's built-in JWT functionality.

**Why use it:** Protect APIs and services with JWT authentication without needing application-level code.

**Configuration options:**
- `enabled` - Enable/disable plugin (default: `true`)
- `algorithm` - JWT signing algorithm (default: `RS256`)
- `issuer` - Expected JWT issuer (optional, set to `none`/`null` to skip validation)
- `audience` - Expected JWT audience (optional, set to `none`/`null` to skip validation)
- `pubkey_path` - Path to public key file (required if `pubkey` not provided)
- `pubkey` - Public key content as string (required if `pubkey_path` not provided)

**Enable via container label:**
```yaml
services:
  api:
    labels:
      easyhaproxy.http.host: api.example.com
      easyhaproxy.http.plugins: jwt_validator
      easyhaproxy.http.plugin.jwt_validator.algorithm: RS256
      easyhaproxy.http.plugin.jwt_validator.issuer: https://auth.example.com/
      easyhaproxy.http.plugin.jwt_validator.audience: https://api.example.com
      easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
    volumes:
      - ./pubkey.pem:/etc/haproxy/jwt_keys/api_pubkey.pem:ro
```

**Skip issuer/audience validation:**
```yaml
labels:
  easyhaproxy.http.plugin.jwt_validator.issuer: none
  easyhaproxy.http.plugin.jwt_validator.audience: none
  easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
```

**HAProxy config generated:**
```
# JWT Validator - Validate JWT tokens
http-request deny content-type 'text/html' string 'Missing Authorization HTTP header' unless { req.hdr(authorization) -m found }

# Extract JWT header and payload
http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg')
http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss')
http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud')
http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int')

# Validate JWT
http-request deny content-type 'text/html' string 'Unsupported JWT signing algorithm' unless { var(txn.alg) -m str RS256 }
http-request deny content-type 'text/html' string 'Invalid JWT issuer' unless { var(txn.iss) -m str https://auth.example.com/ }
http-request deny content-type 'text/html' string 'Invalid JWT audience' unless { var(txn.aud) -m str https://api.example.com }
http-request deny content-type 'text/html' string 'Invalid JWT signature' unless { http_auth_bearer,jwt_verify(txn.alg,"/etc/haproxy/jwt_keys/api_pubkey.pem") -m int 1 }

# Validate expiration
http-request set-var(txn.now) date()
http-request deny content-type 'text/html' string 'JWT has expired' if { var(txn.exp),sub(txn.now) -m int lt 0 }
```

**What it validates:**
- ✅ Authorization header presence
- ✅ JWT signing algorithm (RS256, RS512, etc.)
- ✅ JWT issuer (if configured)
- ✅ JWT audience (if configured)
- ✅ JWT signature using public key
- ✅ JWT expiration time

**Important:** Requires HAProxy 2.5+ with JWT support. Mount public key file as read-only volume.

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
    # Configure jwt_validator plugin
    easyhaproxy.plugin.jwt_validator.algorithm: "RS256"
    easyhaproxy.plugin.jwt_validator.issuer: "https://auth.example.com/"
    easyhaproxy.plugin.jwt_validator.audience: "https://api.example.com"
    easyhaproxy.plugin.jwt_validator.pubkey_path: "/etc/haproxy/jwt_keys/api_pubkey.pem"
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

Configure plugins globally in `/etc/haproxy/static/config.yaml`:

```yaml
plugins:
  # Global settings
  abort_on_error: false  # Log and continue on errors (recommended)

  # Enable global plugins
  enabled: [cleanup]

  # Configure individual plugins
  config:
    cloudflare:
      enabled: true
      ip_list_path: /etc/haproxy/cloudflare_ips.lst

    cleanup:
      enabled: true
      max_idle_time: 600

    deny_pages:
      enabled: false  # Disable globally, enable per-container via labels
```

### 4. Environment Variables

Configure plugins via environment variables:

```bash
# Global settings
EASYHAPROXY_PLUGINS_ENABLED=cleanup
EASYHAPROXY_PLUGINS_ABORT_ON_ERROR=false

# Plugin-specific configuration
EASYHAPROXY_PLUGIN_CLEANUP_ENABLED=true
EASYHAPROXY_PLUGIN_CLEANUP_MAX_IDLE_TIME=600
EASYHAPROXY_PLUGIN_CLOUDFLARE_IP_LIST_PATH=/etc/haproxy/cloudflare_ips.lst
```

**Variable format:**
- Enable plugins: `EASYHAPROXY_PLUGINS_ENABLED=plugin1,plugin2`
- Configure plugin: `EASYHAPROXY_PLUGIN_<PLUGIN_NAME>_<CONFIG_KEY>=value`

## Common Use Cases

### Protect API with JWT Authentication

Secure your API endpoints with JWT token validation:

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

To create your own plugins, see the [Plugin Developer Guide](plugin-development.md).

## Further Reading

- [Plugin Developer Guide](plugin-development.md) - Create custom plugins
- [Container Labels](container-labels.md) - Label configuration reference
- [Environment Variables](environment-variable.md) - Environment variable reference
- [Static Configuration](static.md) - YAML configuration reference
