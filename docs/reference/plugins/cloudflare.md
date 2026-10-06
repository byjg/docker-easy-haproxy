---
sidebar_position: 3
sidebar_label: "Cloudflare"
---

# Cloudflare Plugin

**Type:** Domain Plugin
**Runs:** Once for each discovered domain/host

## Overview

The Cloudflare plugin restores the original visitor IP address when requests come through Cloudflare's CDN. The plugin includes **built-in Cloudflare IP ranges** that are automatically written to the IP list file - no manual configuration required!

## Why Use It

Cloudflare replaces the visitor's IP with its own. This plugin restores the original IP from the `CF-Connecting-IP` header.

The header is only trusted when the connection comes from an IP in the trusted list. By default, this is the list of Cloudflare edge IPs.
If you use a [Cloudflare Tunnel](#cloudflare-tunnel), the connection comes from `cloudflared` instead, and you must provide its IPs.

## Configuration Options

| Option              | Description                                                               | Default                               |
|---------------------|---------------------------------------------------------------------------|---------------------------------------|
| `enabled`           | Enable/disable plugin                                                     | `true`                                |
| `use_builtin_ips`   | Use built-in Cloudflare IP ranges                                         | `true`                                |
| `ip_list`           | Base64-encoded list of trusted IPs/CIDRs (one per line). Takes precedence over `use_builtin_ips` | *empty*  |
| `ip_list_path`      | Path to the trusted IP list file                                          | `/etc/easyhaproxy/cloudflare_ips.lst` |
| `update_log_format` | Change the HAProxy log format to show the real visitor IP                 | `true`                                |

The IP list file is written from `ip_list` (if set) or from the built-in IPs (if `use_builtin_ips` is `true`).
If neither is set, the plugin uses the existing file at `ip_list_path`.

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
plugins:
  config:
    cloudflare:
      enabled: true
      use_builtin_ips: true  # Uses built-in Cloudflare IPs (default)
```

### Environment Variables

| Environment Variable                              | Config Key          | Type    | Default                               | Description                                   |
|---------------------------------------------------|---------------------|---------|---------------------------------------|-----------------------------------------------|
| `EASYHAPROXY_PLUGIN_CLOUDFLARE_ENABLED`           | `enabled`           | boolean | `true`                                | Enable/disable plugin for all domains         |
| `EASYHAPROXY_PLUGIN_CLOUDFLARE_USE_BUILTIN_IPS`   | `use_builtin_ips`   | boolean | `true`                                | Use built-in Cloudflare IP ranges             |
| `EASYHAPROXY_PLUGIN_CLOUDFLARE_IP_LIST`           | `ip_list`           | string  | *empty*                               | Base64-encoded list of trusted IPs/CIDRs      |
| `EASYHAPROXY_PLUGIN_CLOUDFLARE_IP_LIST_PATH`      | `ip_list_path`      | string  | `/etc/easyhaproxy/cloudflare_ips.lst` | Path to the trusted IP list file              |
| `EASYHAPROXY_PLUGIN_CLOUDFLARE_UPDATE_LOG_FORMAT` | `update_log_format` | boolean | `true`                                | Show the real visitor IP in the HAProxy log   |

## Cloudflare Tunnel

With a Cloudflare Tunnel, HAProxy receives the connection from the `cloudflared` process, not from a Cloudflare edge IP.
The built-in list doesn't match, so the plugin does nothing. `cloudflared` still sends the `CF-Connecting-IP` header.

Disable the built-in IPs and trust the IPs `cloudflared` connects from. Check the HAProxy log to find them:
it's the IP after the `/` (or the first field, if the plugin is not enabled yet).

```bash
# One IP/CIDR per line, base64-encoded
printf '10.168.0.0/16\n10.42.0.0/16\n' | base64 -w0
```

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    easyhaproxy.plugins: "cloudflare"
    easyhaproxy.plugin.cloudflare.use_builtin_ips: "false"
    easyhaproxy.plugin.cloudflare.ip_list: "MTAuMTY4LjAuMC8xNgoxMC40Mi4wLjAvMTYK"
```

:::warning Trust only what you need
Any client connecting from a trusted IP can set `CF-Connecting-IP` to any value.
Keep the list as small as possible, e.g. only the `cloudflared` host, and make sure HAProxy can't be reached from other hosts in that range.
On Kubernetes, if `cloudflared` runs on the node, the connection comes from the node's CNI gateway (e.g. `10.42.0.1` on k3s).
Trusting the whole pod network (e.g. `10.42.0.0/16`) means trusting every pod in the cluster.
:::

## Generated HAProxy Configuration

Backend section:

```haproxy
# Cloudflare - Restore original visitor IP
acl from_cloudflare src -f /etc/easyhaproxy/cloudflare_ips.lst
http-request set-var(txn.real_ip) req.hdr(CF-Connecting-IP) if from_cloudflare
http-request set-header X-Forwarded-For %[var(txn.real_ip)] if from_cloudflare
```

With `option forwardfor`, HAProxy also appends the connection IP, so the backend receives
`X-Forwarded-For: <visitor_ip>, <connection_ip>`. Use the first value, or read the `CF-Connecting-IP` header directly.

## Log Format

When `update_log_format` is `true` (default), the plugin adds this to the `defaults` section:

```haproxy
log-format "%[var(txn.real_ip,-)]/%ci:%cp [%tr] %ft %b/%s %TR/%Tw/%Tc/%Tr/%Ta %ST %B %CC %CS %tsc %ac/%fc/%bc/%sc/%rc %sq/%bq %hr %hs %{+Q}r"
```

The line starts with `real_ip/connection_ip:port`, replacing the `client_ip:port` of the standard HAProxy log:

| Field           | Example       | Description                                                                                       |
|-----------------|---------------|---------------------------------------------------------------------------------------------------|
| `real_ip`       | `203.0.113.7` | Visitor IP from `CF-Connecting-IP`. `-` if not from a trusted IP, or the domain doesn't use the plugin |
| `connection_ip` | `10.42.0.1`   | IP connected to HAProxy: a Cloudflare edge IP, or `cloudflared` when using a [tunnel](#cloudflare-tunnel) |
| `port`          | `50126`       | Source port of that connection                                                                    |

The rest is the standard HAProxy HTTP log format (timestamp, frontend, backend/server, timings, status, bytes, termination state, ...).
See the [HAProxy HTTP log format](https://docs.haproxy.org/3.3/configuration.html#8.2.3) for each field.

Examples:

```text
203.0.113.7/10.42.0.1:50126 [04/Oct/2026:16:18:30.776] http_in_80 srv_example_com_80/srv-0 0/0/0/4/4 200 184 - - ---- 12/12/0/0/0 0/0 "GET / HTTP/1.1"
-/10.168.30.10:54626 [04/Oct/2026:16:18:31.249] http_in_80 srv_other_com_80/srv-0 0/0/0/9/9 200 394 - - ---- 27/27/17/17/0 0/0 "POST /api HTTP/1.1"
```

## Important Notes

- ✅ **No manual configuration required** - Built-in Cloudflare IPs are included!
- The plugin runs once per domain during the discovery cycle
- IP list file is automatically created and updated
- **The IP list file is shared.** All domains with the same `ip_list_path` write to the same file, and the last one processed wins.
  Use the same `ip_list` on all of them, or a different `ip_list_path` for each.
- **The log format is global.** It is set in the `defaults` section, so it changes the log line of **all** domains,
  even if only one uses the plugin. Set `update_log_format: false` to keep the standard HAProxy log format.

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

## Related Documentation

- [Plugin System Overview](../../guides/plugins.md)
- [Container Labels Reference](../container-labels.md)
