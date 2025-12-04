---
sidebar_position: 2
---

# Swarm

## Setup Docker EasyHAProxy

This method involves using a Docker Swarm installation to discover containers and configure HAProxy.

EasyHAProxy inspects Docker containers within the Swarm and retrieves labels to configure HAProxy. Once it identifies a container with at least the label 'easyhaproxy.http.host,' it configures HAProxy to redirect traffic to that container. To accomplish this, EasyHAProxy may need to attach the same network to its container.

:::tip Docker Swarm Advantages
- **Container Discovery**: Docker Swarm facilitates the discovery of containers within the cluster, streamlining the process of identifying services for HAProxy configuration.
- **Remote Node Management**: Docker Swarm allows for the management of containers across multiple nodes, providing flexibility and scalability in deploying services while ensuring seamless HAProxy configuration across the cluster.
:::

It's recommended to create a network external to EasyHAProxy.

:::warning Limitations
- You cannot mix Docker containers with Swarm containers.
- This method does not work with containers that use the `--network=host` option. See [limitations](limitations.md) for details.
:::

For example:

```bash title="Create overlay network"
docker network create -d overlay --attachable easyhaproxy
```

And then deploy the EasyHAProxy stack:

```yaml
services:
  haproxy:
    image: byjg/easy-haproxy:4.6.0
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

Deploy the stack:

```bash title="Deploy EasyHAProxy stack"
docker stack deploy --compose-file docker-compose.yml easyhaproxy
```

Mapping to `/var/run/docker.sock` is necessary to discover the docker containers and get the labels;

:::danger Single Replica Only
**Do not** add more than one replica for EasyHAProxy. To understand why, see the [limitations](limitations.md) page.
:::

## Running containers

To make your containers "discoverable" by EasyHAProxy, that is the minimum configuration you need:

```yaml
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

Once the container is running, EasyHAProxy will detect automatically and start to redirect all traffic from `example.org:80` to your container.

You don't need to expose any port in your container.

Please follow the [docker label configuration](container-labels.md) to see other configurations available.

## Setup the EasyHAProxy container

You can configure the behavior of the EasyHAProxy by setup specific environment variables. To get a list of the variables, please follow the [environment variable guide](environment-variable.md)

## More information

You can refer to the [Docker Documentation](docker.md) to get other detailed instructions.

----
[Open source ByJG](http://opensource.byjg.com)
