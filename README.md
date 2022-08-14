# Easy HAProxy

[![Opensource ByJG](https://img.shields.io/badge/opensource-byjg-success.svg)](http://opensource.byjg.com)
[![Build Status](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml)
[![GitHub source](https://img.shields.io/badge/Github-source-informational?logo=github)](https://github.com/byjg/docker-easy-haproxy/)
[![GitHub license](https://img.shields.io/github/license/byjg/uri.svg)](https://opensource.byjg.com/opensource/licensing.html)
[![GitHub release](https://img.shields.io/github/release/byjg/uri.svg)](https://github.com/byjg/docker-easy-haproxy/releases/)

Service discovery for HAProxy.

This Docker image will create dynamically the `haproxy.cfg` based on the labels defined in docker containers or from
a simple Yaml instead docker

## Features

- Enable or disable Stats on port 1936 with custom password
- Discover and setup haproxy from Docker Tag
- Discover and setup haproxy redirect from Docker Tag
- Setup HAProxy CFG from a Yaml file.

## Basic Usage

The Easy HAProxy will create the `haproxy.cfg` automatically based on the containers or from a YAML provided.

The basic command line to run is:

```bash
docker run -d \
    --name easy-haproxy-container \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -e DISCOVER="swarm|docker|static" \
    # + Environment Variables \
    # + ports mapped to the host \
    byjg/easy-haproxy
```

The mapping to `/var/run/docker.sock` is necessary to discover the docker containers and get the labels;

The environment variables will setup the HAProxy.

| Environment Variable | Description                                                                   |
|----------------------|-------------------------------------------------------------------------------|
| DISCOVER             | How `haproxy.cfg` will be created: `static`, `docker` or `swarm`              |
| LOOKUP_LABEL         | (Optional) The key will search to match resources. Default: `easyhaproxy`.     |
| HAPROXY_USERNAME     | (Optional) The HAProxy username to the statistics. Default: `admin`           |
| HAPROXY_PASSWORD     | The HAProxy password to the statistics. If not set disable stats.             |
| HAPROXY_STATS_PORT   | (Optional) The HAProxy port to the statistics. Default: `1936`                |
| HAPROXY_CUSTOMERRORS | (Optional) If HAProxy will use custom HTML errors. true/false. Default: false |

The environment variable `DISCOVER` will define where is located your containers (see below more details):

- docker
- swarm
- static

## Automatic Discover Services

Easy HAProxy can discover automatically the container services running in the same network of Docker or in a Docker Swarm cluster. 

### DISCOVER: docker

This method will use a regular docker installation to discover the containers and configure the HAProxy.

The only requirement is that containers and easy-haproxy must be in the same docker network.

The discover will occur every minute.

e.g.:

```bash
docker create networkd easyhaproxy

docker run --network easyhaproxy byjg/easyhaproxy

docker run --network easyhaproxy myimage
```

### DISCOVER: swarm

This method requires a functional Docker Swarm Cluster. The system will search for the labels in all containers on all
swarm nodes.

The discover will occur every minute.

Important: easyhaproxy needs to be in the same network of the containers or otherwise will not access.

### Tags to be attached in the Docker Container (Swarm or Docker)

| Tag                                | Description                                                                                             | Example      |
|------------------------------------|---------------------------------------------------------------------------------------------------------|--------------|
| easyhaproxy.definitions            | A Comma delimited list with the definitions. Each name requires the definition of the parameters below. | service,service2   |
| easyhaproxy.mode.[definition]      | (Optional) Is this `http` or `tcp` mode in HAProxy. (Defaults to http)                                  | http  |
| easyhaproxy.port.[definition]      | (Optional) What is the port that the HAProxy will listen to. (Defaults to 80)                           | 80           |
| easyhaproxy.localport.[definition] | (Optional) What is the port that the container is listening. (Defaults to 80)                           | 8080         |
| easyhaproxy.host.[definition]      | What is the host that the HAProxy will listen to.                                                       | somehost.com |
| easyhaproxy.redirect.[definition]  | (Optional) Host redirects from connections in the port defined above.                                   | foo.com--https://bla.com,bar.com--https://bar.org |
| easyhaproxy.sslcert.[definition]   | (Optional) Cert PEM Base64 encoded.                                                                     |              |
| easyhaproxy.health-check.[definition] | (Optional) `ssl`, enable health check via SSL in `mode tcp` (Defaults to "empty")                 |              |

### Defining the labels in Docker Swarm

if you are deploying a stack in a Docker Swarm cluster set labels at the `deploy` level:

```yaml
services:
 foo:
   deploy:
      labels:
         easyhaproxy.definitions: "service1,service2"
         ...
```

### Single Definition

```bash
docker run \
    -l easyhaproxy.definitions=webapi \
    -l easyhaproxy.port.webapi=80\
    -l easyhaproxy.host.webapi=byjg.com.br \
    ....
```

### Multiples Definitions on the same container

```bash
docker run \
    -l easyhaproxy.definitions=express,admin \

    -l easyhaproxy.port.express=80 \
    -l easyhaproxy.localport.express=3000 \
    -l easyhaproxy.host.express=express.byjg.com.br \

    -l easyhaproxy.port.admin=80 \
    -l easyhaproxy.localport.admin=3001 \
    -l easyhaproxy.host.admin=admin.byjg.com.br \
    .... \
    some/myimage
```

### TLS passthrough

Used to pass on SSL-termination to a backend. Alternatively, you can enable health-check via SSL on the backend with the optional `health-check` label:

```bash
docker run \
    -l easyhaproxy.defintions=example \
    -l easyhaproxy.mode.example=tcp \
    -l easyhaproxy.health-check.example=ssl \
    -l easyhaproxy.port.example=443
    .... \
    some/tcp-service
```

### Redirect Example

```bash
docker run \
    -l easyhaproxy.redirect.<defintion>=www.byjg.com.br--http://byjg.com.br,byjg.com--http://byjg.com.br
```

## DISCOVER: static

This method expects a YAML file to setup the `haproxy.cfg`

Create a YAML file and map to `/etc/haproxy/easyconfig.yml`

```yaml
stats:
  username: admin
  password: password
  port: 1936         # Optional (default 1936)

customerrors: true   # Optional (default false)

easymapping:
  - port: 80
    hosts:
      host1.com.br: container:5000
      host2.com.br: other:3000
    redirect:
      www.host1.com.br: http://host1.com.br

  - port: 443
    ssl_cert: /path/to/ssl/certificate
    hosts:
      host1.com.br: container:80

  - port: 8080
    hosts:
      host3.com.br: domain:8181
```

Running:

```bash
docker run -v /my/config.yml:/etc/haproxy/easyconfig.yml .... byjg/easyhaproxy
```

## Mapping custom .cfg files

Map a folder containing valid HAProxy `.cfg` files to `/etc/haproxy/conf.d`. It will be concatenated to your HAProxy CFG.

```bash
docker run \
    /* other parameters */
    -v /your/local/conf.d:/etc/haproxy/conf.d \
    -d byjg/easy-haproxy
```

## Handling SSL

You can attach a valid SSL certificate to the request.

1. First Create a single PEM file including CA.

```bash
cat example.com.crt example.com.key > single.pem

cat single.pem

-----BEGIN CERTIFICATE-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC5ZheHqmBnEJP+
U9r1gxYWKLzdqrMrcxtQN6M1hIH9n0peuJeIrybdcV7sMbStMXI=
-----END CERTIFICATE-----

-----BEGIN PRIVATE KEY-----
MIIEojCCA4qgAwIBAgIUegW2BimwuL4RzRZ2WYkHA6U5nkAwDQYJKoZIhvcNAQEL
3j4wz8/I5fdsk090j4s5KA==
-----END PRIVATE KEY-----
```

2. Convert it to BASE64 in a single line:

```bash
cat single.pem | base64 -w0
```

3. Use this string to define the label `easyhaproxy.sslcert.[definition]`

## Setting Custom Errors

If enabled, map the volume : `/etc/haproxy/errors-custom/` to your container and put a file named `ERROR_NUMBER.http`
where ERROR_NUMBER is the http error code (e.g. 503.http)

## Build


```bash
docker build -t byjg/easy-haproxy .
```

----
[Open source ByJG](http://opensource.byjg.com)
