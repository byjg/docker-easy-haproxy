---
sidebar_position: 5
---

# Install via pip / uv

EasyHAProxy can run directly on any Linux or macOS host without Docker, using the `easyhaproxy` Python package.

## Prerequisites

HAProxy must be installed and available in your system `PATH` before running `easy-haproxy`. EasyHAProxy will refuse to start with a clear error message if HAProxy is not found.

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
  <TabItem value="debian" label="Debian / Ubuntu" default>

```bash
sudo apt install haproxy
```

  </TabItem>
  <TabItem value="rhel" label="RHEL / Fedora">

```bash
sudo dnf install haproxy
```

  </TabItem>
  <TabItem value="macos" label="macOS">

```bash
brew install haproxy
```

  </TabItem>
</Tabs>

## Installation

### Recommended: `uv tool` (system-wide, isolated)

[`uv`](https://docs.astral.sh/uv/) installs `easyhaproxy` into its own isolated environment and exposes the `easy-haproxy` binary in `~/.local/bin/`, similar to `pipx`.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install easyhaproxy as a tool
uv tool install easyhaproxy

# Make sure ~/.local/bin is in PATH (one-time setup)
uv tool update-shell
```

After installation:

```bash
easy-haproxy --help
```

### Alternative: `pip`

```bash
pip install easyhaproxy
```

:::note Virtual environments
When installing inside a virtual environment, `easy-haproxy` is only available while the environment is activated. For system-wide use, prefer `uv tool install` or install with `pip` at the system/user level.
:::

## CLI Reference

Every configuration option can be set via a CLI flag **or** an environment variable. CLI flags take precedence over environment variables.

```
easy-haproxy [OPTIONS]
```

### Core

| Flag                     | Environment Variable       | Default                                              | Description                                               |
|--------------------------|----------------------------|------------------------------------------------------|-----------------------------------------------------------|
| `--discover MODE`        | `EASYHAPROXY_DISCOVER`     | **required**                                         | Discovery mode: `static`, `docker`, `swarm`, `kubernetes` |
| `--base-path PATH`       | `EASYHAPROXY_BASE_PATH`    | `/etc/easyhaproxy` (root) `~/easyhaproxy` (non-root) | Base directory for all EasyHAProxy files                  |
| `--label-prefix PREFIX`  | `EASYHAPROXY_LABEL_PREFIX` | `easyhaproxy`                                        | Label/annotation prefix used to discover services         |
| `--ssl-mode MODE`        | `EASYHAPROXY_SSL_MODE`     | `default`                                            | TLS policy: `strict`, `default`, or `loose`               |
| `--refresh-conf SECONDS` | `EASYHAPROXY_REFRESH_CONF` | `10`                                                 | Polling interval for configuration changes                |
| `--customer-errors BOOL` | `HAPROXY_CUSTOMERRORS`     | `false`                                              | Enable custom HAProxy HTML error pages                    |

### Logging

| Flag                        | Environment Variable    | Default  | Description               |
|-----------------------------|-------------------------|----------|---------------------------|
| `--log-level LEVEL`         | `EASYHAPROXY_LOG_LEVEL` | `DEBUG`  | EasyHAProxy log level     |
| `--haproxy-log-level LEVEL` | `HAPROXY_LOG_LEVEL`     | `INFO`   | HAProxy process log level |
| `--certbot-log-level LEVEL` | `CERTBOT_LOG_LEVEL`     | `DEBUG`  | Certbot log level         |

Valid levels: `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`

### Stats Dashboard

| Flag                                 | Environment Variable        | Default      | Description                                 |
|--------------------------------------|-----------------------------|--------------|---------------------------------------------|
| `--haproxy-password PASSWORD`        | `HAPROXY_PASSWORD`          | *(disabled)* | Enable stats dashboard with this password   |
| `--haproxy-username USERNAME`        | `HAPROXY_USERNAME`          | `admin`      | Stats dashboard username                    |
| `--haproxy-stats-port PORT`          | `HAPROXY_STATS_PORT`        | `1936`       | Stats dashboard port                        |
| `--haproxy-stats-cors-origin ORIGIN` | `HAPROXY_STATS_CORS_ORIGIN` | *(none)*     | Allowed CORS origin for the stats dashboard |

:::tip
The stats dashboard is only enabled when `--haproxy-password` (or `HAPROXY_PASSWORD`) is set.
:::

### ACME / Certbot (SSL certificates)

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

See the full [ACME documentation](acme.md) for details.

### Plugins

| Flag                            | Environment Variable                 | Default  | Description                               |
|---------------------------------|--------------------------------------|----------|-------------------------------------------|
| `--plugins-enabled LIST`        | `EASYHAPROXY_PLUGINS_ENABLED`        | *(none)* | Comma-separated list of plugins to enable |
| `--plugins-abort-on-error BOOL` | `EASYHAPROXY_PLUGINS_ABORT_ON_ERROR` | `false`  | Abort startup if a plugin fails to load   |

See the [plugins documentation](plugins.md) for available plugins.

### Kubernetes

| Flag                                       | Environment Variable                 | Default  | Description                                  |
|--------------------------------------------|--------------------------------------|----------|----------------------------------------------|
| `--update-ingress-status BOOL`             | `EASYHAPROXY_UPDATE_INGRESS_STATUS`  | `true`   | Update Ingress status with load-balancer IP  |
| `--deployment-mode MODE`                   | `EASYHAPROXY_DEPLOYMENT_MODE`        | `auto`   | Deployment mode: `auto`, `single`, `cluster` |
| `--external-hostname HOSTNAME`             | `EASYHAPROXY_EXTERNAL_HOSTNAME`      | *(none)* | External hostname reported in Ingress status |
| `--ingress-status-update-interval SECONDS` | `EASYHAPROXY_STATUS_UPDATE_INTERVAL` | `30`     | Interval to update Ingress status            |

## Quick-start examples

### Static mode (bare-metal / VM)

```bash
mkdir -p ~/easyhaproxy/static

cat > ~/easyhaproxy/static/config.yml <<EOF
containers:
  "myapp.example.com:80":
    ip: ["127.0.0.1:3000"]
EOF

easy-haproxy --discover static
```

### Static mode with stats and HTTPS redirect

```bash
easy-haproxy \
  --discover static \
  --haproxy-password mysecret \
  --ssl-mode default \
  --log-level INFO
```

### Let's Encrypt (ACME)

```bash
easy-haproxy \
  --discover static \
  --certbot-email admin@example.com \
  --certbot-autoconfig letsencrypt
```

## Running as a systemd service

To keep `easy-haproxy` running across reboots, create a systemd unit:

```ini title="/etc/systemd/system/easy-haproxy.service"
[Unit]
Description=EasyHAProxy
After=network.target

[Service]
ExecStart=/usr/local/bin/easy-haproxy --discover static --haproxy-password mysecret
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now easy-haproxy
```

:::tip Adjust ExecStart path
Run `which easy-haproxy` to get the correct binary path for `ExecStart`. If you installed with `uv tool`, it is typically `/root/.local/bin/easy-haproxy` when running as root.
:::

----
[Open source ByJG](http://opensource.byjg.com)