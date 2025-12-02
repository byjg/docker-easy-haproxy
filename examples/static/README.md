# Static Configuration Example

This directory demonstrates EasyHAProxy using **static configuration** mode instead of dynamic service discovery.

## What is Static Mode?

Static mode uses a YAML configuration file (`config.yml`) to define HAProxy routing rules instead of discovering services automatically from Docker/Kubernetes/Swarm labels.

**Use cases:**
- Non-containerized backends
- Mixed environments (containers + VMs + bare metal)
- Fixed infrastructure where services don't change frequently
- Testing HAProxy configurations

---

## Files in This Example

- `conf/config.yml` - Static configuration defining hosts and routing
- `docker-compose.yml` - EasyHAProxy container mounting the config file
- `host1.local.pem` - Example SSL certificate

---

## Configuration Structure

### docker-compose.yml

```yaml
services:
  haproxy:
    image: byjg/easy-haproxy:4.6.0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./conf:/etc/haproxy/static          # Mount static config
      - ./host1.local.pem:/certs/haproxy/host1.local.pem
    environment:
      EASYHAPROXY_DISCOVER: static          # Use static mode
      EASYHAPROXY_SSL_MODE: "loose"
    ports:
      - "80:80"
      - "443:443"
      - "1936:1936"
```

### conf/config.yml

```yaml
stats:
  username: admin
  password: password
  port: 1936

customerrors: true

easymapping:
  # HTTP Port 80 - Redirects to HTTPS
  - port: 80
    redirect:
      host1.local: https://host1.local
      www.host1.local: https://host1.local

  # HTTPS Port 443
  - port: 443
    ssl: true
    hosts:
      host1.local:
        containers:
          - container:8080    # Backend container
```

---

## How It Works

### 1. Port Definitions

Each item in `easymapping` defines a listening port:

```yaml
easymapping:
  - port: 80              # Listen on port 80
    redirect: {...}       # Optional redirects

  - port: 443             # Listen on port 443
    ssl: true             # Enable SSL
    hosts: {...}          # Virtual hosts
```

### 2. Redirect Configuration

Redirect specific domains to different URLs:

```yaml
- port: 80
  redirect:
    host1.local: https://host1.local        # HTTP → HTTPS
    www.host1.local: https://host1.local    # www → non-www + HTTPS
    old.domain.com: https://new.domain.com  # Domain change
```

### 3. Virtual Hosts

Define hosts and their backend containers:

```yaml
- port: 443
  ssl: true
  hosts:
    host1.local:                      # Virtual host domain
      containers:
        - container:8080              # Backend: container_name:port
        - another_container:3000      # Multiple backends = load balancing

    host2.local:
      containers:
        - webserver:80
```

**Backend formats:**
- `container_name:port` - Docker container by name
- `ip_address:port` - Direct IP address
- `hostname:port` - Hostname resolution

### 4. SSL Configuration

```yaml
- port: 443
  ssl: true              # Enable SSL on this port
  hosts:
    secure.example.com:
      containers:
        - app:8080
```

SSL certificates must be placed in:
- `/certs/haproxy/<domain>.pem` inside container
- `./certs/<domain>.pem` on host (if volume mounted)

Certificate format: PEM file containing both certificate and private key.

### 5. Stats Interface

```yaml
stats:
  username: admin
  password: password
  port: 1936
```

Access at: `http://localhost:1936`

---

## Running the Example

### Prerequisites: Generate SSL Certificates

Before running the examples, you need to generate the required SSL certificates:

```bash
# From the repository root
./examples/generate-keys.sh
```

This script automatically generates:
- SSL certificates for host1.local and host2.local
- JWT keys for authentication examples
- All other .pem files needed for testing

### 1. Start the Example

```bash
cd examples/static
docker compose up -d
```

### 2. Create Backend Container

The static config references `container:8080`. Create a container with this name:

```bash
docker run -d --name container \
  -p 8080:8080 \
  byjg/static-httpserver
```

Or add to `docker-compose.yml`:

```yaml
services:
  # ... haproxy service ...

  container:
    image: byjg/static-httpserver
    ports:
      - "8080:8080"
```

### 3. Test

```bash
# Add to /etc/hosts:
# 127.0.0.1 host1.local www.host1.local

# Test HTTP redirect
curl -I http://host1.local
# Should return: HTTP/1.1 301 Moved Permanently
# Location: https://host1.local

# Test HTTPS
curl -k https://host1.local

# Access stats
open http://localhost:1936
# Username: admin
# Password: password
```

---

## Advanced Configuration

### Load Balancing Multiple Backends

```yaml
hosts:
  api.example.com:
    containers:
      - api_server_1:8080
      - api_server_2:8080
      - api_server_3:8080
```

Default algorithm: round-robin

### Custom Balance Algorithm

```yaml
hosts:
  api.example.com:
    balance: leastconn    # Use least connections instead of round-robin
    containers:
      - api_1:8080
      - api_2:8080
```

**Available algorithms:**
- `roundrobin` - Distribute evenly (default)
- `leastconn` - Send to server with fewest connections
- `source` - Same client IP always goes to same server

