---
sidebar_position: 5
sidebar_label: "Native (pip/uv)"
---

# Native install (pip / uv)

EasyHAProxy can run directly on any Linux or macOS host without Docker, using the `easyhaproxy` Python package. HAProxy is installed on the host; EasyHAProxy manages it.

## Prerequisites

HAProxy must be installed and available in your system `PATH` before running `easy-haproxy`.

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

[`uv`](https://docs.astral.sh/uv/) installs `easyhaproxy` into its own isolated environment and exposes the `easy-haproxy` binary in `~/.local/bin/`.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install easyhaproxy as a tool
uv tool install easyhaproxy

# Make sure ~/.local/bin is in PATH (one-time setup)
uv tool update-shell
```

### Alternative: `pip`

```bash
pip install easyhaproxy
```

:::note Virtual environments
When installing inside a virtual environment, `easy-haproxy` is only available while the environment is activated. For system-wide use, prefer `uv tool install`.
:::

## Quick start

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

### Docker mode

```bash
easy-haproxy --discover docker
```

### Kubernetes mode

```bash
easy-haproxy --discover kubernetes
```

## Running as a systemd service

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
Run `which easy-haproxy` to get the correct binary path. If installed with `uv tool`, it is typically `/root/.local/bin/easy-haproxy` when running as root.
:::

---

## Full options

- [CLI Reference](../reference/cli.md) — all flags and environment variables
- [ACME / Let's Encrypt](../guides/acme.md) — automatic certificate issuing
- [Plugins](../guides/plugins.md) — extend functionality

----
[Open source ByJG](http://opensource.byjg.com)
