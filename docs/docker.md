---
sidebar_position: 3
---

# Docker

## Setup Docker EasyHAProxy

This method involves using a standalone Docker installation to discover containers 
and configure HAProxy.

EasyHAProxy inspects Docker containers and retrieves labels to configure HAProxy. 
Once it identifies a container with at least the label 'easyhaproxy.http.host,' 
it configures HAProxy to redirect traffic to that container. 
To accomplish this, EasyHAProxy may need to attach the same network to its container.

It's recommended to create a network external to EasyHAProxy, although it's not mandatory.

:::warning Limitations
- You cannot mix Docker containers with Swarm containers.
- This method does not work with containers that use the `--network=host` option. See [limitations](limitations.md) for details.
:::

For example:

```bash title="Create EasyHAProxy network"
docker network create easyhaproxy
```

And then run the EasyHAProxy:

```bash title="Run EasyHAProxy container"
docker run -d \
      --name easy-haproxy-container \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -e EASYHAPROXY_DISCOVER="docker" \
      # + Environment Variables \
      -p 80:80 \
      -p 443:443 \
      -p 1936:1936 \
      --network easyhaproxy
    byjg/easy-haproxy
```

Mapping to `/var/run/docker.sock` is necessary to discover the docker containers and get the labels;

## Running containers

To make your containers "discoverable" by EasyHAProxy, this is the minimum configuration you need:

```bash title="Run container with EasyHAProxy labels"
docker run -d \
      --label easyhaproxy.http.host=example.org \
      --label easyhaproxy.http.port=80 \
      --label easyhaproxy.http.localport=8080 \
      --network easyhaproxy
    my/image:tag
```

Once the container is running, EasyHAProxy will detect automatically and start to redirect all traffic from `example.org:80` to your container.

You don't need to expose any port in your container.

Please follow the [docker label configuration](container-labels.md) to see other configurations available.

## Setup the EasyHAProxy container

You can configure the behavior of the EasyHAProxy by setup specific environment variables. To get a list of the variables, please follow the [environment variable guide](environment-variable.md)

## Setup certificates with ACME (e.g. Letsencrypt)

Follow [this link](acme.md)

## Setup your own certificates

Follow [this link](ssl.md)

----
[Open source ByJG](http://opensource.byjg.com)
