---
sidebar_position: 1
sidebar_label: "CLI Reference"
---

# CLI Reference

The `easy-haproxy` command is the native binary installed via `pip` or `uv`. Every option can be set as a **CLI flag** or an **environment variable**. CLI flags take precedence over environment variables.

```
easy-haproxy [OPTIONS]
```

For installation instructions, see [Native install](../getting-started/native.md).

## Core

| Flag                     | Environment Variable       | Default                                              | Description                                               |
|--------------------------|----------------------------|------------------------------------------------------|-----------------------------------------------------------|
| `--discover MODE`        | `EASYHAPROXY_DISCOVER`     | **required**                                         | Discovery mode: `static`, `docker`, `swarm`, `kubernetes` |
| `--base-path PATH`       | `EASYHAPROXY_BASE_PATH`    | `/etc/easyhaproxy` (root) `~/easyhaproxy` (non-root) | Base directory for all EasyHAProxy files                  |
| `--label-prefix PREFIX`  | `EASYHAPROXY_LABEL_PREFIX` | `easyhaproxy`                                        | Label/annotation prefix used to discover services         |
| `--ssl-mode MODE`        | `EASYHAPROXY_SSL_MODE`     | `default`                                            | TLS policy: `strict`, `default`, or `loose`               |
| `--refresh-conf SECONDS` | `EASYHAPROXY_REFRESH_CONF` | `10`                                                 | Polling interval for configuration changes                |
| `--customer-errors BOOL` | `HAPROXY_CUSTOMERRORS`     | `false`                                              | Enable custom HAProxy HTML error pages                    |

## Logging

| Flag                        | Environment Variable    | Default  | Description               |
|-----------------------------|-------------------------|----------|---------------------------|
| `--log-level LEVEL`         | `EASYHAPROXY_LOG_LEVEL` | `DEBUG`  | EasyHAProxy log level     |
| `--haproxy-log-level LEVEL` | `HAPROXY_LOG_LEVEL`     | `INFO`   | HAProxy process log level |
| `--certbot-log-level LEVEL` | `CERTBOT_LOG_LEVEL`     | `DEBUG`  | Certbot log level         |

Valid levels: `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`

## Stats Dashboard

| Flag                                 | Environment Variable        | Default      | Description                                 |
|--------------------------------------|-----------------------------|--------------|---------------------------------------------|
| `--haproxy-password PASSWORD`        | `HAPROXY_PASSWORD`          | *(disabled)* | Enable stats dashboard with this password   |
| `--haproxy-username USERNAME`        | `HAPROXY_USERNAME`          | `admin`      | Stats dashboard username                    |
| `--haproxy-stats-port PORT`          | `HAPROXY_STATS_PORT`        | `1936`       | Stats dashboard port                        |
| `--haproxy-stats-cors-origin ORIGIN` | `HAPROXY_STATS_CORS_ORIGIN` | *(none)*     | Allowed CORS origin for the stats dashboard |

:::tip
The stats dashboard is only enabled when `--haproxy-password` (or `HAPROXY_PASSWORD`) is set.
:::

## ACME / Certbot (SSL certificates)

| Flag                                  | Environment Variable                       | Default  | Description                                                                                                                                           |
|---------------------------------------|--------------------------------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--certbot-email EMAIL`               | `EASYHAPROXY_CERTBOT_EMAIL`                | *(none)* | Contact email — enables ACME when set                                                                                                                 |
| `--certbot-autoconfig CA`             | `EASYHAPROXY_CERTBOT_AUTOCONFIG`           | *(none)* | Well-known CA shorthand: `letsencrypt`, `letsencrypt_test`, `buypass`, `buypass_test`, `sslcom_rca`, `sslcom_ecc`, `google`, `google_test`, `zerossl` |
| `--certbot-server URL`                | `EASYHAPROXY_CERTBOT_SERVER`               | *(none)* | Custom ACME server directory URL                                                                                                                      |
| `--certbot-eab-kid KID`               | `EASYHAPROXY_CERTBOT_EAB_KID`              | *(none)* | External Account Binding key ID                                                                                                                       |
| `--certbot-eab-hmac-key KEY`          | `EASYHAPROXY_CERTBOT_EAB_HMAC_KEY`         | *(none)* | External Account Binding HMAC key                                                                                                                     |
| `--certbot-retry-count N`             | `EASYHAPROXY_CERTBOT_RETRY_COUNT`          | `60`     | Iterations before retrying after a rate limit                                                                                                         |
| `--certbot-preferred-challenges TYPE` | `EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES` | `http`   | ACME challenge type                                                                                                                                   |
| `--certbot-manual-auth-hook SCRIPT`   | `EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK`     | *(none)* | Path to a manual auth hook script for certbot                                                                                                         |

See the full [ACME documentation](../guides/acme.md) for details.

## Plugins

| Flag                            | Environment Variable                 | Default  | Description                               |
|---------------------------------|--------------------------------------|----------|-------------------------------------------|
| `--plugins-enabled LIST`        | `EASYHAPROXY_PLUGINS_ENABLED`        | *(none)* | Comma-separated list of plugins to enable |
| `--plugins-abort-on-error BOOL` | `EASYHAPROXY_PLUGINS_ABORT_ON_ERROR` | `false`  | Abort startup if a plugin fails to load   |

See the [plugins guide](../guides/plugins.md) for available plugins.

## Kubernetes

| Flag                                       | Environment Variable                 | Default  | Description                                  |
|--------------------------------------------|--------------------------------------|----------|----------------------------------------------|
| `--update-ingress-status BOOL`             | `EASYHAPROXY_UPDATE_INGRESS_STATUS`  | `true`   | Update Ingress status with load-balancer IP  |
| `--deployment-mode MODE`                   | `EASYHAPROXY_DEPLOYMENT_MODE`        | `auto`   | Deployment mode: `auto`, `single`, `cluster` |
| `--external-hostname HOSTNAME`             | `EASYHAPROXY_EXTERNAL_HOSTNAME`      | *(none)* | External hostname reported in Ingress status |
| `--ingress-status-update-interval SECONDS` | `EASYHAPROXY_STATUS_UPDATE_INTERVAL` | `30`     | Interval to update Ingress status            |
