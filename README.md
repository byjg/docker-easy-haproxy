# EasyHAProxy

[![Opensource ByJG](https://img.shields.io/badge/opensource-byjg-success.svg)](http://opensource.byjg.com)
[![Build Status](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml)
[![GitHub source](https://img.shields.io/badge/Github-source-informational?logo=github)](https://github.com/byjg/docker-easy-haproxy/)
[![GitHub license](https://img.shields.io/github/license/byjg/docker-easy-haproxy.svg)](https://opensource.byjg.com/opensource/licensing.html)
[![GitHub release](https://img.shields.io/github/release/byjg/docker-easy-haproxy.svg)](https://github.com/byjg/docker-easy-haproxy/releases/)
[![Helm Version](https://img.shields.io/badge/dynamic/yaml?color=blue&label=Helm&query=%24.entries.easyhaproxy%5B0%5D.version&url=http%3A%2F%2Fopensource.byjg.com%2Fhelm%2Findex.yaml)](https://opensource.byjg.com/helm)

![EasyHAProxy](docs/easyhaproxy_logo.png)

## Service discovery for HAProxy

EasyHAProxy dynamically creates the `haproxy.cfg` based on the labels defined in docker containers.

EasyHAProxy can detect and configure HAProxy automatically on the following platforms:

- Docker
- Docker Swarm
- Kubernetes

## Features

EasyHAProxy will discover the services based on the Docker Tags of the containers running on a Docker host or Docker Swarm cluster and dynamically set up the `haproxy.cfg`. Below, EasyHAProxy main features:

- Automatic SSL Certificate issued by any ACME compatible service as Letsencrypt and ZeroSSL
- Set your custom SSL certificates
- Balance traffic between multiple replicas
- Set SSL with three different levels of validations and according to the most recent definitions.
- Set up HAProxy to listen to TCP.
- Add redirects.
- Enable/disable Stats on port 1936 with a custom password.
- Enable/disable custom errors.

Also, it is possible to set up HAProxy from a simple Yaml file instead of creating `haproxy.cfg` file.

## How Does It Works?

You don't need to change your current infrastructure and don't need to learn the HAProxy configuration.

The steps are:

- Run the EasyHAProxy container;
- Add some labels to the containers you want to be parsed by EasyHAProxy (see detailed instructions below);
- EasyHAProxy will automatically detect the containers, set up, and reload the HAProxy configurations for you without downtime.

## Detailed Instructions

For detailed instructions on how to use EasyHAProxy, follow the instructions for the platform you want to use:

[![Kubernetes](docs/easyhaproxy_kubernetes.png)](docs/kubernetes.md)
[![Docker Swarm](docs/easyhaproxy_swarm.png)](docs/swarm.md)
[![Docker](docs/easyhaproxy_docker.png)](docs/docker.md)
[![Static](docs/easyhaproxy_static.png)](docs/static.md)

Or you can install using tools:

[![Helm](docs/easyhaproxy_helm.png)](docs/helm.md)
[![MicroK8s](docs/easyhaproxy_microk8s.png)](docs/microk8s.md)
[![Dokku](docs/easyhaproxy_dokku.png)](docs/dokku.md)

## See EasyHAProxy in action

Click on the image to see the videos (use HD for better visualization)

[![Docker In Action](docs/video-docker.png)](https://youtu.be/ar8raFK0R1k)
[![Docker and Letsencrypt](docs/video-docker-ssl.png)](https://youtu.be/xwIdj9mc2mU)
[![K8s In Action](docs/video-kubernetes.png)](https://youtu.be/uq7TuLIijks)
[![K8s and Letsencrypt](docs/video-kubernetes-letsencrypt.png)](https://youtu.be/v9Q4M5Al7AQ)
[![Static Configuration](docs/video-static.png)](https://youtu.be/B_bYZnRTGJM)
[![TCP Mode](docs/video-tcp-mysql.png)](https://youtu.be/JHqcq9crbDI)

[Here is the code](https://gist.github.com/byjg/e125e478a0562190176d69ea795fd3d4) applied in the examples above.

----
[Open source ByJG](http://opensource.byjg.com)