### External Backends (Non-Docker)

```yaml
hosts:
  legacy.example.com:
    containers:
      - 192.168.1.100:8080    # VM
      - 192.168.1.101:8080    # Another VM
      - database.local:5432    # Database server
```

### Health Checks

```yaml
hosts:
  webapp.example.com:
    containers:
      - server1:8080
      - server2:8080
    healthcheck:
      path: /health
      interval: 5s
```

### Multiple Domains, Same Backend

```yaml
hosts:
  example.com:
    containers:
      - webapp:8080
  www.example.com:
    containers:
      - webapp:8080      # Same backend
  app.example.com:
    containers:
      - webapp:8080      # Same backend
```

### Path-Based Routing

While static mode focuses on host-based routing, you can achieve path-based routing using redirects:

```yaml
- port: 80
  redirect:
    api.example.com/v1: https://api-v1.internal:8080
    api.example.com/v2: https://api-v2.internal:8080
```

Or use HAProxy ACLs via custom templates (advanced).

---

## Plugins with Static Configuration

Enable plugins globally or per-host in static mode:

### Global Plugin Configuration

```yaml
plugins:
  enabled: [cleanup]
  config:
    cleanup:
      max_idle_time: 600
```

### Per-Host Plugin Configuration (via env vars)

Since static mode doesn't support per-host plugin configuration directly, use environment variables for domain-specific plugins:

```yaml
environment:
  EASYHAPROXY_PLUGINS_ENABLED: cloudflare,deny_pages
  EASYHAPROXY_PLUGIN_CLOUDFLARE_IP_LIST_PATH: /etc/haproxy/cloudflare_ips.lst
  EASYHAPROXY_PLUGIN_DENY_PAGES_PATHS: /admin,/private
```

See [Using Plugins](../../docs/plugins.md) for more details.

---

## Comparison: Static vs. Dynamic Discovery

| Feature       | Static Mode                 | Docker/Swarm/K8s Mode                        |
|---------------|-----------------------------|----------------------------------------------|
| Configuration | YAML file                   | Container labels / Ingress annotations       |
| Backend types | Any (containers, VMs, IPs)  | Containers only                              |
| Updates       | Manual config edit + reload | Automatic discovery                          |
| Use case      | Fixed infrastructure        | Dynamic container environments               |
| Plugin config | Global via YAML/env         | Per-container/ingress via labels/annotations |

---

## Tips

1. **Reloading Configuration:**
   ```bash
   # EasyHAProxy watches config.yml for changes
   # Edit conf/config.yml, changes auto-reload

   # Or manually restart:
   docker compose restart haproxy
   ```

2. **Validate Configuration:**
   ```bash
   # Check HAProxy config is valid
   docker compose exec haproxy haproxy -c -f /etc/haproxy/haproxy.cfg
   ```

3. **View Generated Config:**
   ```bash
   docker compose exec haproxy cat /etc/haproxy/haproxy.cfg
   ```

4. **Debugging:**
   ```bash
   # Enable debug mode
   docker compose up
   # Watch logs in real-time
   ```

5. **SSL Certificate Management:**
   ```bash
   # Generate self-signed cert
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout host.key -out host.crt \
     -subj "/CN=host1.local"

   # Combine into PEM
   cat host.crt host.key > host1.local.pem
   ```

---

## Troubleshooting

### Backend Unreachable

**Error:** `503 Service Unavailable`

**Causes:**
- Backend container not running
- Wrong container name in config
- Wrong port number
- Network connectivity issues

**Debug:**
```bash
# Check backend container is running
docker ps | grep container_name

# Test backend directly
curl http://container_name:port

# Check HAProxy logs
docker compose logs haproxy
```

### Configuration Not Reloading

**Solution:**
```bash
# Restart HAProxy
docker compose restart haproxy

# Check file is mounted correctly
docker compose exec haproxy cat /etc/haproxy/static/config.yml
```

### SSL Certificate Not Found

**Error:** Certificate errors in logs

**Solution:**
```bash
# Verify certificate is mounted
docker compose exec haproxy ls -la /certs/haproxy/

# Check certificate format (must be PEM with cert + key)
openssl x509 -in host.pem -text -noout
openssl rsa -in host.pem -check
```

---

## Migration from Dynamic to Static

If you have Docker labels and want to convert to static config:

**Docker label:**
```yaml
labels:
  easyhaproxy.http.host: api.example.com
  easyhaproxy.http.port: 80
  easyhaproxy.http.localport: 8080
  easyhaproxy.http.redirect_ssl: true
```

**Static config equivalent:**
```yaml
easymapping:
  - port: 80
    redirect:
      api.example.com: https://api.example.com

  - port: 443
    ssl: true
    hosts:
      api.example.com:
        containers:
          - container_name:8080
```

---

## Further Reading

- [Static Configuration Guide](../../docs/static.md)
- [Environment Variables](../../docs/environment-variable.md)
- [Using Plugins](../../docs/plugins.md)
- [SSL Configuration](../../docs/ssl.md)
