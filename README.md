# Easy HAProxy 

This Docker image will create dynamically the `haproxy.cfg` based on the labels defined in docker containers or from 
a simple Yaml instead docker 

# Features

- Enable or disable Stats on port 1936 with custom password
- Discover and setup haproxy from Docker Tag 
- Discover and setup haproxy redirect from Docker Tag
- Setup HAProxy CFG from a Yaml file. 


# Basic Usage

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
| HAPROXY_USERNAME     | (Optional) The HAProxy username to the statistics. Default: `admin`           |
| HAPROXY_PASSWORD     | The HAProxy password to the statistics. If not set disable stats.             |
| HAPROXY_STATS_PORT   | (Optional) The HAProxy port to the statistics. Default: `1936`                |
| HAPROXY_CUSTOMERRORS | (Optional) If HAProxy will use custom HTML errors. true/false. Default: false |



The environment variable `DISCOVER` will define where is located your containers (see below more details):
- docker
- swarm
- static

# DISCOVER: `docker`

This method will use a regular docker installation to discover the containers and configure the HAProxy. 

The only requirement is that containers and easy-haproxy must be in the same docker network. 

The discover will occur every minute.

e.g.:

```bash
docker create networkd easyhaproxy

docker run --network easyhaproxy byjg/easyhaproxy

docker run --network easyhaproxy myimage
```

# DISCOVER: `swarm`

This method requires a functional Docker Swarm Cluster. The system will search for the labels in all containers on all 
swarm nodes. 

The discover will occur every minute.

Important: easyhaproxy needs to be in the same network of the containers or otherwise will not access.   

## Tags to be attached in the Docker Container

| Tag                                         | Description                                                                                             |
|---------------------------------------------|---------------------------------------------------------------------------------------------------------|
| com.byjg.easyhaproxy.definitions            | A Comma delimited list with the definitions. Each name requires the definition of the parameters below. |
| com.byjg.easyhaproxy.port.<definition>      | (Optional) What is the port that the HAProxy will listen to. (Defaults to 80)                           |
| com.byjg.easyhaproxy.localport.<definition> | (Optional) What is the port that the container is listening. (Defaults to 80)                           |
| com.byjg.easyhaproxy.host.<definition>      | What is the host that the HAProxy will listen to.                                                       |
| com.byjg.easyhaproxy.redirect.<definition>  | (Optional) Host redirects from connections in the port defined above.                                   |
| com.byjg.easyhaproxy.sslcert.<definition>   | (Optional) Cert PEM Base64 encoded.                                                                     |


Note: if you are deploying a stack set labels at the `deploy` level:

```yaml
services:
 foo:
   deploy:
      labels:
         com.byjg.easyhaproxy.definitions: "http,https"
         ...
```


### Single Definition:

```bash
docker run \
    -l com.byjg.easyhaproxy.definitions=http \
    -l com.byjg.easyhaproxy.port.http=80\
    -l com.byjg.easyhaproxy.host.http=byjg.com.br \
    ....
```

### Multiples Definitions on the same container:

```bash
docker run \
    -l com.byjg.easyhaproxy.definitions=express,admin \

    -l com.byjg.easyhaproxy.port.express=80 \
    -l com.byjg.easyhaproxy.localport.express=3000 \
    -l com.byjg.easyhaproxy.host.express=express.byjg.com.br \

    -l com.byjg.easyhaproxy.port.admin=80 \
    -l com.byjg.easyhaproxy.localport.admin=3001 \
    -l com.byjg.easyhaproxy.host.admin=admin.byjg.com.br \
    .... \
    some/myimage
```

### Redirect Example:

```bash
docker run \
    -l com.byjg.easyhaproxy.redirect.<defintion>=www.byjg.com.br--http://byjg.com.br,byjg.com--http://byjg.com.br
```

# DISCOVER: `static`

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
    ssl_cert: BASE64_PEM_CERTIFICATE
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

# Mapping custom .cfg files

Map a folder containing valid HAProxy `.cfg` files to `/etc/haproxy/conf.d`. It will be concatenated to your HAProxy CFG. 

```bash
docker run \ 
    /* other parameters */
    -v /your/local/conf.d:/etc/haproxy/conf.d \
    -d byjg/easy-haproxy
```


# Handling SSL

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

3. Use this string to define the label `com.byjg.easyhaproxy.sslcert.<definition>`

# Setting Custom Errors

If enabled, map the volume : `/etc/haproxy/errors-custom/` to your container and put a file named `ERROR_NUMBER.http` 
where ERROR_NUMBER is the http error code (e.g. 503.http)  

# Build

```
docker build -t byjg/easy-haproxy .
```


