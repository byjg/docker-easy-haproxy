---
sidebar_position: 4
sidebar_label: "Static YAML"
---

# Static YAML

Use this mode to configure EasyHAProxy from a hand-written YAML file. Works for any backend — Docker containers, VMs, bare-metal servers, or anything reachable by IP/hostname.

:::tip Live Reload
EasyHAProxy monitors this file for changes and automatically reconfigures HAProxy when any changes are detected.
:::

## Step 1 — Write a minimal config file

```yaml
containers:
  "myapp.example.com:80":
    ip: ["10.0.0.5:3000"]
```

Save this as `config.yml`.

## Step 2 — Run EasyHAProxy

```bash
docker run -d \
      --name easy-haproxy-container \
      -v /my/static/:/etc/easyhaproxy/static/ \
      -e EASYHAPROXY_DISCOVER="static" \
      -p 80:80 \
      -p 443:443 \
      -p 1936:1936 \
    byjg/easy-haproxy
```

:::tip Docker Socket Optional
Mounting `/var/run/docker.sock` is not required in static discovery mode.
:::

## Step 3 — Verify

```bash
curl http://myapp.example.com
```

---

## Full YAML reference

```yaml
stats:
  username: admin     # Optional (default "admin")
  password: password  # If omitted, stats are public with no password
  port: 1936          # Optional (default 1936)

customerrors: true   # Optional (default false)

ssl_mode: default    # Optional

logLevel:
  certbot: DEBUG       # Optional. Can be: TRACE,DEBUG,INFO,WARN,ERROR,FATAL
  easyhaproxy: DEBUG   # Optional. Can be: TRACE,DEBUG,INFO,WARN,ERROR,FATAL
  haproxy: INFO        # Optional. Can be: TRACE,DEBUG,INFO,WARN,ERROR,FATAL

certbot:
  email: "acme@example.org"  # If set, enables ACME/Certbot
  autoconfig: ""             # Well-known CA shorthand (e.g. letsencrypt)
  eab_hmac_key: ""           # Required by some CAs
  eab_kid: ""                # Required by some CAs
  server: False              # ACME endpoint URL (or False for Let's Encrypt)
  retry_count: 60            # Retry after rate limit

containers:
  # Format: "hostname:port"
  "host1.com.br:80":
    ip: ["container:5000"]   # Endpoints: "address:localport"
    certbot: true            # Request certbot certificate
    redirect_ssl: true       # Redirect HTTP to HTTPS
    mode: http               # Default `http`. Can be http or tcp

  # HTTPS version (SSL)
  "host1.com.br:443":
    ip: ["container:80"]
    ssl: true                # Enable SSL for this port

  # Redirect www → main domain
  "www.host1.com.br:80":
    ip: ["container:5000"]
    redirect_ssl: true
```

:::note SSL Certificates in Static Mode
The only way to provide SSL certificates in static configuration mode is to map the certificate files as a Docker volume. See the [SSL documentation](../guides/ssl.md) to learn how to configure this.
:::

---

## Full options

- [Container label reference](../reference/container-labels.md) — label semantics also apply to static YAML keys
- [Environment variable reference](../reference/environment-variables.md) — configure EasyHAProxy behavior

----
[Open source ByJG](http://opensource.byjg.com)
