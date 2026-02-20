---
sidebar_position: 5
sidebar_label: "Deny Pages"
---

# Deny Pages Plugin

**Type:** Domain Plugin
**Runs:** Once for each discovered domain/host

## Overview

The Deny Pages plugin blocks access to specific paths for a domain, returning a configurable HTTP status code.

## Why Use It

Protect admin panels, internal APIs, or debugging endpoints from public access.

## Configuration Options

| Option        | Description                            | Default    |
|---------------|----------------------------------------|------------|
| `enabled`     | Enable/disable plugin                  | `true`     |
| `paths`       | Comma-separated list of paths to block | (required) |
| `status_code` | HTTP status code to return             | `403`      |

## Configuration Examples

### Docker/Docker Compose (Basic)

```yaml
services:
  webapp:
    labels:
      easyhaproxy.http.host: example.com
      easyhaproxy.http.plugins: deny_pages
      easyhaproxy.http.plugin.deny_pages.paths: /admin,/private,/debug
      easyhaproxy.http.plugin.deny_pages.status_code: 404
```

### WordPress Protection

```yaml
labels:
  easyhaproxy.http.host: wordpress.example.com
  easyhaproxy.http.plugins: deny_pages
  easyhaproxy.http.plugin.deny_pages.paths: /wp-admin,/wp-login.php,/.env
  easyhaproxy.http.plugin.deny_pages.status_code: 404
```

### Kubernetes Annotations

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    easyhaproxy.plugins: "deny_pages"
    easyhaproxy.plugin.deny_pages.paths: "/admin,/private"
    easyhaproxy.plugin.deny_pages.status_code: "403"
spec:
  rules:
    - host: example.com
      http:
        paths:
          - path: /
            backend:
              service:
                name: webapp
                port:
                  number: 80
```

### Static YAML Configuration

```yaml
containers:
  "example.com:80":
    ip: ["webapp:80"]
    plugins: [deny_pages]
    plugin:
      deny_pages:
        paths: [/admin, /private, /debug]
        status_code: 403
```

### Multiple Plugins (with Cloudflare)

```yaml
labels:
  easyhaproxy.http.host: secure-app.com
  easyhaproxy.http.plugins: cloudflare,deny_pages
  easyhaproxy.http.plugin.deny_pages.paths: /admin,/config
  easyhaproxy.http.plugin.deny_pages.status_code: 403
```

### Environment Variables

| Environment Variable                        | Config Key    | Type    | Default | Description                            |
|---------------------------------------------|---------------|---------|---------|----------------------------------------|
| `EASYHAPROXY_PLUGIN_DENY_PAGES_ENABLED`     | `enabled`     | boolean | `true`  | Enable/disable plugin for all domains  |
| `EASYHAPROXY_PLUGIN_DENY_PAGES_PATHS`       | `paths`       | string  | -       | Comma-separated list of paths to block |
| `EASYHAPROXY_PLUGIN_DENY_PAGES_STATUS_CODE` | `status_code` | integer | `403`   | HTTP status code to return             |

## Generated HAProxy Configuration

```haproxy
# Deny Pages - Block specific paths
acl denied_path path_beg /admin /private /debug
http-request deny deny_status 404 if denied_path
```

## Important Notes

- The plugin runs once per domain during the discovery cycle
- Path matching uses `path_beg` (prefix matching), so `/admin` blocks `/admin/*` too
- Consider using `404` instead of `403` to hide the existence of blocked paths
- Works well in combination with other security plugins

## Related Documentation

- [Plugin System Overview](../../guides/plugins.md)
- [Container Labels Reference](../container-labels.md)
