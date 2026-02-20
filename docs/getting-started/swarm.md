---
sidebar_position: 2
sidebar_label: "Docker Swarm"
---

# Docker Swarm

EasyHAProxy inspects Docker Swarm services, reads their labels, and configures HAProxy automatically across all nodes.

:::tip Docker Swarm Advantages
- **Container Discovery**: Docker Swarm facilitates the discovery of containers within the cluster.
- **Remote Node Management**: Manage containers across multiple nodes while EasyHAProxy configures HAProxy seamlessly.
:::

:::warning Limitations
- You cannot mix Docker containers with Swarm containers.
- This method does not work with containers that use the `--network=host` option. See [limitations](../concepts/limitations.md) for details.
:::

## Step 1 — Create an overlay network

```bash
docker network create -d overlay --attachable easyhaproxy
```

## Step 2 — Deploy EasyHAProxy as a Swarm stack

```yaml
services:
  haproxy:
    image: byjg/easy-haproxy:6.0.0
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

```bash
docker stack deploy --compose-file docker-compose.yml easyhaproxy
```

:::danger Single Replica Only
**Do not** add more than one replica for EasyHAProxy. To understand why, see the [limitations](../concepts/limitations.md) page.
:::

## Step 3 — Label your service

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

EasyHAProxy detects this service automatically and routes traffic from `host1.local:80` to your container. You do not need to expose any container ports.

## Step 4 — Verify

```bash
curl http://host1.local
```

---

## Full options

- [Container label reference](../reference/container-labels.md) — all available labels
- [Environment variable reference](../reference/environment-variables.md) — configure EasyHAProxy behavior
- [Docker guide](docker.md) — more detailed Docker examples

----
[Open source ByJG](http://opensource.byjg.com)
