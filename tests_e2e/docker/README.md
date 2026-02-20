# Docker Compose Examples

Self-contained examples for EasyHAProxy. **All documentation is in the docker-compose files as header comments.**

## Quick Start

1. Pick an example below
2. Open the docker-compose file
3. Read the header comments for complete instructions
4. Run the commands step-by-step

## Basic Examples

| File                                                                       | Description                                                    |
|----------------------------------------------------------------------------|----------------------------------------------------------------|
| [docker-compose.yml](docker-compose.yml)                                   | Basic SSL setup with two virtual hosts and stats interface     |
| [docker-compose-acme.yml](docker-compose-acme.yml)                         | Let's Encrypt SSL with automatic certificate generation        |
| [docker-compose-multi-containers.yml](docker-compose-multi-containers.yml) | Load balancing across multiple container replicas              |
| [docker-compose-changed-label.yml](docker-compose-changed-label.yml)       | Using custom label prefix (for multiple EasyHAProxy instances) |

## Real-World Application Examples

| File                                                                                 | Description                                         |
|--------------------------------------------------------------------------------------|-----------------------------------------------------|
| [docker-compose-portainer.yml](docker-compose-portainer.yml)                         | Portainer behind EasyHAProxy with Let's Encrypt     |
| [docker-compose-portainer-app-example.yml](docker-compose-portainer-app-example.yml) | Additional app alongside Portainer (shared network) |

## Plugin Examples

| File                                                                       | Description                                         |
|----------------------------------------------------------------------------|-----------------------------------------------------|
| [docker-compose-php-fpm.yml](docker-compose-php-fpm.yml)                   | FastCGI plugin with PHP-FPM and PATH_INFO routing   |
| [docker-compose-jwt-validator.yml](docker-compose-jwt-validator.yml)       | JWT token validation for API protection             |
| [docker-compose-ip-whitelist.yml](docker-compose-ip-whitelist.yml)         | IP whitelist for admin panels or sensitive services |
| [docker-compose-cloudflare.yml](docker-compose-cloudflare.yml)             | Restore real client IPs when behind Cloudflare CDN  |
| [docker-compose-plugins-combined.yml](docker-compose-plugins-combined.yml) | Multiple plugins combined for layered security      |

## Documentation Structure

Each docker-compose file contains:
- **WHAT THIS DEMONSTRATES** - Key features and concepts
- **REQUIREMENTS** - Idempotent setup commands (safe to run multiple times)
- **HOW TO START** - Command to launch the stack
- **HOW TO VERIFY IT'S WORKING** - Test commands with expected outputs
- **CLEAN UP** - Commands to stop and remove resources

## Additional Documentation

- [Container Labels Reference](../../docs/reference/container-labels.md)
- [Docker Configuration Guide](../../docs/getting-started/docker.md)
- [Environment Variables](../../docs/reference/environment-variables.md)
- [Plugin Documentation](../../docs/guides/plugins.md)
