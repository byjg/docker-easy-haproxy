# Docker

## Setup Docker EasyHAProxy

This method will use a docker standalone installation to discover the containers and configure the HAProxy.

You cannot mix docker containers with swarm containers.

The only request is that containers and EasyHAProxy must be in the same docker network.
If you don't add to your services the same network EasyHAProxy is connected to, EasyHAProxy will attach it network to your container.

Also, it is highly recommended you create a network external to EasyHAProxy.

e.g.:

```bash
docker network create easyhaproxy
```

And then run the EasyHAProxy

```bash
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

To make your containers "discoverable" by EasyHAProxy, that is the minimum configuration you need:

```bash
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

You can configure the behavior of the EasyHAProxy by setup specific environment variables. To get a list of the variables, please follow the [docker container environment](docker-environment.md)


## Setup certificates with Letsencrypt

Follow [this link](letsencrypt.md)

## Setup your own certificates

Follow [this link](ssl.md)

----
[Open source ByJG](http://opensource.byjg.com)
