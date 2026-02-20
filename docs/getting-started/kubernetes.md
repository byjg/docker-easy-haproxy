---
sidebar_position: 1
sidebar_label: "Kubernetes"
---

# Kubernetes

EasyHAProxy acts as an Ingress controller for Kubernetes — it watches Ingress resources with `ingressClassName: easyhaproxy` and configures HAProxy automatically.

:::info How it works
EasyHAProxy queries all ingress definitions with either the
`spec.ingressClassName: easyhaproxy` field (recommended) or the deprecated annotation
`kubernetes.io/ingress.class: easyhaproxy-ingress` (for backward compatibility).
:::

## Deployment Modes

Choose the deployment mode that fits your infrastructure:

| Mode      | Workload   | Exposed Ports          | Node Label | Recommended When              |
|-----------|------------|------------------------|------------|-------------------------------|
| NodePort  | Deployment | 31080 / 31443 / 31936  | No         | Most setups **(recommended)** |
| ClusterIP | Deployment | cluster-internal only  | No         | Behind a LoadBalancer **(recommended)** |
| DaemonSet | DaemonSet  | 80 / 443 / 1936 (host) | Yes        | Bare-metal, special cases     |

**NodePort** and **ClusterIP** run as a Deployment — no node label needed, and they survive node replacements safely.

**DaemonSet** binds to host ports and requires a node label (`easyhaproxy/node=master`) via `nodeAffinity`. The label must be manually reapplied after any node replacement, which can cause outages. Use only for bare-metal or special-case setups.

EasyHAProxy detects its deployment mode automatically (`EASYHAPROXY_DEPLOYMENT_MODE=auto`). See the [environment variable reference](../reference/environment-variables.md#kubernetes) for manual override options.

## Step 1 — Install EasyHAProxy

```bash
kubectl create namespace easyhaproxy
```

### NodePort (recommended)

Exposes HAProxy on NodePort `31080` (HTTP), `31443` (HTTPS), and `31936` (stats). Point your DNS or external load balancer to any node IP on these ports.

```bash
kubectl apply -f \
    https://raw.githubusercontent.com/byjg/docker-easy-haproxy/6.0.0/deploy/kubernetes/easyhaproxy-nodeport.yml
```

### ClusterIP (behind a LoadBalancer)

Cluster-internal only. Pair with an external cloud LoadBalancer or `kubectl port-forward` for local testing.

```bash
kubectl apply -f \
    https://raw.githubusercontent.com/byjg/docker-easy-haproxy/6.0.0/deploy/kubernetes/easyhaproxy-clusterip.yml
```

### DaemonSet (special cases — requires node label)

:::warning Requires node label maintenance
The node label must be reapplied after any node replacement. Failing to do so will cause an outage.
:::

```bash
# Label the target node first
kubectl label nodes node-01 "easyhaproxy/node=master"

kubectl apply -f \
    https://raw.githubusercontent.com/byjg/docker-easy-haproxy/6.0.0/deploy/kubernetes/easyhaproxy-daemonset.yml
```

If you need to configure environment variables (log levels, stats password, etc.), see the [environment variable reference](../reference/environment-variables.md).

## Step 2 — Create an Ingress

```yaml
kind: Ingress
metadata:
  name: example-ingress
  namespace: example
spec:
  ingressClassName: easyhaproxy
  rules:
  - host: example.org
    http:
      paths:
      - backend:
          service:
            name: example-service
            port:
              number: 8080
        pathType: ImplementationSpecific
```

EasyHAProxy routes traffic from `example.org:80` to your service at port 8080. No container port exposure needed.

:::note Backward Compatibility
The deprecated annotation `kubernetes.io/ingress.class: easyhaproxy-ingress` is still supported but `spec.ingressClassName` is recommended for new deployments.
:::

## Step 3 — Verify

```bash
curl http://example.org
```

---

## Kubernetes Annotations

Customize EasyHAProxy behavior per-ingress using annotations. For the full annotations reference, see [Container Labels — Kubernetes Ingress Annotations](../reference/container-labels.md#kubernetes-ingress-annotations).

**Important**: Annotations apply to all hosts in the ingress configuration.

## Using Plugins

Add the `easyhaproxy.plugins` annotation with a comma-separated list of plugin names:

```yaml
metadata:
  annotations:
    easyhaproxy.plugins: "cloudflare,deny_pages"
    easyhaproxy.plugin.deny_pages.paths: "/wp-admin,/wp-login.php"
    easyhaproxy.plugin.deny_pages.status_code: "404"
```

For full plugin documentation, see the [Using Plugins](../guides/plugins.md) guide.

## Loading Plugin Configuration from Kubernetes Secrets

EasyHAProxy supports loading sensitive plugin configuration values from Kubernetes Secrets using the `k8s_secret` pattern:

```yaml
# Auto-detect key (tries common variations):
easyhaproxy.plugin.{plugin_name}.k8s_secret.{config_key}: "secret_name"

# Explicit key (no variations):
easyhaproxy.plugin.{plugin_name}.k8s_secret.{config_key}: "secret_name/key_name"
```

### How It Works

1. You create a Kubernetes Secret with your sensitive data
2. You reference the secret in your ingress annotation using the `k8s_secret` pattern
3. EasyHAProxy reads the secret from the same namespace as the ingress
4. EasyHAProxy transforms the annotation to inject the secret value
5. The plugin receives the value as if it was provided directly in the annotation

### Complete Example

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: jwt-pubkey-secret
  namespace: production
type: Opaque
stringData:
  pubkey: |
    -----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
    -----END PUBLIC KEY-----

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: production
  annotations:
    easyhaproxy.plugins: "jwt_validator"
    easyhaproxy.plugin.jwt_validator.algorithm: "RS256"
    easyhaproxy.plugin.jwt_validator.issuer: "https://auth.example.com/"
    easyhaproxy.plugin.jwt_validator.audience: "https://api.example.com"
    easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "jwt-pubkey-secret"
spec:
  ingressClassName: easyhaproxy
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 8080
```

### Priority Order

1. **Explicit annotation** (e.g., `easyhaproxy.plugin.jwt_validator.pubkey: "value"`)
2. **k8s_secret annotation** (e.g., `easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "secret"`)

### Security Considerations

- Secrets are read from the **same namespace** as the ingress (no cross-namespace access)
- EasyHAProxy needs RBAC permissions to read secrets (included in default deployment)
- Use Kubernetes RBAC to control which service accounts can read which secrets

## ACME / Let's Encrypt

Add the `easyhaproxy.certbot` annotation to enable automatic certificate issuing:

```yaml
kind: Ingress
metadata:
  annotations:
    easyhaproxy.certbot: 'true'
  name: example-ingress
  namespace: example
spec:
  ingressClassName: easyhaproxy
```

More info in the [ACME guide](../guides/acme.md). Make sure ports 80 and 443 are publicly reachable.

## Custom SSL Certificates

Create a secret with your certificate and key and associate it with your ingress:

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: host2-tls
  namespace: default
data:
  tls.crt: base64 of your certificate
  tls.key: base64 of your certificate private key
type: kubernetes.io/tls

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-example
  namespace: default
spec:
  ingressClassName: easyhaproxy
  tls:
  - hosts:
      - host2.local
    secretName: host2-tls
  rules:
    ...
```

## Important Limitations

- The implementation doesn't support all ingress properties or wildcard domains.
- EasyHAProxy reads all `spec.rules[].host` values but parses only the **first path** per rule.

----
[Open source ByJG](http://opensource.byjg.com)
