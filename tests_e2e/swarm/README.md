# Docker Swarm Examples

Self-contained examples for EasyHAProxy in Docker Swarm mode. **All documentation is in the YAML files as header comments.**

## Quick Start

1. Pick an example below
2. Open the YAML file
3. Read the header comments for complete instructions
4. Run the commands step-by-step

## Prerequisites

All examples require:
- Docker Swarm initialized (`docker swarm init`)
- Overlay network created (`docker network create --driver overlay --attachable easyhaproxy`)
- EasyHAProxy deployed (`docker stack deploy -c easyhaproxy.yml easyhaproxy`)

See header comments in each file for detailed setup instructions.

## Basic Examples

| File | Description |
|------|-------------|
| [easyhaproxy.yml](easyhaproxy.yml) | EasyHAProxy service for Swarm with stats and certbot |
| [services.yml](services.yml) | Basic services with SSL (embedded cert and file-based) |
| [portainer.yml](portainer.yml) | Portainer management UI behind EasyHAProxy |

## Plugin Examples

| File | Description |
|------|-------------|
| [jwt-validator.yml](jwt-validator.yml) | JWT token validation for API protection |
| [ip-whitelist.yml](ip-whitelist.yml) | IP whitelist for admin panels or sensitive services |
| [cloudflare.yml](cloudflare.yml) | Restore real client IPs when behind Cloudflare CDN |
| [plugins-combined.yml](plugins-combined.yml) | Multiple plugins combined for layered security |

## Documentation Structure

Each YAML file contains:
- **WHAT THIS DEMONSTRATES** - Key features and concepts
- **REQUIREMENTS** - Idempotent setup commands (safe to run multiple times)
- **HOW TO START** - Command to deploy the stack
- **HOW TO VERIFY IT'S WORKING** - Test commands with expected outputs
- **CLEAN UP** - Commands to remove resources

## Important: Service Labels

In Swarm mode, labels must be under `deploy.labels`, NOT top-level `labels`:

```yaml
# ✅ CORRECT - Service labels
deploy:
  labels:
    easyhaproxy.http.host: example.com

# ❌ WRONG - Container labels (ignored in Swarm)
labels:
  easyhaproxy.http.host: example.com
```

## Additional Documentation

- [Docker Swarm Guide](../../docs/getting-started/swarm.md)
- [Container Labels Reference](../../docs/reference/container-labels.md)
- [Using Plugins](../../docs/guides/plugins.md)
- [ACME/Let's Encrypt](../../docs/guides/acme.md)
