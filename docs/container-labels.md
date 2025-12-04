---
sidebar_position: 11
---

# Container Labels

## Container (Docker or Swarm) labels

| Label                                 | Description                                                                                                                                          | Default      | Example                                                                                                          |
|---------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------------------------------------------------------------------------------------------------------------|
| easyhaproxy.[definition].host         | Host(s) HAProxy is listening. More than one host use comma as delimiter                                                                              | **required** | somehost.com OR host1.com,host2.com                                                                              |
| easyhaproxy.[definition].mode         | (Optional) Is this `http` or `tcp` mode in HAProxy.                                                                                                  | http         | http or tcp                                                                                                      |
| easyhaproxy.[definition].port         | (Optional) Port HAProxy will listen for the host.                                                                                                    | 80           | 3000                                                                                                             |
| easyhaproxy.[definition].localport    | (Optional) Port container is listening.                                                                                                              | 80           | 8080                                                                                                             |
| easyhaproxy.[definition].redirect     | (Optional) JSON containing key/value pair from host/to URL redirect.                                                                                 | *empty*      | \{"foo.com":"https://bla.com", "bar.com":"https://bar.org"}                                                      |
| easyhaproxy.[definition].sslcert      | (Optional) Cert PEM Base64 encoded. Do not use this if `certbot` is enabled.                                                                         | *empty*      | base64 cert + key                                                                                                |
| easyhaproxy.[definition].ssl          | (Optional) If `true` you need to provide certificate as a file. See below. Do not use with `sslcert`.                                                | false        | true or false                                                                                                    |
| easyhaproxy.[definition].ssl-check    | (Optional) `ssl`, enable health check via SSL in `mode tcp`                                                                                          | *empty*      | ssl                                                                                                              |
| easyhaproxy.[definition].certbot      | (Optional) Generate certificate with certbot. Do not use with `sslcert` parameter. More info [here](acme.md).                                        | false        | true OR false                                                                                                    |
| easyhaproxy.[definition].redirect_ssl | (Optional) Redirect all requests to https                                                                                                            | false        | true OR false                                                                                                    |
| easyhaproxy.[definition].clone_to_ssl | (Optional) It copies the configuration to HTTPS(443) and disable SSL from the current config. **Do not use** this with `ssl` or `certbot` parameters | false        | true OR false                                                                                                    |
| easyhaproxy.[definition].balance      | (Optional) HAProxy balance algorithm. See [HAProxy documentation](https://cbonte.github.io/haproxy-dconv/1.8/configuration.html#4.2-balance)         | roundrobin   | roundrobin, source, uri, url_param, hdr, rdp-cookie, leastconn, first, static-rr, rdp-cookie, hdr_dom, map-based |
| easyhaproxy.[definition].proto        | (Optional) Backend server protocol (e.g., fcgi for PHP-FPM, h2 for HTTP/2)                                                                           | *empty*      | fcgi, h2                                                                                                         |
| easyhaproxy.[definition].socket       | (Optional) Unix socket path for backend connection (alternative to host:port)                                                                        | *empty*      | /run/php/php-fpm.sock                                                                                            |

:::info Understanding Definitions
The `[definition]` is a string identifier that groups related configuration labels together. Different definitions create separate HAProxy configurations.

A single container can have multiple definitions to expose different services or ports.
:::

## Configurations

### Single Definition

```bash title="Single service configuration"
docker run \
    --label easyhaproxy.webapi.port=80\
    --label easyhaproxy.webapi.host=byjg.com.br \
    ....
```

### Multiple Definitions on the same container

```bash title="Multiple services on one container"
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

### Multiple hosts on the same container

```bash title="Multiple hosts for one service"
docker run \
    --label easyhaproxy.express.port=80 \
    --label easyhaproxy.express.localport=3000 \
    --label easyhaproxy.express.host=express.byjg.com.br,admin.byjg.com.br \
    .... \
    some/myimage
```

If you are using docker-compose you can use this way:

```yaml
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

```bash title="TCP mode configuration"
docker run \
    --label easyhaproxy.example.mode=tcp \
    --label easyhaproxy.example.port=3306
    --label easyhaproxy.example.localport=3306
    .... \
    some/tcp-service
```

### FastCGI (PHP-FPM) Support

EasyHAProxy supports FastCGI protocol for PHP-FPM and other FastCGI applications.

#### Using Unix Socket

```yaml title="PHP-FPM with Unix socket"
services:
  php-fpm:
    image: php:8.2-fpm
    labels:
      easyhaproxy.fcgi.host: phpapp.local
      easyhaproxy.fcgi.port: 80
      easyhaproxy.fcgi.socket: /run/php/php-fpm.sock
      easyhaproxy.fcgi.proto: fcgi
    volumes:
      - /run/php:/run/php
```

#### Using TCP Connection

```yaml title="PHP-FPM with TCP connection"
services:
  php-fpm:
    image: php:8.2-fpm
    labels:
      easyhaproxy.fcgi.host: phpapp.local
      easyhaproxy.fcgi.port: 80
      easyhaproxy.fcgi.localport: 9000
      easyhaproxy.fcgi.proto: fcgi
```

**Generated HAProxy Configuration:**

```
backend srv_phpapp_local_80
    balance roundrobin
    mode http
    option forwardfor
    http-request set-header X-Forwarded-Port %[dst_port]
    http-request add-header X-Forwarded-Proto https if { ssl_fc }
    server srv-0 /run/php/php-fpm.sock check weight 1 proto fcgi
```

### Redirect Domains

```bash title="Domain redirect configuration"
docker run \
    --label easyhaproxy.[definition].redirect='{"www.byjg.com.br":"http://byjg.com.br","byjg.com":"http://byjg.com.br"}'
```

----
[Open source ByJG](http://opensource.byjg.com)
