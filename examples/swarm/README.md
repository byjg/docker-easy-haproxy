# Docker Swarm Examples

This directory contains Docker Swarm stack examples demonstrating EasyHAProxy in a Swarm cluster environment.

## What is Docker Swarm Mode?

Docker Swarm mode enables:
- **Service orchestration** across multiple nodes
- **Service scaling** with replicas
- **Load balancing** across service replicas
- **Rolling updates** with zero downtime
- **Service discovery** via overlay networks

EasyHAProxy automatically discovers Swarm services and routes traffic based on service labels.

---

## Prerequisites

### 1. Initialize Docker Swarm

```bash
# On manager node
docker swarm init

# On worker nodes (use token from swarm init output)
docker swarm join --token <token> <manager-ip>:2377
```

### 2. Create Overlay Network

```bash
# Create attachable overlay network for EasyHAProxy
docker network create --driver overlay --attachable easyhaproxy
```

**Why attachable?** Allows both swarm services and standalone containers to connect.

---

## Files in This Directory

- `easyhaproxy.yml` - EasyHAProxy service stack
- `services.yml` - Example application services
- `portainer.yml` - Portainer management interface
- `certs/` - Directory for SSL certificates

---

## Quick Start

### 1. Deploy EasyHAProxy

```bash
cd examples/swarm

# Edit easyhaproxy.yml and change:
# EASYHAPROXY_CERTBOT_EMAIL: your-email@example.com

# Deploy stack
docker stack deploy -c easyhaproxy.yml easyhaproxy
```

**What this creates:**
- EasyHAProxy service with 1 replica
- Exposed ports: 80, 443, 1936
- Mounts Docker socket for service discovery
- Mounts volume for certbot certificates

### 2. Deploy Example Services

```bash
docker stack deploy -c services.yml myapp
```

### 3. (Optional) Deploy Portainer

```bash
docker stack deploy -c portainer.yml portainer
```

---

## Example Files Explained

### easyhaproxy.yml

```yaml
version: "3"

services:
  haproxy:
    image: byjg/easy-haproxy:4.6.0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # Service discovery
      - ./certs:/certs/haproxy                     # SSL certificates
      - certs_certbot:/certs/certbot               # Let's Encrypt certs
    deploy:
      replicas: 1                                   # Single instance
    environment:
      EASYHAPROXY_DISCOVER: swarm                  # Swarm mode!
      EASYHAPROXY_SSL_MODE: "loose"
      EASYHAPROXY_CERTBOT_EMAIL: changeme@example.org  # Change this!
      HAPROXY_CUSTOMERRORS: "true"
      HAPROXY_USERNAME: admin
      HAPROXY_PASSWORD: password
      HAPROXY_STATS_PORT: 1936
    ports:
      - "80:80/tcp"
      - "443:443/tcp"
      - "1936:1936/tcp"
    networks:
      - easyhaproxy                                # Overlay network

networks:
  easyhaproxy:
    external: true                                 # Created separately

volumes:
  certs_certbot:                                   # Persistent certbot data
```

**Key differences from Docker Compose mode:**
- `EASYHAPROXY_DISCOVER: swarm` - Discovery mode
- `deploy.replicas: 1` - Swarm deployment config
- External overlay network

---

## Service Labels in Swarm

Service labels are similar to container labels but applied to **services**, not containers.

### Basic Service Example

```yaml
version: "3"

services:
  webapp:
    image: nginx:alpine
    deploy:
      replicas: 3           # 3 instances for load balancing
      labels:
        # Service labels (not container labels!)
        easyhaproxy.http.host: "webapp.example.com"
        easyhaproxy.http.port: "80"
        easyhaproxy.http.localport: "80"
    networks:
      - easyhaproxy
```

**Important:** Use `deploy.labels`, NOT top-level `labels`!

```yaml
# ✅ CORRECT - Service labels
deploy:
  labels:
    easyhaproxy.http.host: example.com

# ❌ WRONG - Container labels (ignored in Swarm)
labels:
  easyhaproxy.http.host: example.com
```

---

## Common Use Cases

### Use Case 1: Simple HTTP Service

```yaml
version: "3"

services:
  myapp:
    image: my-app:latest
    deploy:
      replicas: 3
      labels:
        easyhaproxy.http.host: "myapp.example.com"
        easyhaproxy.http.port: "80"
        easyhaproxy.http.localport: "3000"
    networks:
      - easyhaproxy

networks:
  easyhaproxy:
    external: true
```

Deploy:
```bash
docker stack deploy -c myapp.yml myapp
```

### Use Case 2: HTTPS with Let's Encrypt

