# Kubernetes Examples

Self-contained examples for EasyHAProxy ingress controller. **All documentation is in the YAML files as header comments.**

## Quick Start

1. Pick an example below
2. Open the YAML file
3. Read the header comments for complete instructions
4. Run the commands step-by-step

## Prerequisites

All examples require:
- EasyHAProxy installed in your Kubernetes cluster
- Node labeled for EasyHAProxy deployment

See header comments in each file for detailed setup instructions.

## Basic Examples

| File                               | Description                                |
|------------------------------------|--------------------------------------------|
| [service.yml](service.yml)         | Basic HTTP ingress with multiple domains   |
| [service_tls.yml](service_tls.yml) | HTTPS/TLS ingress with custom certificates |

## Plugin Examples

| File                                         | Description                                         |
|----------------------------------------------|-----------------------------------------------------|
| [jwt-validator.yml](jwt-validator.yml)       | JWT token validation for API protection             |
| [ip-whitelist.yml](ip-whitelist.yml)         | IP whitelist for admin panels or sensitive services |
| [cloudflare.yml](cloudflare.yml)             | Restore real client IPs when behind Cloudflare CDN  |
| [plugins-combined.yml](plugins-combined.yml) | Multiple plugins combined for layered security      |

## Documentation Structure

Each YAML file contains:
- **WHAT THIS DEMONSTRATES** - Key features and concepts
- **REQUIREMENTS** - Idempotent setup commands (safe to run multiple times)
- **HOW TO START** - Command to apply the manifest
- **HOW TO VERIFY IT'S WORKING** - Test commands with expected outputs
- **CLEAN UP** - Commands to remove resources

## Additional Documentation

- [Kubernetes Installation Guide](../../docs/kubernetes.md)
- [Helm Installation](../../docs/helm.md)
- [Kubernetes Annotations Reference](../../docs/kubernetes.md#kubernetes-annotations)
- [Using Plugins with Kubernetes](../../docs/kubernetes.md#using-plugins-with-kubernetes)
