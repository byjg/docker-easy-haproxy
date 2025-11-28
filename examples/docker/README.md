# Docker Compose Examples

This directory contains various Docker Compose examples demonstrating different EasyHAProxy configurations.

## Examples Overview

### 1. Basic Configuration (`docker-compose.yml`)

**What it demonstrates:**
- Basic SSL setup with two virtual hosts
- SSL redirect (HTTP → HTTPS)
- Custom SSL certificates (embedded and file-based)
- HAProxy stats interface

**Features:**
- `host1.local`: SSL certificate embedded as base64 in labels
- `host2.local`: SSL certificate loaded from file (`host2.local.pem`)
- Automatic HTTP to HTTPS redirect
- Stats available at port 1936

**Usage:**
```bash
docker compose up -d
```

**Test:**
```bash
# Test HTTPS
curl -k -H "Host: host1.local" https://127.0.0.1/
curl -k -H "Host: host2.local" https://127.0.0.1/

# Test HTTP redirect
curl -I -H "Host: host1.local" http://127.0.0.1
# Should return: HTTP/1.1 301 Moved Permanently

# View SSL certificate
openssl s_client -showcerts -connect 127.0.0.1:443 -servername host1.local
```

**Access stats:**
- URL: http://localhost:1936
- Username: `admin`
- Password: `password`

---

### 2. ACME/Let's Encrypt (`docker-compose-acme.yml`)

**What it demonstrates:**
- Automatic SSL certificate generation using Let's Encrypt
- HTTP-01 ACME challenge
- Certificate persistence

**Requirements:**
- Public IP address pointing to your machine
- Open ports 80 and 443 in firewall
- Valid domain name

**Configuration:**
```yaml
EASYHAPROXY_CERTBOT_EMAIL: user@example.com  # Change this!
easyhaproxy.http.certbot: true               # Enable certbot
```

**Usage:**
```bash
# Edit docker-compose-acme.yml and set:
# - EASYHAPROXY_CERTBOT_EMAIL to your email
# - easyhaproxy.http.host to your domain

docker compose -f docker-compose-acme.yml up -d
```

**Certificate storage:**
Certificates are persisted in `./certs/certbot/` to avoid re-challenges on restart.

---

### 3. Multiple Containers with Load Balancing (`docker-compose-multi-containers.yml`)

**What it demonstrates:**
- Multiple containers behind single domain
- Load balancing with round-robin
- Domain redirect functionality

**Features:**
- 2 replicas of nginx container
- Load balancing across replicas
- Domain redirect: `google.helloworld.com` → `www.google.com`

**Usage:**
```bash
docker compose -f docker-compose-multi-containers.yml up -d
```

**Test:**
```bash
# Test load balancing (hostname changes between containers)
curl -H "Host: www.helloworld.com" localhost:19901
# Response: f6d8d45b7411
curl -H "Host: www.helloworld.com" localhost:19901
# Response: 59b213cb8592

# Test redirect
curl -I -H "Host: google.helloworld.com" localhost:19901
# Should redirect to: www.google.com/
```

---

### 4. Changed Label Prefix (`docker-compose-changed-label.yml`)

**What it demonstrates:**
- Using custom label prefix instead of default `easyhaproxy`
- Useful for running multiple EasyHAProxy instances

**Configuration:**
```yaml
environment:
  EASYHAPROXY_LABEL_PREFIX: myproxy
```

**Container labels:**
```yaml
labels:
  myproxy.http.host: example.com
  myproxy.http.port: 80
```

---

### 5. Portainer Integration (`docker-compose-portainer.yml`)

**What it demonstrates:**
- Running Portainer behind EasyHAProxy
- Real-world application example

**Access Portainer:**
- URL: http://portainer.local (add to `/etc/hosts` or use real DNS)
- First time: Create admin user

---

### 6. Portainer + App Example (`docker-compose-portainer-app-example.yml`)

**What it demonstrates:**
- Multiple applications behind EasyHAProxy
- Portainer + custom app setup

---

## Plugin Examples

### JWT Validator Plugin

Protect your API with JWT token validation:

