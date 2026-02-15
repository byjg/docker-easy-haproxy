---
sidebar_position: 22
---

# Other configurations

## Exposing Ports

Some ports on the EasyHAProxy container and in the firewall are required to be open. However, you don't need to expose the other container ports because EasyHAProxy will handle that.

- The ports `80` and `443`.
- If you enable the HAProxy statistics, you must also expose the port defined in `HAPROXY_STATS_PORT` environment variable (default 1936). Statistics are only generated when you set `HAPROXY_PASSWORD`.
- Every port defined in `easyhaproxy.[definitions].port` also should be exposed. 

For example:

```bash title="Expose required ports"
docker run \
    /* other parameters */
    -p 80:80 \
    -p 443:443 \
    -p 1936:1936 \
    -d byjg/easy-haproxy
```

## Mapping Docker Volume

The docker volume or a way to call the API needs to pass to the EasyHAProxy container.

```bash title="Mount Docker socket"
docker run \
    /* other parameters */
    -v /var/run/docker.sock:/var/run/docker.sock \
    -d byjg/easy-haproxy
```

## Mapping custom .cfg files

You can concatenate valid HAProxy `.cfg` files to the dynamically generated `haproxy.cfg` by mapping the folder `/etc/easyhaproxy/haproxy/conf.d`.

```bash title="Mount custom config directory"
docker run \
    /* other parameters */
    -v /your/local/conf.d:/etc/easyhaproxy/haproxy/conf.d \
    -d byjg/easy-haproxy
```

## Setting Custom Errors

If enabled, map the volume : `/etc/easyhaproxy/haproxy/errors-custom/` to your container and put a file named `ERROR_NUMBER.http`
where ERROR_NUMBER is the HTTP error code (e.g., `503.http`)

----
[Open source ByJG](http://opensource.byjg.com)
