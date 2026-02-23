---
sidebar_position: 4
sidebar_label: "Volumes"
---

# Volumes

:::info Volume Mapping
These volumes allow you to persist certificates, provide custom configurations, and extend EasyHAProxy functionality.
:::

## Directory Structure

:::info Base Path
All EasyHAProxy files are organized under `/etc/easyhaproxy/`. This can be customized using the `EASYHAPROXY_BASE_PATH` environment variable.
:::

```plaintext title="/etc/easyhaproxy/ Directory Tree"
/etc/easyhaproxy/
├── static/                             # 🔧 Runtime (static mode only)
│   └── config.yml                      # Static service configuration
│
├── haproxy/
│   ├── haproxy.cfg                     # 🔧 Runtime - Generated HAProxy config
│   ├── conf.d/                         # 📦 Base image
│   │   ├── README.md
│   │   └── *.cfg                       # User-provided custom configs
│   └── errors-custom/                  # 📦 Base image
│       ├── 400.http                    # Bad Request
│       ├── 403.http                    # Forbidden
│       ├── 408.http                    # Request Timeout
│       ├── 500.http                    # Internal Server Error
│       ├── 502.http                    # Bad Gateway
│       ├── 503.http                    # Service Unavailable
│       └── 504.http                    # Gateway Timeout
│
├── certs/
│   ├── live/                           # 🔧 Runtime (Certbot)
│   │   └── {domain}/
│   │       ├── cert.pem                # Certificate only
│   │       ├── chain.pem               # Certificate chain
│   │       ├── fullchain.pem           # cert.pem + chain.pem
│   │       ├── privkey.pem             # Private key
│   │       └── README
│   ├── archive/                        # 🔧 Runtime (Certbot)
│   │   └── {domain}/
│   │       ├── cert1.pem, cert2.pem... # Versioned certificates
│   │       └── privkey1.pem...         # Versioned keys
│   ├── work/                           # 🔧 Runtime (Certbot working dir)
│   ├── logs/                           # 🔧 Runtime (Certbot logs)
│   │   └── letsencrypt.log
│   ├── certbot/                        # 📦 Base image
│   │   ├── {domain}.pem                # 🔧 Runtime - Merged cert+key
│   │   └── placeholder.pem             # 📦 Base image - Placeholder cert
│   └── haproxy/                        # 📦 Base image
│       ├── {domain}.pem                # User-provided cert+key (PEM format)
│       └── placeholder.pem             # 📦 Base image - Placeholder cert
│
├── plugins/                            # Optional - Custom plugins
│   └── *.py                            # Python plugin files
│
├── jwt_keys/                           # Optional - JWT validation
│   └── *.pem                           # RSA public keys
│
├── cloudflare_ips.lst                  # Optional - Cloudflare plugin
│
└── www/                                # 📦 Base image - Stats dashboard
    └── dashboard.html                  # 📦 Base image - Stats dashboard UI
```

:::tip Legend
- **📦 Base image** - Included in the Docker image
- **🔧 Runtime** - Created/generated when EasyHAProxy runs
- **Optional** - Created only when specific features are used
:::

## Common Volume Mappings

The most commonly mapped volumes for persistence and customization:

| Volume                                    | Purpose                                                                                    | Required |
|-------------------------------------------|--------------------------------------------------------------------------------------------|----------|
| `/etc/easyhaproxy/static/`                | [Static configuration](../getting-started/static.md) - mount your `config.yml` here        | Optional |
| `/etc/easyhaproxy/certs/haproxy/`         | [SSL certificates](../guides/ssl.md) - user-provided certificates in PEM format            | Optional |
| `/etc/easyhaproxy/certs/certbot/`         | [ACME/Certbot certificates](../guides/acme.md) - auto-generated Let's Encrypt certificates | Optional |
| `/etc/easyhaproxy/certs/live/`            | Certbot live certificates - persist across container restarts                              | Optional |
| `/etc/easyhaproxy/haproxy/conf.d/`        | [Custom HAProxy config](other.md) - additional `.cfg` files to include                     | Optional |
| `/etc/easyhaproxy/haproxy/errors-custom/` | [Custom error pages](other.md) - custom HTTP error pages (400, 403, 500, etc.)             | Optional |
| `/etc/easyhaproxy/plugins/`               | [Custom plugins](../guides/plugins.md) - Python plugin files                               | Optional |
| `/etc/easyhaproxy/jwt_keys/`              | [JWT public keys](plugins/jwt-validator.md) - RSA public keys for JWT validation           | Optional |
| `/etc/easyhaproxy/www/`                   | Stats dashboard UI - served on port `stats_port + 10000` (default `11936`)                 | Optional |

