# Cloudflare Plugin

**Type:** Domain Plugin
**Runs:** Once for each discovered domain/host

## Overview

The Cloudflare plugin restores the original visitor IP address when requests come through Cloudflare's CDN.

## Why Use It

Cloudflare replaces the visitor's IP with its own. This plugin restores the original IP from the `CF-Connecting-IP` header.

## Configuration Options

| Option         | Description                | Default                           |
|----------------|----------------------------|-----------------------------------|
| `enabled`      | Enable/disable plugin      | `true`                            |
| `ip_list_path` | Path to Cloudflare IP list | `/etc/haproxy/cloudflare_ips.lst` |

## Configuration Examples

### Docker/Docker Compose (Basic)

```yaml
services:
  myapp:
    labels:
      easyhaproxy.http.host: example.com
      easyhaproxy.http.plugins: cloudflare
```

### Docker/Docker Compose (Custom IP List Path)

```yaml
labels:
  easyhaproxy.http.plugins: cloudflare
  easyhaproxy.http.plugin.cloudflare.ip_list_path: /custom/path/cf_ips.lst
```

### Kubernetes Annotations

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    easyhaproxy.plugins: "cloudflare"
    easyhaproxy.plugin.cloudflare.ip_list_path: "/etc/haproxy/cloudflare_ips.lst"
spec:
  rules:
    - host: example.com
      http:
        paths:
          - path: /
            backend:
              service:
                name: myapp
                port:
                  number: 80
```

### Static YAML Configuration

```yaml
# /etc/haproxy/static/config.yaml
plugins:
  config:
    cloudflare:
      enabled: true
      ip_list_path: /etc/haproxy/cloudflare_ips.lst
```

## Generated HAProxy Configuration

```haproxy
# Cloudflare - Restore original visitor IP
acl from_cloudflare src -f /etc/haproxy/cloudflare_ips.lst
http-request set-header X-Forwarded-For %[req.hdr(CF-Connecting-IP)] if from_cloudflare
```

## Important Notes

- **Required:** Download Cloudflare IP list from [Cloudflare documentation](https://support.cloudflare.com/hc/en-us/articles/200170786)
- The plugin runs once per domain during the discovery cycle
- Ensure the IP list file is mounted and accessible to HAProxy

## Related Documentation

- [Plugin System Overview](../plugins.md)
- [Container Labels Reference](../container-labels.md)
