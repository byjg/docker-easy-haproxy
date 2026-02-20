# Sample PHP Application for FastCGI Plugin

This directory contains a sample PHP application that demonstrates the FastCGI plugin functionality with EasyHAProxy.

## Files

### index.php
The main page that displays:
- PHP version and configuration
- FastCGI environment variables set by EasyHAProxy
- How the FastCGI plugin works
- Links to test pages

Access: `http://phpapp.local/`

### info.php
Standard `phpinfo()` page showing complete PHP configuration.

Access: `http://phpapp.local/info.php`

### test-path-info.php
Demonstrates PATH_INFO support for RESTful URL routing.

Examples:
- `http://phpapp.local/test-path-info.php/users`
- `http://phpapp.local/test-path-info.php/users/123`
- `http://phpapp.local/test-path-info.php/api/v1/products`

## FastCGI Environment Variables

The FastCGI plugin generates an `fcgi-app` configuration that defines these CGI parameters for HAProxy to use:

| Variable | Description | Example |
|----------|-------------|---------|
| `SCRIPT_FILENAME` | Full path to PHP script | `/var/www/html/index.php` |
| `DOCUMENT_ROOT` | Document root directory | `/var/www/html` |
| `SCRIPT_NAME` | Script path | `/index.php` |
| `REQUEST_URI` | Full request URI with query | `/index.php?page=1` |
| `QUERY_STRING` | Query string parameters | `page=1&limit=10` |
| `REQUEST_METHOD` | HTTP method | `GET`, `POST`, etc. |
| `CONTENT_TYPE` | Request content type | `application/json` |
| `CONTENT_LENGTH` | Request body length | `1024` |
| `SERVER_NAME` | Virtual host name | `phpapp.local` |
| `SERVER_PORT` | Server port | `80` or `443` |
| `HTTPS` | SSL status | `on` or `off` |
| `PATH_INFO` | Extra path info (optional) | `/users/123` |

## How It Works

1. **FastCGI plugin generates configuration** (at startup)
   - Creates an `fcgi-app` section with CGI parameter definitions
   - Includes `docroot`, `index`, and `path-info` settings
   - Adds `use-fcgi-app` directive to the backend

2. **Request arrives at HAProxy** (port 80)
   - URL: `http://phpapp.local/index.php`

3. **HAProxy uses the fcgi-app configuration**
   - Sets `SCRIPT_FILENAME` to `/var/www/html/index.php`
   - Sets `DOCUMENT_ROOT` to `/var/www/html`
   - Sets all other CGI variables based on the request
   - Handles directory requests (appends `index.php`)

4. **HAProxy forwards to PHP-FPM** via FastCGI protocol
   - Host: `php-fpm` (container name)
   - Port: `9000` (TCP) or Unix socket
   - Protocol: `fcgi`
   - Sends CGI parameters in FastCGI format

5. **PHP-FPM executes the script**
   - Reads the PHP file from `SCRIPT_FILENAME`
   - Processes the PHP code with CGI environment
   - Returns HTML/JSON response

6. **HAProxy sends response to client**

## Customizing

You can customize the FastCGI plugin configuration in `docker-compose-php-fpm.yml`:

```yaml
labels:
  # Change document root
  easyhaproxy.http.plugin.fastcgi.document_root: /var/www/public

  # Change default index file
  easyhaproxy.http.plugin.fastcgi.index_file: app.php

  # Disable PATH_INFO
  easyhaproxy.http.plugin.fastcgi.path_info: "false"

  # Add custom FastCGI parameters
  easyhaproxy.http.plugin.fastcgi.custom_params: '{"PHP_VALUE":"memory_limit=256M","APP_ENV":"production"}'
```

## Adding Your Own PHP Application

Replace the contents of this directory with your own PHP application:

```bash
# Remove sample files
rm -rf php-app/*

# Copy your PHP application
cp -r /path/to/your/app/* php-app/

# Restart the stack
docker compose -f docker-compose-php-fpm.yml restart
```

Make sure your application's entry point matches the `index_file` configuration (default: `index.php`).

## Troubleshooting

### "File not found" error

Check that:
1. The file exists in the `php-app/` directory
2. The `document_root` matches the container path (`/var/www/html`)
3. The volume mount is correct in docker-compose.yml

### PATH_INFO not working

Ensure `path_info` is enabled in the plugin configuration:
```yaml
easyhaproxy.http.plugin.fastcgi.path_info: "true"
```

### PHP-FPM connection error

Verify:
1. The `localport: 9000` is set correctly
2. The `proto: fcgi` parameter is set
3. Both containers are running and can communicate

View logs:
```bash
docker compose -f docker-compose-php-fpm.yml logs php-fpm
docker compose -f docker-compose-php-fpm.yml logs haproxy
```

Check connectivity:
```bash
docker compose -f docker-compose-php-fpm.yml exec haproxy ping php-fpm
```

## Learn More

- [FastCGI Plugin Documentation](../../../docs/reference/plugins/fastcgi.md)
- [Container Labels Reference](../../../docs/reference/container-labels.md)
- [HAProxy FastCGI Documentation](https://docs.haproxy.org/2.8/configuration.html#5.2-proto)
