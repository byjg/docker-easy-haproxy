# EasyHAProxy

[![Opensource ByJG](https://img.shields.io/badge/opensource-byjg-success.svg)](http://opensource.byjg.com)
[![Build Status](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml)
[![GitHub source](https://img.shields.io/badge/Github-source-informational?logo=github)](https://github.com/byjg/docker-easy-haproxy/)
[![GitHub license](https://img.shields.io/github/license/byjg/docker-easy-haproxy.svg)](https://opensource.byjg.com/opensource/licensing.html)
[![GitHub release](https://img.shields.io/github/release/byjg/docker-easy-haproxy.svg)](https://github.com/byjg/docker-easy-haproxy/releases/)

![EasyHAProxy](easyhaproxy_logo.png)

## Service discovery for HAProxy

The main objective of EasyHAProxy is dynamically create the `haproxy.cfg` based on the labels defined in docker containers.

EasyHAProxy can detect and configure automatically HAProxy on the folowing platforms:

- Docker
- Docker Swarm
- Kubernetes

## Features

EasyHAProxy will discover the services based on the Docker Tags of the running containers in a Docker host or Docker Swarm cluster and dynamically set up the `haproxy.cfg`. Below, EasyHAProxy main features:

- Use Letsencrypt with HAProxy.
- Set your custom SSL certificates
- Balance traffic between multiple replicas
- Set SSL with three different levels of validations and according to the most recent definitions.
- Setup HAProxy to listen to TCP.
- Add redirects.
- Enable/disable Stats on port 1936 with a custom password.
- Enable/disable custom errors.

Also, it is possible to set up HAProxy from a simple Yaml file instead of creating `haproxy.cfg` file.

## How It Works?

You don't need to change your current infrastructure and don't need to learn the HAProxy configuration.

You need run the EasyHAProxy container, add some labels to your existing container and EasyHAProxy will
automatically detect them and setup HAProxy for you.

## Detailed Instructions

For detailed instructions on how to use EasyHAProxy follow the instructions for the platform you want to use:

| Kubernetes | Docker Swarm | Docker |  Static
|:----------:|:------------:|:------:|:-------:
| [![Kubernetes](easyhaproxy_kubernetes.png)](docs/kubernetes.md) | [![Docker Swarm](easyhaproxy_swarm.png)](docs/swarm.md)  | [![Docker](easyhaproxy_docker.png)](docs/docker.md) | [![Static](easyhaproxy_static.png)](docs/static.md)


----
[Open source ByJG](http://opensource.byjg.com)