```yaml
version: "3"

services:
  secure-app:
    image: secure-app:latest
    deploy:
      replicas: 2
      labels:
        easyhaproxy.http.host: "secure.example.com"
        easyhaproxy.http.port: "80"
        easyhaproxy.http.localport: "8080"
        easyhaproxy.http.certbot: "true"
        easyhaproxy.http.redirect_ssl: "true"
    networks:
      - easyhaproxy

networks:
  easyhaproxy:
    external: true
```

**Requirements:**
- Public IP with DNS pointing to swarm
- Ports 80/443 open
- Certbot email configured in `easyhaproxy.yml`

### Use Case 3: Multiple Domains, One Service

```yaml
services:
  webapp:
    image: webapp:latest
    deploy:
      replicas: 4
      labels:
        # Primary domain
        easyhaproxy.http.host: "example.com"
        easyhaproxy.http.port: "80"
        easyhaproxy.http.localport: "8080"

        # Additional domain (www)
        easyhaproxy.http2.host: "www.example.com"
        easyhaproxy.http2.port: "80"
        easyhaproxy.http2.localport: "8080"

        # API subdomain
        easyhaproxy.api.host: "api.example.com"
        easyhaproxy.api.port: "80"
        easyhaproxy.api.localport: "8080"
    networks:
      - easyhaproxy
```

### Use Case 4: Service with Plugins

```yaml
services:
  api:
    image: api-server:latest
    deploy:
      replicas: 3
      labels:
        easyhaproxy.http.host: "api.example.com"
        easyhaproxy.http.port: "80"
        easyhaproxy.http.localport: "8080"
        # Enable plugins
        easyhaproxy.http.plugins: "jwt_validator,deny_pages"
        # Configure JWT validator
        easyhaproxy.http.plugin.jwt_validator.algorithm: "RS256"
        easyhaproxy.http.plugin.jwt_validator.issuer: "https://auth.example.com/"
        easyhaproxy.http.plugin.jwt_validator.pubkey_path: "/etc/haproxy/jwt_keys/api.pem"
        # Configure deny_pages
        easyhaproxy.http.plugin.deny_pages.paths: "/admin,/private"
        easyhaproxy.http.plugin.deny_pages.status_code: "403"
    networks:
      - easyhaproxy
```

### Use Case 5: Multiple Services with Load Balancing

```yaml
version: "3"

services:
  frontend:
    image: frontend-app:latest
    deploy:
      replicas: 2
      labels:
        easyhaproxy.http.host: "example.com"
        easyhaproxy.http.port: "80"
        easyhaproxy.http.localport: "3000"
    networks:
      - easyhaproxy

  api:
    image: api-server:latest
    deploy:
      replicas: 5           # More replicas for API
      labels:
        easyhaproxy.http.host: "api.example.com"
        easyhaproxy.http.port: "80"
        easyhaproxy.http.localport: "8080"
    networks:
      - easyhaproxy

  admin:
    image: admin-panel:latest
    deploy:
      replicas: 1
      labels:
        easyhaproxy.http.host: "admin.example.com"
        easyhaproxy.http.port: "80"
        easyhaproxy.http.localport: "4000"
        # Restrict access
        easyhaproxy.http.plugins: "ip_whitelist"
        easyhaproxy.http.plugin.ip_whitelist.allowed_ips: "192.168.1.0/24"
    networks:
      - easyhaproxy

networks:
  easyhaproxy:
    external: true
```

---

## Scaling Services

Scale services dynamically:

```bash
# Scale up
docker service scale myapp_webapp=10

# Scale down
docker service scale myapp_webapp=2

# Check replicas
docker service ls
```

EasyHAProxy automatically detects all replicas and load balances across them.

---

## Rolling Updates

Update services with zero downtime:

```bash
# Update service image
docker service update --image webapp:v2 myapp_webapp

# Update with custom settings
docker service update \
  --image webapp:v2 \
  --update-parallelism 2 \
  --update-delay 10s \
  myapp_webapp
```

EasyHAProxy continues routing to healthy containers during rollout.

---

## Management Commands

### View Stacks

```bash
docker stack ls
```

### View Services in Stack

```bash
docker stack services myapp
```

### View Service Details

```bash
docker service inspect myapp_webapp
```

### View Service Logs

```bash
docker service logs -f myapp_webapp
```

### Update Service Labels

```bash
docker service update \
  --label-add easyhaproxy.http.certbot=true \
  myapp_webapp
```

### Remove Stack

```bash
docker stack rm myapp
```

---

## SSL Certificates in Swarm

### Option 1: Let's Encrypt (Recommended)

Configure in `easyhaproxy.yml`:
```yaml
environment:
  EASYHAPROXY_CERTBOT_EMAIL: your-email@example.com
```

Enable per-service:
```yaml
deploy:
  labels:
    easyhaproxy.http.certbot: "true"
```

### Option 2: Custom Certificates

Mount certificates directory:
```yaml
# easyhaproxy.yml
volumes:
  - ./certs:/certs/haproxy
```