## Directory Details

### Configuration Files

#### Static Configuration
```bash
/etc/easyhaproxy/static/config.yml
```
Static service configuration when not using service discovery (Docker/Kubernetes).

:::note
This directory only exists when `EASYHAPROXY_DISCOVER=static` is set.
:::

#### HAProxy Configuration
```bash
/etc/easyhaproxy/haproxy/haproxy.cfg
```
Auto-generated HAProxy configuration file.

:::warning Do Not Edit
This file is automatically generated by EasyHAProxy. Any manual changes will be overwritten.
:::

#### Custom Configuration Snippets
```bash
/etc/easyhaproxy/haproxy/conf.d/*.cfg
```
Place custom HAProxy configuration snippets here. These files are automatically included in the main configuration.

:::tip Example
```bash
# Mount your custom config
docker run -v ./my-custom.cfg:/etc/easyhaproxy/haproxy/conf.d/my-custom.cfg byjg/easy-haproxy
```
:::

### SSL/TLS Certificates

#### User-Provided Certificates
```bash
/etc/easyhaproxy/certs/haproxy/{domain}.pem
```
Place your SSL certificates here in PEM format (certificate + private key combined).

:::info PEM Format
```bash
cat domain.crt domain.key > /etc/easyhaproxy/certs/haproxy/domain.com.pem
```
:::

#### ACME/Let's Encrypt Certificates
```bash
/etc/easyhaproxy/certs/certbot/{domain}.pem  # Merged cert+key for HAProxy
/etc/easyhaproxy/certs/live/{domain}/        # Certbot live certificates (symlinks)
/etc/easyhaproxy/certs/archive/{domain}/     # Versioned certificate archive
```

EasyHAProxy automatically merges Certbot certificates from `/etc/easyhaproxy/certs/live/` into `/etc/easyhaproxy/certs/certbot/` for HAProxy consumption.

:::tip Persist Certbot Certificates
```yaml
volumes:
  - certbot-certs:/etc/easyhaproxy/certs/live
  - certbot-archive:/etc/easyhaproxy/certs/archive
```
:::

### Plugins & Extensions

#### Custom Plugins
```bash
/etc/easyhaproxy/plugins/*.py
```
Add custom Python plugins to extend EasyHAProxy functionality.

See [Plugin Development](../guides/plugin-development.md) for details.

#### JWT Public Keys
```bash
/etc/easyhaproxy/jwt_keys/*.pem
```
RSA public keys for [JWT token validation](plugins/jwt-validator.md).

#### Cloudflare IP Ranges
```bash
/etc/easyhaproxy/cloudflare_ips.lst
```
Cloudflare IP ranges for the [Cloudflare plugin](plugins/cloudflare.md) to restore real client IPs.

### Error Pages

```bash
/etc/easyhaproxy/haproxy/errors-custom/{code}.http
```

Custom HTTP error pages (400, 403, 408, 500, 502, 503, 504). Default error pages are included in the base image.

:::tip Customize Error Pages
```bash
# Mount your custom 503 error page
docker run -v ./custom-503.http:/etc/easyhaproxy/haproxy/errors-custom/503.http byjg/easy-haproxy
```
:::

----
[Open source ByJG](http://opensource.byjg.com)
