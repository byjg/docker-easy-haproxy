---
sidebar_position: 17
---

# FastCGI Plugin

**Type:** Domain Plugin
**Runs:** Once for each discovered domain/host

## Overview

The FastCGI plugin configures HAProxy to communicate with PHP-FPM and other FastCGI applications. It automatically generates the necessary HAProxy `fcgi-app` configuration that defines CGI parameters for proper PHP-FPM communication.

## Why Use It

Automatically generates HAProxy `fcgi-app` configuration that defines required CGI parameters for PHP-FPM communication without manual HAProxy configuration.

## Configuration Options

| Option            | Description                             | Default                            |
|-------------------|-----------------------------------------|------------------------------------|
| `enabled`         | Enable/disable plugin                   | `true`                             |
| `document_root`   | Document root path                      | `/var/www/html`                    |
| `script_filename` | Custom pattern for SCRIPT_FILENAME      | `%[path]` (uses HAProxy's default) |
| `index_file`      | Default index file                      | `index.php`                        |
| `path_info`       | Enable PATH_INFO support                | `true`                             |
| `custom_params`   | Dictionary of custom FastCGI parameters | (optional)                         |

## Configuration Examples

### Docker/Docker Compose (TCP connection)

```yaml
services:
  php-fpm:
    image: php:8.2-fpm
    labels:
      easyhaproxy.http.host: phpapp.local
      easyhaproxy.http.port: 80
      easyhaproxy.http.localport: 9000
      easyhaproxy.http.proto: fcgi
      easyhaproxy.http.plugins: fastcgi
      easyhaproxy.http.plugin.fastcgi.document_root: /var/www/html
      easyhaproxy.http.plugin.fastcgi.index_file: index.php
    volumes:
      - ./app:/var/www/html
```

### Docker/Docker Compose (Unix socket)

```yaml
services:
  php-fpm:
    image: php:8.2-fpm
    labels:
      easyhaproxy.http.host: phpapp.local
      easyhaproxy.http.socket: /run/php/php-fpm.sock
      easyhaproxy.http.proto: fcgi
      easyhaproxy.http.plugins: fastcgi
      easyhaproxy.http.plugin.fastcgi.document_root: /var/www/html
      easyhaproxy.http.plugin.fastcgi.index_file: index.php
    volumes:
      - ./app:/var/www/html
      - /run/php:/run/php
```

### Custom Document Root and Index File

```yaml
labels:
  easyhaproxy.http.plugins: fastcgi
  easyhaproxy.http.plugin.fastcgi.document_root: /var/www/myapp/public
  easyhaproxy.http.plugin.fastcgi.index_file: app.php
  easyhaproxy.http.plugin.fastcgi.path_info: true
```

### Kubernetes Annotations

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    easyhaproxy.plugins: "fastcgi"
    easyhaproxy.plugin.fastcgi.document_root: "/var/www/html"
    easyhaproxy.plugin.fastcgi.index_file: "index.php"
spec:
  rules:
    - host: phpapp.example.com
      http:
        paths:
          - path: /
            backend:
              service:
                name: php-fpm
                port:
                  number: 9000
```

### Static YAML Configuration

```yaml
# /etc/haproxy/static/config.yaml
easymapping:
  - host: phpapp.local
    port: 80
    container: php-fpm:9000
    proto: fcgi
    plugins:
      - fastcgi
    plugin_config:
      fastcgi:
        document_root: /var/www/html
        index_file: index.php
        path_info: true
```

### Environment Variables

Configure FastCGI plugin defaults for all domains:

| Environment Variable                         | Config Key        | Type     | Default         | Description                           |
|----------------------------------------------|-------------------|----------|-----------------|---------------------------------------|
| `EASYHAPROXY_PLUGIN_FASTCGI_ENABLED`         | `enabled`         | boolean  | `true`          | Enable/disable plugin for all domains |
| `EASYHAPROXY_PLUGIN_FASTCGI_DOCUMENT_ROOT`   | `document_root`   | string   | `/var/www/html` | Document root path                    |
| `EASYHAPROXY_PLUGIN_FASTCGI_SCRIPT_FILENAME` | `script_filename` | string   | `%[path]`       | Custom pattern for SCRIPT_FILENAME    |
| `EASYHAPROXY_PLUGIN_FASTCGI_INDEX_FILE`      | `index_file`      | string   | `index.php`     | Default index file                    |
| `EASYHAPROXY_PLUGIN_FASTCGI_PATH_INFO`       | `path_info`       | boolean  | `true`          | Enable PATH_INFO support              |

**Note:** Environment variables set defaults for ALL domains. To configure per-domain, use container labels or Kubernetes annotations. Custom params (`custom_params`) cannot be configured via environment variables - use YAML or labels instead.

## Generated HAProxy Configuration

The plugin generates a top-level `fcgi-app` section and a `use-fcgi-app` directive in the backend:

```haproxy
# Top-level fcgi-app definition (added after defaults, before frontends/backends)
fcgi-app fcgi_phpapp_local
    docroot /var/www/html
    index index.php
    path-info ^(/.+\.php)(/.*)?$

# Backend configuration (added to the backend section)
backend srv_phpapp_local_80
    use-fcgi-app fcgi_phpapp_local
    # TCP connection:
    server srv-0 172.19.0.3:9000 proto fcgi
    # OR Unix socket:
    # server srv-0 /run/php/php-fpm.sock proto fcgi
```

## CGI Parameters

**Note:** HAProxy automatically sets standard CGI parameters based on the `fcgi-app` configuration when communicating with PHP-FPM via the FastCGI protocol.

The plugin configures:
- ✅ **SCRIPT_FILENAME** - Path to PHP script
- ✅ **DOCUMENT_ROOT** - Document root directory
- ✅ **SCRIPT_NAME** - Script name from URL
- ✅ **REQUEST_URI** - Full request URI with query string
- ✅ **QUERY_STRING** - URL query parameters
- ✅ **REQUEST_METHOD** - HTTP method (GET, POST, etc.)
- ✅ **CONTENT_TYPE & CONTENT_LENGTH** - Request body info
- ✅ **SERVER_NAME & SERVER_PORT** - Server details
- ✅ **HTTPS** - SSL/TLS status
- ✅ **PATH_INFO** - Path information (optional)

## Important Notes

- **Required:** Use this plugin together with `proto: fcgi` parameter for complete PHP-FPM support
- The plugin runs once per domain during the discovery cycle
- HAProxy handles the actual FastCGI protocol communication and CGI parameter transmission

## Related Documentation

- [Plugin System Overview](../plugins.md)
- [Container Labels Reference](../container-labels.md)
