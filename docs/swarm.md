# Swarm

## Setup Docker EasyHAProxy

This method will use a docker swarm installation to discover the containers and configure the HAProxy.
The advantage of this method is that you can discover container in other nodes from cluster. 

The only requirement is that containers and EasyHAProxy must be in the same docker swarm network in order to HAProxy be able direct the traffic to the containers.

e.g.:

```bash
docker create network easyhaproxy
```

And then deploy the EasyHAProxy stack:

```yaml
version: "3"

services:
  haproxy:
    image: byjg/easy-haproxy
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    deploy:
      replicas: 1
    environment:
      EASYHAPROXY_DISCOVER: swarm
      EASYHAPROXY_SSL_MODE: "loose"
      HAPROXY_CUSTOMERRORS: "true"
      HAPROXY_USERNAME: admin
      HAPROXY_PASSWORD: password
      HAPROXY_STATS_PORT: 1936
    ports:
      - "80:80/tcp"
      - "443:443/tcp"
      - "1936:1936/tcp"
    networks:
      - easyhaproxy

networks:
  easyhaproxy:
    external: true
```

and then:

```bash
docker stack deploy --compose-file docker-compose.yml easyhaproxy
```

The mapping to `/var/run/docker.sock` is necessary to discover the docker containers and get the labels;

**Do not** add more than one replica for EasyHAProxy. To understand that see [limitations](limitations.md) page.

## Running containers

To make your containers "discoverable" by EasyHAProxy that is minimum configuration you need:

```yaml
version: "3"

services:
  container:
    image: my/image:tag
    deploy:
      replicas: 1
      labels:
        easyhaproxy.http.host: host1.local
        easyhaproxy.http.port: 80
        easyhaproxy.http.localport: 8080
    networks:
      - easyhaproxy

networks:
  easyhaproxy:
    external: true
```

Once the container is running EasyHAProxy will detect automatically and start to redirect all traffic from `example.org:80` to your container.

You don't need to expose any port in your container.

There a list of other parameters you can to configure your container. Please follow the [docker label configuration](container-labels.md)

## Setup the EasyHAProxy container

You can configure the behavior of the EasyHAProxy by setup specific environment variables. To get a list of the variables please follow the [docker container environment](docker-environment.md)

## More information

You can refer the [Docker Documentation](docker.md) to get other detailed instructions.

----
[Open source ByJG](http://opensource.byjg.com)
