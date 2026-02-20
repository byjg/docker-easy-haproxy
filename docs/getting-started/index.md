---
sidebar_position: 1
sidebar_label: "Getting Started"
---

# Getting Started with EasyHAProxy

EasyHAProxy dynamically builds `haproxy.cfg` from metadata on your running workloads — no HAProxy knowledge required.

## Choose your runtime

EasyHAProxy runs in two ways:

| Runtime | When to choose |
|---------|---------------|
| **Docker container** (`byjg/easy-haproxy`) | You already run Docker, Swarm, or Kubernetes |
| **Native host** (`easy-haproxy` CLI) | You want HAProxy on the host with full OS control — no Docker needed |

## Choose your discovery mode

Once running, EasyHAProxy discovers your services in one of four ways:

| Mode | How it works | Label/annotation format |
|------|-------------|------------------------|
| **Docker** | Reads labels from running containers on a Docker host | Container labels |
| **Swarm** | Reads labels from services in a Docker Swarm cluster | Service labels |
| **Kubernetes** | Reads `ingressClassName: easyhaproxy` Ingress resources | Ingress annotations |
| **Static** | Reads a hand-written YAML file you provide | YAML file |

## Quick-start guides

Pick the guide that matches your environment:

### Container runtimes (Docker image)

- **[Docker](docker.md)** — standalone Docker host, container labels
- **[Docker Swarm](swarm.md)** — overlay network, service labels
- **[Kubernetes](kubernetes.md)** — Ingress controller, DaemonSet/NodePort
- **[Static YAML](static.md)** — any environment, config file

### Native host (pip/uv package)

- **[Native install](native.md)** — HAProxy on the host, `easy-haproxy` CLI

## What's next?

After you have traffic flowing:

- **[Guides](../guides/ssl.md)** — SSL certificates, ACME/Let's Encrypt, plugins
- **[Concepts](../concepts/index.md)** — how service discovery and the config pipeline work
- **[Reference](../reference/environment-variables.md)** — full environment variable and label tables