Place certificate files:
```bash
./certs/
  ├── example.com.pem
  ├── api.example.com.pem
  └── secure.example.com.pem
```

### Option 3: Docker Secrets (Production)

```bash
# Create secret
docker secret create example_com_cert ./example.com.pem

# Use in stack
version: "3"
services:
  haproxy:
    secrets:
      - example_com_cert
    environment:
      EASYHAPROXY_SSL_CERT_example_com: /run/secrets/example_com_cert

secrets:
  example_com_cert:
    external: true
```

---

## Monitoring and Stats

### HAProxy Stats Interface

Access at: `http://<swarm-ip>:1936`
- Username: `admin` (configured in `easyhaproxy.yml`)
- Password: `password` (configured in `easyhaproxy.yml`)

### Service Health

```bash
# Check service health
docker service ps myapp_webapp

# View detailed service info
docker service inspect --pretty myapp_webapp
```

---

## Troubleshooting

### Service Not Detected

**Check service labels:**
```bash
docker service inspect myapp_webapp | grep -A 20 Labels
```

Ensure labels are under `deploy.labels`, not top-level `labels`.

**Check EasyHAProxy logs:**
```bash
docker service logs -f easyhaproxy_haproxy
```

### Service Unreachable (503)

**Causes:**
- Service containers not ready yet
- Wrong network configuration
- Service crashed

**Debug:**
```bash
# Check service is running
docker service ps myapp_webapp

# Check network
docker network inspect easyhaproxy

# Test service directly
docker run --rm --network easyhaproxy alpine \
  wget -O- http://myapp_webapp:8080
```

### Overlay Network Issues

**Create network if missing:**
```bash
docker network create --driver overlay --attachable easyhaproxy
```

**Verify service is on network:**
```bash
docker service inspect myapp_webapp | grep -A 5 Networks
```

### EasyHAProxy Not Starting

**Check Docker socket permissions:**
```bash
docker service logs easyhaproxy_haproxy
```

**Verify socket is mounted:**
```bash
docker service inspect easyhaproxy_haproxy | grep -A 5 Mounts
```

### Certificate Issues

**Certbot fails:**
- Ensure swarm is publicly accessible
- Check DNS points to swarm IP
- Verify ports 80/443 are open
- Check certbot logs: `docker service logs easyhaproxy_haproxy | grep certbot`

**Custom cert not found:**
```bash
# Exec into service container
docker exec -it $(docker ps -q -f name=easyhaproxy) sh
ls -la /certs/haproxy/
```

---

## High Availability Setup

### Multiple Manager Nodes

```bash
# On additional manager nodes
docker swarm join-token manager
# Use token on new nodes
```

### EasyHAProxy Constraints

Run EasyHAProxy on specific node:

```yaml
services:
  haproxy:
    deploy:
      placement:
        constraints:
          - node.role == manager
          - node.labels.haproxy == true
```

Label node:
```bash
docker node update --label-add haproxy=true <node-name>
```

### Multiple EasyHAProxy Replicas

**Not recommended** - EasyHAProxy should run as single instance because:
- Multiple instances would compete for port binding
- Use external load balancer (cloud LB, keepalived, etc.) for HA

**Alternative HA pattern:**
```
Internet → Cloud Load Balancer → Multiple Swarm Nodes
                                  └→ EasyHAProxy (runs on 1 node)
                                     └→ Services (distributed across nodes)
```

---

## Best Practices

1. **Use Overlay Networks:**
   - Create dedicated network for EasyHAProxy
   - Use `--attachable` for flexibility

2. **Service Labels:**
   - Always use `deploy.labels`, never top-level `labels`
   - Use clear, descriptive domain names

3. **Replicas:**
   - Start with 2-3 replicas per service
   - Scale based on load monitoring
   - Use odd number for consensus (3, 5, 7)

4. **Updates:**
   - Use rolling updates for zero downtime
   - Set appropriate `update-delay`
   - Test in staging first

5. **Monitoring:**
   - Enable HAProxy stats
   - Use Portainer for visual management
   - Monitor service health regularly

6. **Security:**
   - Use Docker secrets for sensitive data
   - Restrict admin panel access
   - Use SSL/TLS for production
   - Apply IP whitelisting for admin interfaces

7. **Persistence:**
   - Use volumes for certbot certificates
   - Backup certificate volumes
   - Store custom certs in version control (encrypted)

---

## Further Reading

- [Docker Swarm Documentation](../../docs/swarm.md)
- [Container Labels Reference](../../docs/container-labels.md)
- [Using Plugins](../../docs/plugins.md)
- [ACME/Let's Encrypt](../../docs/acme.md)
- [Environment Variables](../../docs/environment-variable.md)
- [Official Docker Swarm Docs](https://docs.docker.com/engine/swarm/)
