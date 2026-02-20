---
sidebar_position: 1
sidebar_label: "Concepts"
---

# Concepts

This section explains how EasyHAProxy works under the hood — the mental models that help you understand why things are configured the way they are.

## Service Discovery

EasyHAProxy runs a polling loop every N seconds (default 10, configurable via `EASYHAPROXY_REFRESH_CONF`). On each tick it:

1. **Queries your runtime** — Docker API for containers/services, Kubernetes API for Ingress objects, or reads the static YAML file.
2. **Filters by label/annotation prefix** — only resources that carry the `easyhaproxy` prefix (or your custom `EASYHAPROXY_LABEL_PREFIX`) are considered.
3. **Builds an intermediate structure** — an in-memory list of (host, port, backend) tuples called `easymapping`.
4. **Runs plugins** — global plugins run once; domain plugins run once per host entry.
5. **Renders `haproxy.cfg`** from a Jinja2 template using the `easymapping` data.
6. **Reloads HAProxy** if the rendered config differs from the previous one (zero-downtime reload).

### Discovery mode comparison

| Mode | Source polled | Auth required |
|------|--------------|---------------|
| `docker` | Docker socket `/var/run/docker.sock` | Socket access |
| `swarm` | Docker socket (Swarm API) | Socket access |
| `kubernetes` | Kubernetes API server | RBAC (`get`/`list` on Ingress, Secret) |
| `static` | File on disk | None |

## Configuration Pipeline

```
Labels / Annotations / YAML file
         ↓
  Discovery (Docker / Swarm / K8s / Static)
         ↓
  parsed_object  { IP → label map }
         ↓
  [GLOBAL PLUGINS]  ← executed once
         ↓
  easymapping  [ list of domain configs ]
         ↓
  For each domain:
    [DOMAIN PLUGINS]  ← executed per domain
         ↓
    PluginResult snippets collected
         ↓
  Jinja2 template render → haproxy.cfg
         ↓
  HAProxy reload (if config changed)
```

The key insight: **you never write `haproxy.cfg` by hand**. You express intent through labels/annotations/YAML, and EasyHAProxy translates that into valid HAProxy configuration on every discovery cycle.

## Plugin Execution Model

Plugins are Python classes that implement `PluginInterface`. They are discovered automatically from:

1. `/src/plugins/builtin/` — bundled plugins
2. `/etc/easyhaproxy/plugins/` — your custom plugins

**Two execution types:**

### GLOBAL plugins

- Run **once per discovery cycle**, before any domain processing.
- Receive the full `parsed_object` (all discovered services).
- Use cases: cleanup tasks, global monitoring, DNS updates.
- Example: `cleanup` plugin.

### DOMAIN plugins

- Run **once per discovered domain/host**.
- Receive domain-specific context: domain name, port, label/annotation map.
- Return `PluginResult` containing HAProxy config snippets to inject into the backend section.
- Use cases: IP whitelisting, JWT validation, Cloudflare IP restoration, path blocking.
- Examples: `cloudflare`, `deny_pages`, `jwt_validator`, `ip_whitelist`, `fastcgi`.

**Configuration precedence** (highest to lowest):
1. Container labels / Ingress annotations (per-domain)
2. Static YAML `plugins.config` block
3. Environment variables `EASYHAPROXY_PLUGIN_<NAME>_<KEY>`

See the [Plugin Developer Guide](../guides/plugin-development.md) for how to build your own plugin.

## SSL/TLS Termination Model

SSL termination happens **at HAProxy**, not in your backend containers.

```
Internet → HAProxy (TLS decryption) → Backend container (plain HTTP)
```

Your containers should only serve HTTP on their internal port. HAProxy handles all TLS on ports 80/443.

**Certificate sources** (evaluated in this order for each domain):
1. **ACME/Certbot** — if `certbot=true` label is set, EasyHAProxy runs Certbot HTTP-01 challenge automatically.
2. **Volume-mounted PEM** — files in `/etc/easyhaproxy/certs/haproxy/{domain}.pem`.
3. **Label-embedded PEM** — base64 certificate in the `sslcert` label.

Both ACME and manual certificates can coexist. Per domain, whichever source is configured takes precedence as shown above.

See [SSL setup](../guides/ssl.md) and [ACME/Let's Encrypt](../guides/acme.md) for step-by-step configuration.
