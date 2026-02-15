---
sidebar_position: 4
---

# Static File

## Setup Docker EasyHAProxy

This method will use a static configuration, which is simpler and easier than creating a `haproxy.cfg`

You can use this configuration to set up external servers unrelated to docker or Kubernetes.

:::tip Live Reload
EasyHAProxy monitors this file for changes and automatically reconfigures HAProxy when any changes are detected.
:::

First, create a YAML configuration:

```yaml
stats:
  username: admin
  password: password
  port: 1936         # Optional (default 1936)

customerrors: true   # Optional (default false)

ssl_mode: default

logLevel:
  haproxy: INFO

certbot:
  email: "acme@example.org"

containers:
  # HTTP with certbot + redirect to HTTPS
  "host1.com.br:80":
    ip: ["container:5000"]
    certbot: true
    redirect_ssl: true

  # Additional HTTP host
  "host2.com.br:80":
    ip: ["other:3000"]

  # Redirect www → main domain
  "www.host1.com.br:80":
    ip: ["container:5000"]
    redirect_ssl: true

  # HTTPS version
  "host1.com.br:443":
    ip: ["container:80"]
    ssl: true

  # Different host on different port
  "host3.com.br:8080":
    ip: ["domain:8181"]
```

:::info New Configuration Format
The `containers` format simplifies static configuration:
- **Flatter structure**: `"hostname:port"` keys instead of nested `easymapping` → `ports` → `hosts`
- **Better readability**: Port and localport embedded in keys (`"host:port"` and `"container:localport"`)
- **Plugin support**: Global and per-host plugin configuration
- **Clearer mapping**: Format mirrors internal Docker label structure
:::

Then map this file to `/etc/easyhaproxy/static/config.yml` in your EasyHAProxy container:

```bash title="Run EasyHAProxy with static configuration"
docker run -d \
      --name easy-haproxy-container \
      -v /my/static/:/etc/easyhaproxy/static/ \
      -e EASYHAPROXY_DISCOVER="static" \
      # + Environment Variables \
      -p 80:80 \
      -p 443:443 \
      -p 1936:1936 \
      --network easyhaproxy \
    byjg/easy-haproxy
```

:::tip Docker Socket Optional
Mounting `/var/run/docker.sock` is not required in static discovery mode. Add it only if you are simultaneously discovering Docker containers.
:::

You can find other information on [docker label configuration](container-labels.md) and [environment variable guide](environment-variable.md)

## Yaml Definition

```yaml
stats:
  username: admin     # Optional (default "admin")
  password: password  # If stats or stats.password is omitted, stats will be public with no password
  port: 1936          # Optional (default 1936)

customerrors: true   # Optional (default false)

ssl_mode: default    # Optional

logLevel:
  certbot: DEBUG       # Optional (default: DEBUG). Can be: TRACE,DEBUG,INFO,WARN,ERROR,FATAL
  easyhaproxy: DEBUG   # Optional (default: DEBUG). Can be: TRACE,DEBUG,INFO,WARN,ERROR,FATAL
  haproxy: INFO        # Optional (default: INFO). Can be: TRACE,DEBUG,INFO,WARN,ERROR,FATAL

certbot:       
  email: "acme@example.org"  # If email is defined enable ACME/Certbot
  autoconfig: ""             # If empty use letsencrypt, otherwise try to set the CA defined. 
  eab_hmac_key: ""           # If required by the CA, set here.
  eab_kid: ""                # If required by the CA, set here.
  server: False              # If empty/False uses Letsencrypt, otherwise the CA Endpoint defined here
  retry_count: 60            # If the certificate reaches the Rate Limit, try again after 'n' iterations.
}

containers:
  # Format: "hostname:port"
  "host1.com.br:80":
    ip: ["container:5000"]   # Endpoints (ip, dns, container, etc) with format "address:localport"
    certbot: true            # Optional. Request a certbot certificate. Requires certbot.email set.
    redirect_ssl: true       # Optional. Redirect HTTP to HTTPS for this host.
    mode: http               # Optional. Default `http`. Can be http or tcp

  # HTTPS version (SSL)
  "host1.com.br:443":
    ip: ["container:80"]
    ssl: true                # Enable SSL for this port

  # Redirect www → main domain (using redirect_ssl with backend)
  "www.host1.com.br:80":
    ip: ["container:5000"]
    redirect_ssl: true
```

:::note SSL Certificates in Static Mode
The only way to provide SSL certificates in static configuration mode is to map the certificates to EasyHAProxy as a docker volume. Refer to the [SSL documentation](ssl.md) to learn how to configure this.
::: 

----
[Open source ByJG](http://opensource.byjg.com)