```yaml
version: "3"

services:
  haproxy:
    image: byjg/easy-haproxy:4.6.0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./jwt_pubkey.pem:/etc/haproxy/jwt_keys/api_pubkey.pem:ro
    environment:
      EASYHAPROXY_DISCOVER: docker
      HAPROXY_USERNAME: admin
      HAPROXY_PASSWORD: password
      HAPROXY_STATS_PORT: 1936
    ports:
      - "80:80/tcp"
      - "443:443/tcp"
      - "1936:1936/tcp"

  api:
    image: my-api:latest
    labels:
      easyhaproxy.http.host: api.example.com
      easyhaproxy.http.port: 80
      easyhaproxy.http.localport: 8080
      # Enable JWT validation
      easyhaproxy.http.plugins: jwt_validator
      easyhaproxy.http.plugin.jwt_validator.algorithm: RS256
      easyhaproxy.http.plugin.jwt_validator.issuer: https://auth.example.com/
      easyhaproxy.http.plugin.jwt_validator.audience: https://api.example.com
      easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
```

**What it validates:**
- Authorization header presence
- JWT signing algorithm
- JWT issuer and audience
- JWT signature using public key
- JWT expiration time

**Test:**
```bash
# Without token - should fail
curl http://api.example.com/endpoint
# Response: Missing Authorization HTTP header

# With valid JWT token
curl -H "Authorization: Bearer eyJhbGc..." http://api.example.com/endpoint
# Response: Success
```

**Generate test public key:**
```bash
# Generate private key
openssl genrsa -out jwt_private.pem 2048

# Extract public key
openssl rsa -in jwt_private.pem -pubout -out jwt_pubkey.pem
```

---

### Cloudflare IP Restoration Plugin

Restore original visitor IPs when using Cloudflare CDN:

```yaml
version: "3"

services:
  haproxy:
    image: byjg/easy-haproxy:4.6.0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./cloudflare_ips.lst:/etc/haproxy/cloudflare_ips.lst:ro
    environment:
      EASYHAPROXY_DISCOVER: docker
    ports:
      - "80:80/tcp"
      - "443:443/tcp"

  webapp:
    image: my-webapp:latest
    labels:
      easyhaproxy.http.host: myapp.com
      easyhaproxy.http.port: 80
      easyhaproxy.http.localport: 3000
      # Enable Cloudflare plugin
      easyhaproxy.http.plugins: cloudflare
```

**Setup Cloudflare IP list:**
```bash
# Download Cloudflare IP ranges
curl https://www.cloudflare.com/ips-v4 > cloudflare_ips.lst
curl https://www.cloudflare.com/ips-v6 >> cloudflare_ips.lst
```

**What it does:**
- Detects requests from Cloudflare IPs
- Restores original visitor IP from `CF-Connecting-IP` header
- Your application logs show real visitor IPs, not Cloudflare IPs

---

### IP Whitelist Plugin

Restrict access to specific IP addresses:

```yaml
version: "3"

services:
  haproxy:
    image: byjg/easy-haproxy:4.6.0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      EASYHAPROXY_DISCOVER: docker
    ports:
      - "80:80/tcp"

  admin_panel:
    image: admin-panel:latest
    labels:
      easyhaproxy.http.host: admin.example.com
      easyhaproxy.http.port: 80
      easyhaproxy.http.localport: 8080
      # Enable IP whitelist
      easyhaproxy.http.plugins: ip_whitelist
      easyhaproxy.http.plugin.ip_whitelist.allowed_ips: 192.168.1.0/24,10.0.0.5
      easyhaproxy.http.plugin.ip_whitelist.status_code: 403
```

**Allowed IP formats:**
- Single IP: `10.0.0.5`
- CIDR range: `192.168.1.0/24`
- Multiple (comma-separated): `192.168.1.0/24,10.0.0.5,172.16.0.100`

**Test:**
```bash
# From allowed IP
curl http://admin.example.com
# Response: Success

# From blocked IP
curl http://admin.example.com
# Response: HTTP 403 Forbidden
```

---

### Multiple Plugins Combined

Combine multiple plugins for enhanced security:

