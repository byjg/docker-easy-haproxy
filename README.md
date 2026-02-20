# EasyHAProxy

[![Sponsor](https://img.shields.io/badge/Sponsor-%23ea4aaa?logo=githubsponsors&logoColor=white&labelColor=0d1117)](https://github.com/sponsors/byjg)
[![Opensource ByJG](https://img.shields.io/badge/opensource-byjg-success.svg)](http://opensource.byjg.com)
[![Build Status](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml)
[![GitHub source](https://img.shields.io/badge/Github-source-informational?logo=github)](https://github.com/byjg/docker-easy-haproxy/)
[![GitHub license](https://img.shields.io/github/license/byjg/docker-easy-haproxy.svg)](https://opensource.byjg.com/opensource/licensing.html)
[![GitHub release](https://img.shields.io/github/release/byjg/docker-easy-haproxy.svg)](https://github.com/byjg/docker-easy-haproxy/releases/)
[![Helm Version](https://img.shields.io/badge/dynamic/yaml?color=blue&label=Helm&query=%24.entries.easyhaproxy%5B0%5D.version&url=http%3A%2F%2Fopensource.byjg.com%2Fhelm%2Findex.yaml)](https://opensource.byjg.com/helm)
[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/byjg)](https://artifacthub.io/packages/search?repo=byjg)

![EasyHAProxy](docs/easyhaproxy_logo.png)

## Service discovery for HAProxy

EasyHAProxy dynamically creates `haproxy.cfg` based on metadata from your workloads — Docker labels, Swarm service labels, or Kubernetes Ingress annotations. No HAProxy knowledge required.

## Features

- **Automatic service discovery** — Docker, Docker Swarm, Kubernetes, or static YAML
- **Zero-downtime HAProxy reload** — configuration updates happen without dropping connections
- **Automatic TLS with ACME** — Let's Encrypt, ZeroSSL, BuyPass, and more
- **Custom SSL certificates** — volume-mount or label-embed your own PEM files
- **TCP mode** — proxy any TCP service, not just HTTP
- **Plugin system** — JWT validation, IP whitelisting, Cloudflare IP restoration, FastCGI, path blocking, and custom plugins
- **HAProxy stats dashboard** — optional, password-protected
- **Balance algorithms** — roundrobin, leastconn, source, uri, and more

## Supported platforms

[![Kubernetes](docs/easyhaproxy_kubernetes.png)](docs/getting-started/kubernetes.md)
[![Docker Swarm](docs/easyhaproxy_swarm.png)](docs/getting-started/swarm.md)
[![Docker](docs/easyhaproxy_docker.png)](docs/getting-started/docker.md)
[![Static](docs/easyhaproxy_static.png)](docs/getting-started/static.md)

Install using tools:

[![Helm](docs/easyhaproxy_helm.png)](docs/guides/helm.md)
[![MicroK8s](docs/easyhaproxy_microk8s.png)](docs/guides/microk8s.md)
[![Dokku](docs/easyhaproxy_dokku.png)](docs/guides/dokku.md)
[![DigitalOcean](docs/easyhaproxy_digitalocean.png)](docs/guides/digitalocean.md)

## Documentation

| Section | Description |
|---------|-------------|
| **[Getting Started](docs/getting-started/)** | Choose your runtime and discovery mode, minimal working setup |
| **[Guides](docs/guides/ssl.md)** | SSL, ACME, plugins, Helm, MicroK8s, Dokku, DigitalOcean |
| **[Concepts](docs/concepts/)** | Service discovery, config pipeline, plugin model, TLS termination |
| **[Reference](docs/reference/environment-variables.md)** | Environment variables, container labels, CLI flags, volumes |

## Who is using?

EasyHAProxy is part of some projects:
- [Dokku](docs/guides/dokku.md)
- [MicroK8s](docs/guides/microk8s.md)
- [DigitalOcean Marketplace](docs/guides/digitalocean.md)

## See EasyHAProxy in action

Click on the image to see the videos (use HD for better visualization)

[![Docker In Action](docs/video-docker.png)](https://youtu.be/ar8raFK0R1k)
[![Docker and Letsencrypt](docs/video-docker-ssl.png)](https://youtu.be/xwIdj9mc2mU)
[![K8s In Action](docs/video-kubernetes.png)](https://youtu.be/uq7TuLIijks)
[![K8s and Letsencrypt](docs/video-kubernetes-letsencrypt.png)](https://youtu.be/v9Q4M5Al7AQ)
[![Static Configuration](docs/video-static.png)](https://youtu.be/B_bYZnRTGJM)
[![TCP Mode](docs/video-tcp-mysql.png)](https://youtu.be/JHqcq9crbDI)

[Here is the code](https://gist.github.com/byjg/e125e478a0562190176d69ea795fd3d4) applied in the test examples above.

----
[Open source ByJG](http://opensource.byjg.com)
