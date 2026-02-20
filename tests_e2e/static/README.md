# Static Configuration Example

Self-contained example for EasyHAProxy using static YAML configuration. **All documentation is in the docker-compose file as header comments.**

## Quick Start

1. Open [docker-compose.yml](docker-compose.yml)
2. Read the header comments for complete instructions
3. Choose a configuration scenario from `conf/` directory
4. Run the commands step-by-step

## What is Static Mode?

Static mode uses explicit YAML configuration files instead of dynamic service discovery. This is useful for:
- **Non-containerized backends** - VMs, bare metal servers, external APIs
- **Fixed infrastructure** - When your backend IPs/ports don't change
- **Explicit routing control** - Precise control over HAProxy configuration

## Configuration Files

All scenarios use `/etc/easyhaproxy/static/config.yml` mounted from `./conf/config.yml`.

Choose one of these pre-made configurations:

| Configuration File         | Description                                     |
|----------------------------|-------------------------------------------------|
| `config-basic.yml`         | Simple HTTP→HTTPS redirect with SSL termination |
| `config-certbot.yml`       | Let's Encrypt SSL (requires public domain)      |
| `config-deny-pages.yml`    | Block specific paths (e.g., `/admin`, `/.env`)  |
| `config-jwt-validator.yml` | JWT token validation for API authentication     |

## Prerequisites

- SSL certificates generated (`./tests_e2e/generate-keys.sh`)
- `/etc/hosts` entry for `host1.local`
- Backend container running on port 8080

See header comments in [docker-compose.yml](docker-compose.yml) for detailed setup.

## Documentation Structure

The docker-compose.yml file contains:
- **WHAT THIS DEMONSTRATES** - Key features and concepts
- **REQUIREMENTS** - Idempotent setup commands (safe to run multiple times)
- **HOW TO START** - Commands to start backend and EasyHAProxy
- **HOW TO VERIFY IT'S WORKING** - Test commands with expected outputs
- **CLEAN UP** - Commands to stop and remove resources

## Example Workflow

```bash
# 1. Generate certificates
cd ../.. && ./tests_e2e/generate-keys.sh && cd tests_e2e/static

# 2. Choose a configuration
cp conf/config-basic.yml conf/config.yml

# 3. Start backend
docker run -d --name container -p 8080:8080 byjg/static-httpserver

# 4. Start EasyHAProxy
docker compose up -d

# 5. Test
curl -k https://host1.local/

# 6. Clean up
docker compose down
docker stop container && docker rm container
```

## Configuration File Reference

Basic structure of `config.yml`:

```yaml
stats:
  username: admin
  password: password
  port: 1936

containers:
  "host1.local:443":
    ip: ["container:8080"]  # Can also be IP:PORT for external backends
    ssl: true
```

See `conf/` directory for complete examples.

## Additional Documentation

- [Static Configuration Guide](../../docs/getting-started/static.md)
- [Using Plugins](../../docs/guides/plugins.md)
- [Environment Variables](../../docs/reference/environment-variables.md)
