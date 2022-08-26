# Easy HAProxy

[![Opensource ByJG](https://img.shields.io/badge/opensource-byjg-success.svg)](http://opensource.byjg.com)
[![Build Status](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/byjg/docker-easy-haproxy/actions/workflows/build.yml)
[![GitHub source](https://img.shields.io/badge/Github-source-informational?logo=github)](https://github.com/byjg/docker-easy-haproxy/)
[![GitHub license](https://img.shields.io/github/license/byjg/docker-easy-haproxy.svg)](https://opensource.byjg.com/opensource/licensing.html)
[![GitHub release](https://img.shields.io/github/release/byjg/docker-easy-haproxy.svg)](https://github.com/byjg/docker-easy-haproxy/releases/)

## Service discovery for HAProxy

This Docker image will dynamically create the `haproxy.cfg` based on the labels defined in docker containers or from
a simple Yaml.

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

## Basic Usage

The Easy HAProxy will automatically create the `haproxy.cfg` file based on the containers or a YAML provided.

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

| Environment Variable          | Description                                                                                     | Default          |
|-------------------------------|-------------------------------------------------------------------------------------------------|------------------|
| EASYHAPROXY_DISCOVER          | How the services will be discovered to create `haproxy.cfg`:  `static`, `docker`, `swarm` or `kubernetes`     | **required**     |
| EASYHAPROXY_LABEL_PREFIX      | (Optional) The key will search for matching resources.                                          | `easyhaproxy`    |
| EASYHAPROXY_LETSENCRYPT_EMAIL | (Optional) The email will be used to request the certificate to Letsencrypt                     | *empty*          |
| EASYHAPROXY_SSL_MODE          | (Optional) `strict` supports only the most recent TLS version; `default` good SSL integration with recent browsers; `loose` supports all old SSL protocols for old browsers (not recommended).  | `default`|
| EASYHAPROXY_REFRESH_CONF      | (Optional) Check configuration every N seconds.                                                 | 10               |
| EASYHAPROXY_LOG_LEVEL         | (Optional) The log level for EasyHAproxy messages. Available: TRACE,DEBUG,INFO,WARN,ERROR,FATAL | DEBUG            |
| CERTBOT_LOG_LEVEL             | (Optional) The log level for Certbot messages. Available: TRACE,DEBUG,INFO,WARN,ERROR,FATAL     | DEBUG            |
| HAPROXY_LOG_LEVEL             | (Optional) The log level for HAProxy messages. Available: TRACE,DEBUG,INFO,WARN,ERROR,FATAL     | DEBUG            |
| HAPROXY_USERNAME              | (Optional) The HAProxy username to the statistics.                                              |  `admin`         |
| HAPROXY_PASSWORD              | (Optional) The HAProxy password to the statistics. If not set, statistics will be available with no password  | *empty* |
| HAPROXY_STATS_PORT            | (Optional) The HAProxy port to the statistics. If set to `false`, disable statistics            | `1936`           |
| HAPROXY_CUSTOMERRORS          | (Optional) If HAProxy will use custom HTML errors. true/false.                                  | `false`          |

The environment variable `EASYHAPROXY_DISCOVER` will define where is located your containers (see below for more details):

- docker
- swarm
- static

## Automatic Discover Services

Easy HAProxy can automatically discover the container services running in the same network of Docker or in a Docker Swarm cluster. 

### EASYHAPROXY_DISCOVER: docker

This method will use a standard docker installation to discover the containers and configure the HAProxy.

The only requirement is that containers and easy-haproxy must be in the same docker network.

The discovery will occur every minute.

e.g.:

```bash
docker create network easyhaproxy

docker run --network easyhaproxy byjg/easyhaproxy

docker run --network easyhaproxy myimage
```

or, if the container is already created you can join it using the command:

```bash
docker network connect easyhaproxy mycontainer
```

### EASYHAPROXY_DISCOVER: swarm

This method requires a functional Docker Swarm Cluster. The system will search for the labels in all containers on all
swarm nodes.

The discovery will occur every minute.

Important: easyhaproxy needs to be in the same network of the containers or otherwise will not access.

### EASYHAPROXY_DISCOVER: kubernetes (experimental and limited)

This will query all `ingress` in the kubernetes cluster and check the annotation `kubernetes.io/ingress.class: easyhaproxy-ingress`.

e.g.:

```yaml
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
  name: example-ingress
  namespace: example
spec:
  rules:
  - host: example.org
    http:
      paths:
      - backend:
          service:
            name: example-service
            port:
              number: 8080
        pathType: ImplementationSpecific
  - host: www.example.org
    http:
      paths:
      - backend:
          service:
            name: example-service
            port:
              number: 8080
        pathType: ImplementationSpecific
```

Caveats:

- At this point, the implementation don't support all ingress properties nor wildcard domains.
- The ingress will publish externally only the ports 80 and 443, plus 1936 if stats is enable.
- The system will read  `spec.rules[].host` and `spec.rules[].http.paths[0].port.number` and ignore the other parameters.
- Only the first path `spec.rules[].http.paths[0]` will be parsed.
- There are specific annotations can be added as described bellow.

### Kubernetes annotations

| annotation                  | Description                                                                             | Default      | Example      |
|-----------------------------|-----------------------------------------------------------------------------------------|--------------|--------------|
| kubernetes.io/ingress.class | (required) Activate EasyHAProxy.                                                        | **required** | easyhaproxy-ingress
| easyhaproxy.redirect_ssl    | (optional) Boolean. Force redirect all endpoints to https.                              | false        | true or false
| easyhaproxy.letsencrypt     | (optional) Boolean. It will request letsencript certificates for the ingresses domains. | false        | true or false
| easyhaproxy.redirect        | (optional) Json. Specific a domain and its destination.                                 | *empty*      | {"domain":"redirect_url"}
| easyhaproxy.mode            | (optional) Set the HTTP mode for that connection.                                       | http         | http or tcp

**Important**: The annotations are per ingress and applied to all hosts in that ingress configuration.

### Kubernetes and Letsencrypt:

It is necessary add the annotation `easyhaproxy.letsencrypt` to the ingress configuration:

```yaml
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
    easyhaproxy.letsencrypt: 'true'
  name: example-ingress
  namespace: example
spec:
  ....
```

Make sure your cluster is accessible both through ports 80 and 443.

### Kubernetes and SSL

You need to create a secret with your certificate and key, and associate them in your ingress.

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: host2-tls
  namespace: default
data:
  tls.crt: base64 of your certificate
  tls.key: base64 of your certificate private key
type: kubernetes.io/tls

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
  name: tls-example
  namespace: default
spec:
  tls:
  - hosts:
      - host2.local
    secretName: host2-tls
  rules:
    ...
```

### Container (Docker or Swarm) labels

| Tag                                   | Description                                                                                           | Default               | Example      |
|---------------------------------------|-------------------------------------------------------------------------------------------------------|----------------|--------------|
| easyhaproxy.[definition].host         | Host(s) HAProxy is listening. More than one host use comma as delimiter                               | **required**   | somehost.com OR host1.com,host2.com |
| easyhaproxy.[definition].mode         | (Optional) Is this `http` or `tcp` mode in HAProxy.                                                   | http           | http or tcp    |
| easyhaproxy.[definition].port         | (Optional) Port HAProxy will listen for the host.                                                     | 80             | 3000           |
| easyhaproxy.[definition].localport    | (Optional) Port container is listening.                                                               | 80             | 8080           |
| easyhaproxy.[definition].redirect     | (Optional) JSON containing key/value pair from host/to URL redirect.                                  | *empty*        | {"foo.com":"https://bla.com", "bar.com":"https://bar.org"} |
| easyhaproxy.[definition].sslcert      | (Optional) Cert PEM Base64 encoded. Do not use this if `letsencrypt` is enabled.                      | *empty*        | base64 cert + key |
| easyhaproxy.[definition].ssl          | (Optional) If `true` you need to provide certificate as a file. See below. Do not use with `sslcert`. | false          | true or false  |
| easyhaproxy.[definition].health-check | (Optional) `ssl`, enable health check via SSL in `mode tcp`                                           | *empty*        | ssl            |
| easyhaproxy.[definition].letsencrypt  | (Optional) Generate certificate with letsencrypt. Do not use with `sslcert` parameter.                | false          | true OR false  |
| easyhaproxy.[definition].redirect_ssl | (Optional) Redirect all requests to https                                                             | false          | true OR false  |
| easyhaproxy.[definition].clone_to_ssl | (Optional) It copies the configuration to HTTPS(443) and disable SSL from the current config. **Do not use* this with `ssl` or `letsencrypt` parameters | false | true OR false    |

### Defining the labels in Docker Swarm

if you are deploying a stack in a Docker Swarm cluster, set labels at the `deploy` level:

```yaml
services:
 foo:
   deploy:
      labels:
         easyhaproxy.my.host: "www.example.org"
         easyhaproxy.my.localport: 8080
         ...
```

```bash
docker stack deploy --compose-file docker-compose.yml mystack
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

### Multiples hosts on the same container

```bash
docker run \
    -l easyhaproxy.express.port=80 \
    -l easyhaproxy.express.localport=3000 \
    -l easyhaproxy.express.host=express.byjg.com.br,admin.byjg.com.br \
    .... \
    some/myimage
```

If you are using docker-compose you can use this way:

```yaml
version: "3"

services:
  mycontainer:
    image: some/myimage
    labels:
      easyhaproxy.express.port: 80
      easyhaproxy.express.localport: 3000
      easyhaproxy.express.host: >-
        express.byjg.com.br,
        admin.byjg.com.br
```

### TLS passthrough

Used to pass on SSL termination to a backend. Alternatively, you can enable health-check via SSL on the backend with the optional `health-check` label:

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
    -l easyhaproxy.[definition].redirect='{"www.byjg.com.br":"http://byjg.com.br","byjg.com":"http://byjg.com.br"}'
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

ssl_mode: default

letsencrypt: {
  "email": "acme@example.org"
}

easymapping:
  - port: 80
    hosts:
      host1.com.br: 
        containers:
          - container:5000
        letsencrypt: true
        redirect_ssl: true
      host2.com.br: 
        containers:
          - other:3000
    redirect:
      www.host1.com.br: http://host1.com.br

  - port: 443
    hosts:
      host1.com.br: 
        containers:
          - container:80
        redirect_ssl: false
      ssl: true

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
- The port 2080 is reserved for the certbot and should not be exposed.
- You cannot set the port 443 for the container with the Letsencrypt because EasyHAProxy will handle this automatically once the certificate is issued.
- If you don't run the EasyHAProxy with the parameter `EASYHAPROXY_LETSENCRYPT_EMAIL` no certificate will be issued. 
- Be aware of Letsencrypt issue limits - https://letsencrypt.org/docs/duplicate-certificate-limit/ and https://letsencrypt.org/docs/rate-limits/

## Exposing Ports

You must expose some ports on the EasyHAProxy container and in the firewall. However, you don't need to expose the other container ports because EasyHAProxy will handle that.

- The ports `80` and `443`.
- If you enable the HAProxy statistics, you must also expose the port defined in `HAPROXY_STATS_PORT` environment variable (default 1936). Be aware that statististics are enabled by default with no password.
- Every port defined in `easyhaproxy.[definitions].port` also should be exposed. 

e.g.

```bash
docker run \
    /* other parameters */
    -p 80:80 \
    -p 443:443 \
    -p 1936:1936 \
    -d byjg/easy-haproxy
```

## Mapping custom .cfg files

You can concatenate valid HAProxy `.cfg` files to the dynamically generated `haproxy.cfg` by mapping the folder `/etc/haproxy/conf.d`.

```bash
docker run \
    /* other parameters */
    -v /your/local/conf.d:/etc/haproxy/conf.d \
    -d byjg/easy-haproxy
```

## Mapping SSL certificates volumes

EasyHAProxy stores the certificates inside the folder `/certs/haproxy` and `/certs/letsencrypt`.

- If you want to preserve the letsencrypt certificates between reloads, map the folder `/certs/letsencrypt` to your volume. 
- If you want to provide your certificates as a file instead of a Base64 parameter, map the folder `/certs/haproxy` to your volume, and instead of use `easyhaproxy.[definition].sslcert`, use `easyhaproxy.[definition].ssl: true`

```bash
docker run \
    /* other parameters */
    -v /your/certs/letsencrypt:/certs/letsencrypt \
    -d byjg/easy-haproxy
```

## Handling SSL

You can attach a valid SSL certificate to the request.

1. First, Create a single PEM file including CA.

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
where ERROR_NUMBER is the HTTP error code (e.g., `503.http`)

## Build

```bash
docker build -t byjg/easy-haproxy .
```

## Limitations

EasyHAProxy has some limitations when there is more than one easy-haproxy container running:

- Replicas can be out-of-sync for a few seconds because each replica will discover the pods separately. 
- Each replica will request a Letsencrypt certificate and can fail because the letsencrypt challenge can be directed to the other replica. 

----
[Open source ByJG](http://opensource.byjg.com)
