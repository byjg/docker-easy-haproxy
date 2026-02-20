---
sidebar_position: 3
sidebar_label: "Docker"
---

# Docker

EasyHAProxy inspects running Docker containers, reads their labels, and configures HAProxy automatically.

:::warning Limitations
- You cannot mix Docker containers with Swarm containers.
- This method does not work with containers that use the `--network=host` option. See [limitations](../concepts/limitations.md) for details.
:::

## Step 1 — Create a shared network

```bash
docker network create easyhaproxy
```

It's recommended to use an external network so EasyHAProxy and your app containers can communicate.

## Step 2 — Run EasyHAProxy

```bash
docker run -d \
      --name easy-haproxy-container \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -e EASYHAPROXY_DISCOVER="docker" \
      -p 80:80 \
      -p 443:443 \
      -p 1936:1936 \
      --network easyhaproxy \
    byjg/easy-haproxy
```

Mounting `/var/run/docker.sock` is required so EasyHAProxy can query the Docker API.

## Step 3 — Label your container

```bash
docker run -d \
      --label easyhaproxy.http.host=example.org \
      --label easyhaproxy.http.port=80 \
      --label easyhaproxy.http.localport=8080 \
      --network easyhaproxy \
    my/image:tag
```

EasyHAProxy detects this container automatically and routes traffic from `example.org:80` to port 8080 in your container. You do not need to expose any container ports.

## Step 4 — Verify

Open `http://example.org` in your browser (or `curl http://example.org`). Traffic should reach your container.

---

## Full options

- [Container label reference](../reference/container-labels.md) — all available labels
- [Environment variable reference](../reference/environment-variables.md) — configure EasyHAProxy behavior
- [SSL certificates](../guides/ssl.md) — add custom TLS
- [ACME / Let's Encrypt](../guides/acme.md) — automatic certificate issuing

----
[Open source ByJG](http://opensource.byjg.com)
