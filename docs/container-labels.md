---
sidebar_position: 11
---

# Container Labels

## Container (Docker or Swarm) labels

| Tag                                   | Description                                                                                                                                         | Default      | Example                                                                                                          |
|---------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------------------------------------------------------------------------------------------------------------|
| easyhaproxy.[definition].host         | Host(s) HAProxy is listening. More than one host use comma as delimiter                                                                             | **required** | somehost.com OR host1.com,host2.com                                                                              |
| easyhaproxy.[definition].mode         | (Optional) Is this `http` or `tcp` mode in HAProxy.                                                                                                 | http         | http or tcp                                                                                                      |
| easyhaproxy.[definition].port         | (Optional) Port HAProxy will listen for the host.                                                                                                   | 80           | 3000                                                                                                             |
| easyhaproxy.[definition].localport    | (Optional) Port container is listening.                                                                                                             | 80           | 8080                                                                                                             |
| easyhaproxy.[definition].redirect     | (Optional) JSON containing key/value pair from host/to URL redirect.                                                                                | *empty*      | \{"foo.com":"https://bla.com", "bar.com":"https://bar.org"}                                                      |
| easyhaproxy.[definition].sslcert      | (Optional) Cert PEM Base64 encoded. Do not use this if `certbot` is enabled.                                                                        | *empty*      | base64 cert + key                                                                                                |
| easyhaproxy.[definition].ssl          | (Optional) If `true` you need to provide certificate as a file. See below. Do not use with `sslcert`.                                               | false        | true or false                                                                                                    |
| easyhaproxy.[definition].ssl-check    | (Optional) `ssl`, enable health check via SSL in `mode tcp`                                                                                         | *empty*      | ssl                                                                                                              |
| easyhaproxy.[definition].certbot      | (Optional) Generate certificate with certbot. Do not use with `sslcert` parameter. More info [here](acme.md).                                       | false        | true OR false                                                                                                    |
| easyhaproxy.[definition].redirect_ssl | (Optional) Redirect all requests to https                                                                                                           | false        | true OR false                                                                                                    |
| easyhaproxy.[definition].clone_to_ssl | (Optional) It copies the configuration to HTTPS(443) and disable SSL from the current config. **Do not use* this with `ssl` or `certbot` parameters | false        | true OR false                                                                                                    |
| easyhaproxy.[definition].balance      | (Optional) HAProxy balance algorithm. See [HAProxy documentation](https://cbonte.github.io/haproxy-dconv/1.8/configuration.html#4.2-balance)        | roundrobin   | roundrobin, source, uri, url_param, hdr, rdp-cookie, leastconn, first, static-rr, rdp-cookie, hdr_dom, map-based |

The `definition` is a string that will group all configurations togethers. Different `definition` will create different configurations.

The container can have more than one definition.

## Configuations

### Single Definition

```bash
docker run \
    --label easyhaproxy.webapi.port=80\
    --label easyhaproxy.webapi.host=byjg.com.br \
    ....
```

### Multiples Definitions on the same container

```bash
docker run \
    --label easyhaproxy.express.port=80 \
    --label easyhaproxy.express.localport=3000 \
    --label easyhaproxy.express.host=express.byjg.com.br \

    --label easyhaproxy.admin.port=80 \
    --label easyhaproxy.admin.localport=3001 \
    --label easyhaproxy.admin.host=admin.byjg.com.br \
    .... \
    some/myimage
```

### Multiples hosts on the same container

```bash
docker run \
    --label easyhaproxy.express.port=80 \
    --label easyhaproxy.express.localport=3000 \
    --label easyhaproxy.express.host=express.byjg.com.br,admin.byjg.com.br \
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

### TCP Mode

Set `easyhaproxy.[definition].mode=tcp` if your application uses TCP protocol instead of HTTP. 

```bash
docker run \
    --label easyhaproxy.example.mode=tcp \
    --label easyhaproxy.example.port=3306
    --label easyhaproxy.example.localport=3306
    .... \
    some/tcp-service
```

### Redirect Domains

```bash
docker run \
    --label easyhaproxy.[definition].redirect='{"www.byjg.com.br":"http://byjg.com.br","byjg.com":"http://byjg.com.br"}'
```

----
[Open source ByJG](http://opensource.byjg.com)