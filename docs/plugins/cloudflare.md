---
sidebar_position: 5
---

# Cloudflare Plugin

**Type:** Domain Plugin
**Runs:** Once for each discovered domain/host

## Overview

The Cloudflare plugin restores the original visitor IP address when requests come through Cloudflare's CDN. The plugin includes **built-in Cloudflare IP ranges** that are automatically written to the IP list file - no manual configuration required!

## Why Use It

Cloudflare replaces the visitor's IP with its own. This plugin restores the original IP from the `CF-Connecting-IP` header.

## Configuration Options

| Option            | Description                              | Default                           |
|-------------------|------------------------------------------|-----------------------------------|
| `enabled`         | Enable/disable plugin                    | `true`                            |
| `use_builtin_ips` | Use built-in Cloudflare IP ranges        | `true`                            |
| `ip_list_path`    | Path to Cloudflare IP list               | `/etc/haproxy/cloudflare_ips.lst` |

## Configuration Examples

### Docker/Docker Compose (Basic - Uses Built-in IPs)

```yaml
services:
  myapp:
    labels:
      easyhaproxy.http.host: example.com
      easyhaproxy.http.plugins: cloudflare
# Built-in Cloudflare IPs are automatically used - no additional configuration needed!
```

### Docker/Docker Compose (Custom IP List)

If you want to use your own IP list file instead of the built-in ranges:

```yaml
labels:
  easyhaproxy.http.plugins: cloudflare
  easyhaproxy.http.plugin.cloudflare.use_builtin_ips: false
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
      use_builtin_ips: true  # Uses built-in Cloudflare IPs (default)
```

## Generated HAProxy Configuration

```haproxy
# Cloudflare - Restore original visitor IP
acl from_cloudflare src -f /etc/haproxy/cloudflare_ips.lst
http-request set-header X-Forwarded-For %[req.hdr(CF-Connecting-IP)] if from_cloudflare
```

## Built-in Cloudflare IP Ranges

The plugin includes the current Cloudflare IP ranges (22 ranges total):

**IPv4 Ranges (15):**
- 173.245.48.0/20, 103.21.244.0/22, 103.22.200.0/22, 103.31.4.0/22
- 141.101.64.0/18, 108.162.192.0/18, 190.93.240.0/20, 188.114.96.0/20
- 197.234.240.0/22, 198.41.128.0/17, 162.158.0.0/15, 104.16.0.0/13
- 104.24.0.0/14, 172.64.0.0/13, 131.0.72.0/22

**IPv6 Ranges (7):**
- 2400:cb00::/32, 2606:4700::/32, 2803:f800::/32, 2405:b500::/32
- 2405:8100::/32, 2a06:98c0::/29, 2c0f:f248::/32

These ranges are automatically written to `/etc/haproxy/cloudflare_ips.lst` during each discovery cycle.

## Important Notes

- ✅ **No manual configuration required** - Built-in Cloudflare IPs are included!
- The plugin runs once per domain during the discovery cycle
- IP list file is automatically created and updated
- To update Cloudflare IPs in the future, simply update the plugin source code and rebuild

## Related Documentation

- [Plugin System Overview](../plugins.md)
- [Container Labels Reference](../container-labels.md)
