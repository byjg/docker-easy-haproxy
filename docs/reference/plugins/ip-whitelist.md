---
sidebar_position: 4
sidebar_label: "IP Whitelist"
---

# IP Whitelist Plugin

**Type:** Domain Plugin
**Runs:** Once for each discovered domain/host

## Overview

The IP Whitelist plugin restricts access to a domain to only specific IP addresses or CIDR ranges.

## Why Use It

Restrict access to internal tools, admin panels, or staging environments to only trusted IP addresses.

## Configuration Options

| Option        | Description                                      | Default    |
|---------------|--------------------------------------------------|------------|
| `enabled`     | Enable/disable plugin                            | `true`     |
| `allowed_ips` | Comma-separated list of IPs/CIDR ranges to allow | (required) |
| `status_code` | HTTP status code to return for blocked IPs       | `403`      |

## Configuration Examples

### Docker/Docker Compose (Basic)

```yaml
services:
  admin:
    labels:
      easyhaproxy.http.host: admin.example.com
      easyhaproxy.http.plugins: ip_whitelist
      easyhaproxy.http.plugin.ip_whitelist.allowed_ips: 192.168.1.0/24,10.0.0.5
      easyhaproxy.http.plugin.ip_whitelist.status_code: 403
```

### Office Network Access

```yaml
labels:
  easyhaproxy.http.host: admin.example.com
  easyhaproxy.http.plugins: ip_whitelist
  easyhaproxy.http.plugin.ip_whitelist.allowed_ips: 203.0.113.0/24,198.51.100.42
```

### Kubernetes Annotations

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    easyhaproxy.plugins: "ip_whitelist"
    easyhaproxy.plugin.ip_whitelist.allowed_ips: "192.168.1.0/24,10.0.0.5"
    easyhaproxy.plugin.ip_whitelist.status_code: "403"
spec:
  rules:
    - host: admin.example.com
      http:
        paths:
          - path: /
            backend:
              service:
                name: admin-panel
                port:
                  number: 80
```

### Static YAML Configuration

```yaml
easymapping:
  - host: admin.example.com
    port: 443
    container: admin-panel:443
    plugins:
      - ip_whitelist
    plugin_config:
      ip_whitelist:
        allowed_ips: 192.168.1.0/24,10.0.0.5
        status_code: 403
```

### Environment Variables

| Environment Variable                          | Config Key    | Type     | Default | Description                                      |
|-----------------------------------------------|---------------|----------|---------|--------------------------------------------------|
| `EASYHAPROXY_PLUGIN_IP_WHITELIST_ENABLED`     | `enabled`     | boolean  | `true`  | Enable/disable plugin for all domains            |
| `EASYHAPROXY_PLUGIN_IP_WHITELIST_ALLOWED_IPS` | `allowed_ips` | string   | -       | Comma-separated list of IPs/CIDR ranges to allow |
| `EASYHAPROXY_PLUGIN_IP_WHITELIST_STATUS_CODE` | `status_code` | integer  | `403`   | HTTP status code to return for blocked IPs       |

## Generated HAProxy Configuration

```haproxy
# IP Whitelist - Only allow specific IPs
acl whitelisted_ip src 192.168.1.0/24 10.0.0.5
http-request deny deny_status 403 if !whitelisted_ip
```

## IP Address Formats

The plugin supports:
- **Single IPs:** `10.0.0.5`, `203.0.113.42`
- **CIDR ranges:** `192.168.1.0/24`, `10.0.0.0/8`
- **Multiple entries:** Comma-separated list of IPs and/or CIDR ranges

## Important Notes

- **Warning:** This blocks ALL IPs except those in the whitelist. Make sure to include your own IP!
- The plugin runs once per domain during the discovery cycle
- Test thoroughly before deploying to production
- Consider using VPN CIDR ranges for remote access

## Related Documentation

- [Plugin System Overview](../../guides/plugins.md)
- [Container Labels Reference](../container-labels.md)