```yaml
version: "3"

services:
  haproxy:
    image: byjg/easy-haproxy:4.6.0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./cloudflare_ips.lst:/etc/haproxy/cloudflare_ips.lst:ro
    environment:
      EASYHAPROXY_DISCOVER: docker
    ports:
      - "80:80/tcp"
      - "443:443/tcp"

  webapp:
    image: webapp:latest
    labels:
      easyhaproxy.http.host: myapp.example.com
      easyhaproxy.http.port: 80
      easyhaproxy.http.localport: 8080
      # Enable multiple plugins
      easyhaproxy.http.plugins: cloudflare,deny_pages
      # Block specific paths
      easyhaproxy.http.plugin.deny_pages.paths: /admin,/wp-admin,/wp-login.php,/.env
      easyhaproxy.http.plugin.deny_pages.status_code: 404

  api:
    image: api:latest
    labels:
      easyhaproxy.http.host: api.example.com
      easyhaproxy.http.port: 80
      easyhaproxy.http.localport: 3000
      # Combine JWT + IP whitelist + path blocking
      easyhaproxy.http.plugins: jwt_validator,ip_whitelist,deny_pages
      easyhaproxy.http.plugin.jwt_validator.algorithm: RS256
      easyhaproxy.http.plugin.jwt_validator.issuer: https://auth.example.com/
      easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api.pem
      easyhaproxy.http.plugin.ip_whitelist.allowed_ips: 192.168.0.0/16,10.0.0.0/8
      easyhaproxy.http.plugin.deny_pages.paths: /internal,/debug
```

**Plugin execution order:**
1. IP Whitelist (blocks non-whitelisted IPs)
2. Deny Pages (blocks specific paths)
3. JWT Validator (validates authentication)

---

## Common Configuration Options

### Environment Variables (HAProxy Container)

| Variable                    | Description               | Default  |
|-----------------------------|---------------------------|----------|
| `EASYHAPROXY_DISCOVER`      | Discovery mode            | `docker` |
| `EASYHAPROXY_SSL_MODE`      | SSL mode (loose/strict)   | `strict` |
| `EASYHAPROXY_CERTBOT_EMAIL` | Email for Let's Encrypt   | -        |
| `HAPROXY_CUSTOMERRORS`      | Enable custom error pages | `false`  |
| `HAPROXY_USERNAME`          | Stats username            | -        |
| `HAPROXY_PASSWORD`          | Stats password            | -        |
| `HAPROXY_STATS_PORT`        | Stats port                | `1936`   |

### Container Labels

| Label                           | Description          | Example       |
|---------------------------------|----------------------|---------------|
| `easyhaproxy.http.host`         | Virtual host domain  | `example.com` |
| `easyhaproxy.http.port`         | External port        | `80`          |
| `easyhaproxy.http.localport`    | Container port       | `8080`        |
| `easyhaproxy.http.redirect_ssl` | Force HTTPS redirect | `true`        |
| `easyhaproxy.http.certbot`      | Enable Let's Encrypt | `true`        |
| `easyhaproxy.https.ssl`         | Enable SSL           | `true`        |
| `easyhaproxy.https.sslcert`     | Base64 SSL cert      | `LS0t...`     |

For complete documentation, see [Container Labels](../../docs/container-labels.md).

## Tips

1. **Local Testing with Fake Domains:**
   Add entries to `/etc/hosts`:
   ```
   127.0.0.1 host1.local host2.local portainer.local
   ```

2. **Viewing Logs:**
   ```bash
   docker compose logs -f haproxy
   ```

3. **Reloading Configuration:**
   EasyHAProxy automatically detects changes. Watch logs for reload events.

4. **Generating Test SSL Certificates:**
   ```bash
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout host.key -out host.crt \
     -subj "/CN=host1.local"
   cat host.crt host.key > host.pem
   ```

5. **Base64 Encoding SSL Certificate:**
   ```bash
   base64 -w 0 host.pem
   ```

## Troubleshooting

**Issue:** Container not detected
- Check labels are correct (prefix, syntax)
- Verify Docker socket is mounted
- Check logs: `docker compose logs haproxy`

**Issue:** SSL not working
- Verify certificate format (cert + key in same PEM file)
- Check certificate matches domain
- Verify SSL mode (`loose` vs `strict`)

**Issue:** Let's Encrypt fails
- Ensure ports 80/443 are publicly accessible
- Verify domain DNS points to your IP
- Check certbot logs in HAProxy container

## Further Reading

- [Docker Configuration Guide](../../docs/docker.md)
- [Container Labels Reference](../../docs/container-labels.md)
- [ACME/Let's Encrypt Guide](../../docs/acme.md)
- [Environment Variables](../../docs/environment-variable.md)
