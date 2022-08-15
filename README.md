# Easy HAProxy

[![Opensource ByJG](https://img.shields.io/badge/opensource-byjg-success.svg)](http://opensource.byjg.com)
[![Build Status](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml)
[![GitHub source](https://img.shields.io/badge/Github-source-informational?logo=github)](https://github.com/byjg/docker-easy-haproxy/)
[![GitHub license](https://img.shields.io/github/license/byjg/docker-easy-haproxy.svg)](https://opensource.byjg.com/opensource/licensing.html)
[![GitHub release](https://img.shields.io/github/release/byjg/docker-easy-haproxy.svg)](https://github.com/byjg/docker-easy-haproxy/releases/)

Service discovery for HAProxy.

This Docker image will create dynamically the `haproxy.cfg` based on the labels defined in docker containers or from
a simple Yaml.

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
    -e EASYHAPROXY_DISCOVER="swarm|docker|static" \
    # + Environment Variables \
    # + ports mapped to the host \
    byjg/easy-haproxy
```

The mapping to `/var/run/docker.sock` is necessary to discover the docker containers and get the labels;

The environment variables will setup the HAProxy.

| Environment Variable          | Description                                                                   |
|-------------------------------|-------------------------------------------------------------------------------|
| EASYHAPROXY_DISCOVER          | How `haproxy.cfg` will be created: `static`, `docker` or `swarm`              |
| EASYHAPROXY_LABEL_PREFIX      | (Optional) The key will search to match resources. Default: `easyhaproxy`.    |
[ EASYHAPROXY_LETSENCRYPT_EMAIL | (Optional) The email will be used to request certificate to letsencrypt       |      
| HAPROXY_USERNAME              | (Optional) The HAProxy username to the statistics. Default: `admin`           |
| HAPROXY_PASSWORD              | The HAProxy password to the statistics. If not set disable stats.             |
| HAPROXY_STATS_PORT            | (Optional) The HAProxy port to the statistics. Default: `1936`                |
| HAPROXY_CUSTOMERRORS.         | (Optional) If HAProxy will use custom HTML errors. true/false. Default: false |

The environment variable `EASYHAPROXY_DISCOVER` will define where is located your containers (see below more details):

- docker
- swarm
- static

## Automatic Discover Services

Easy HAProxy can discover automatically the container services running in the same network of Docker or in a Docker Swarm cluster. 

### EASYHAPROXY_DISCOVER: docker

This method will use a regular docker installation to discover the containers and configure the HAProxy.

The only requirement is that containers and easy-haproxy must be in the same docker network.

The discover will occur every minute.

e.g.:

```bash
docker create networkd easyhaproxy

docker run --network easyhaproxy byjg/easyhaproxy

docker run --network easyhaproxy myimage
```

### EASYHAPROXY_DISCOVER: swarm

This method requires a functional Docker Swarm Cluster. The system will search for the labels in all containers on all
swarm nodes.

The discover will occur every minute.

Important: easyhaproxy needs to be in the same network of the containers or otherwise will not access.

### Tags to be attached in the Docker Container (Swarm or Docker)

| Tag                                   | Description                                                                                             | Example      |
|---------------------------------------|---------------------------------------------------------------------------------------------------------|--------------|
| easyhaproxy.[definition].host         | Host(s) HAProxy is listening. More than one host use comma as delimiter                                 | somehost.com OR host1.com,host2.com |
| easyhaproxy.[definition].mode         | (Optional) Is this `http` or `tcp` mode in HAProxy. (Defaults to http)                                  | http         |
| easyhaproxy.[definition].port         | (Optional) Port HAProxy will listen for the host. (Defaults to 80)                                      | 80           |
| easyhaproxy.[definition].localport    | (Optional) Port container is listening. (Defaults to 80)                                                | 8080         |
| easyhaproxy.[definition].redirect     | (Optional) JSON containing key/value pair from host/to url redirect.                                    | {"foo.com":"https://bla.com", "bar.com":"https://bar.org"} |
| easyhaproxy.[definition].sslcert      | (Optional) Cert PEM Base64 encoded. Do not use this if letsencrypt is enabled.                          |              |
| easyhaproxy.[definition].health-check | (Optional) `ssl`, enable health check via SSL in `mode tcp` (Defaults to "empty")                       |              |
| easyhaproxy.[definition].letsencrypt  | (Optional) Generate certificate with letsencrypt. Do not use with sslcert                               | true, yes    |

### Defining the labels in Docker Swarm

if you are deploying a stack in a Docker Swarm cluster set labels at the `deploy` level:

```yaml
services:
 foo:
   deploy:
      labels:
         easyhaproxy.my.host: "www.example.org"
         easyhaproxy.my.localport: 8080
         ...
```

### Single Definition

```bash
docker run \
    -l easyhaproxy.webapi.port=80\
    -l easyhaproxy.webapi.host=byjg.com.br \
    ....
```

### Multiples Definitions on the same container

```bash
docker run \
    -l easyhaproxy.express.port=80 \
    -l easyhaproxy.express.localport=3000 \
    -l easyhaproxy.express.host=express.byjg.com.br \

    -l easyhaproxy.admin.port=80 \
    -l easyhaproxy.admin.localport=3001 \
    -l easyhaproxy.admin.host=admin.byjg.com.br \
    .... \
    some/myimage
```

### TLS passthrough

Used to pass on SSL-termination to a backend. Alternatively, you can enable health-check via SSL on the backend with the optional `health-check` label:

```bash
docker run \
    -l easyhaproxy.example.mode=tcp \
    -l easyhaproxy.example.health-check=ssl \
    -l easyhaproxy.example.port=443
    .... \
    some/tcp-service
```

### Redirect Example

```bash
docker run \
    -l easyhaproxy.[definition].redirect=www.byjg.com.br--http://byjg.com.br,byjg.com--http://byjg.com.br
```

## EASYHAPROXY_DISCOVER: static

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
      host1.com.br: 
        containers:
          - container:5000
        letsencrypt: true
      host2.com.br: 
        containers:
          - other:3000
    redirect:
      www.host1.com.br: http://host1.com.br

  - port: 443
    ssl_cert: /path/to/ssl/certificate
    hosts:
      host1.com.br: 
        containers:
          - container:80

  - port: 8080
    hosts:
      host3.com.br: 
        containers: 
          - domain:8181
```

Running:

```bash
docker run -v /my/config.yml:/etc/haproxy/easyconfig.yml .... byjg/easyhaproxy
```

## Letsencrypt

This HAProxy can issue a letsencrypt certificate. The command is as below:

Run the EasyHAProxy:

```bash
docker run \
    -e EASYHAPROXY_LETSENCRYPT_EMAIL=john@doe.com
    .... \
    byjg/easy-haproxy
```

Run your container:
```bash
docker run \
    -l easyhaproxy.express.port=80 \
    -l easyhaproxy.express.localport=3000 \
    -l easyhaproxy.express.host=example.org \
    -l easyhaproxy.express.letsencrypt=true \
    .... \
    some/myimage
```

Caveats:

- Your container **must** listen to the port 80. Besides no error, the certificate won't be issued if in a different port.
- The port 2080 is reserved for the certbot
- You cannot set the port 443 for the container with the Letsencrypt. EasyHAProxy will handle this automatically once the certificate is issued. 
- If you don't run the EasyHAProxy with the parameter `EASYHAPROXY_LETSENCRYPT_EMAIL` no certificate will be issued. 


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

3. Use this string to define the label `easyhaproxy.[definition].sslcert`

## Setting Custom Errors

If enabled, map the volume : `/etc/haproxy/errors-custom/` to your container and put a file named `ERROR_NUMBER.http`
where ERROR_NUMBER is the http error code (e.g. 503.http)

## Build


```bash
docker build -t byjg/easy-haproxy .
```

----
[Open source ByJG](http://opensource.byjg.com)
