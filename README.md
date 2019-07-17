# Easy HAProxy 

This Docker image will create dynamically the `haproxy.cfg` based on very simple Yaml.

# Features

- Enable or disable Stats on port 1936 with custom password
- Discover and setup haproxy from Docker Tag 
- Discover and setup haproxy redirect from Docker Tag


# Basic Usage

Docker run:

```bash
docker run \ 
    -p 80:80 \
    -p 8080:8080 \
    -p 1936:1936 \
    --name easy-haproxy-instance \
    -e DISCOVER=swarm \
    -e HAPROXY_USERNAME=admin \
    -e HAPROXY_PASSWORD=password \
    -e HAPROXY_STATS_PORT=1936 \ 
    -v /var/run/docker.sock:/var/run/docker.sock \
    -d byjg/easy-haproxy
```

The `DISCOVER` environment variable will define where is located your containers (see below more details):
- swarm
- static (maps to /etc/haproxy/easyconfig.yml)

# Tags to defined:

| Tag                                         | Description                                                                                             |
|---------------------------------------------|---------------------------------------------------------------------------------------------------------|
| com.byjg.easyhaproxy.definitions            | A Comma delimited list with the definitions. Each name requires the definition of the parameters below. |
| com.byjg.easyhaproxy.port.<definition>      | What is the port that the HAProxy will listen to.                                                       |
| com.byjg.easyhaproxy.localport.<definition> | What is the port that the container is listening.                                                       |
| com.byjg.easyhaproxy.host.<definition>      | What is the host that the HAProxy will listen to. (Defaults to 80)                                      |
| com.byjg.easyhaproxy.redirect.<definition>  | Host redirects from connections in the port defined above.                                              |
| com.byjg.easyhaproxy.sslcert.<definition>   | Cert PEM Base64 encoded.                                                                                |

E.g.

```
docker run \
    -l com.byjg.easyhaproxy.definitions=http \
    -l com.byjg.easyhaproxy.port.http=80\
    -l com.byjg.easyhaproxy.host.http=byjg.com.br \
    ....
```

## Redirect Example:

```text
www.byjg.com.br=>http://byjg.com.br,byjg.com=>http://byjg.com.br
```

# Mapping custom .cfg files

Just create a folder and put files with the extension .cfg. and map the volume to the container. 
This will concatenate your config into the main haproxy.cfg

```bash
docker run \ 
    /* other parameters */
    -v /your/local/conf.d:/etc/haproxy/conf.d \
    -d byjg/easy-haproxy
```

Check if your config is ok:

```bash
docker run \ 
    /* other parameters */
    -v /your/local/conf.d:/etc/haproxy/conf.d \
    -byjg/easy-haproxy -c -f /etc/haproxy/haproxy.cfg
```

# Docker Compose

```yaml
version: "3.4"
services:
  front:
    image: byjg/easy-haproxy
    volume:
      - /path/to/local:/etc/easyconfig
    ports:
      - 80:80
      - 8080:8080
      - 1936:1936
```

# Handling SSL

HaProxy can handle SSL for you. in this case add the parameter pointing to file containing
the pem of certificates and key in only one file:

```
  - port: 443
    ssl_cert: /etc/easyconfig/mycert.pem
    hosts:
      host1.com.br: container:80
```

Important: Different certificates need to be handled in different entries. 

# Setting Custom Errors

Map the volume : `/etc/haproxy/errors-custom/` and put a file named `ERROR_NUMBER.http` where ERROR_NUMBER
is the http error code (e.g. 503.http)  

# Build

```
docker build -t byjg/easy-haproxy .
```



# Docker Swarm


# AWS

Easy HAProxy will try to get tasks from the tasks running in the CLUSTER. 
It is important that easy haproxy run in the ECS Cluster and can connect to the containers.  

   
You'll have to pass also the `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` or setup a role in the instance in order and 
the `ECS_CLUSTER` with the arn of the cluster


