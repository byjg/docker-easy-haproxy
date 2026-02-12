---
sidebar_position: 1
---

# Kubernetes

## Setup Kubernetes EasyHAProxy

:::info How it works
EasyHAProxy for Kubernetes operates by querying all ingress definitions with either the
`spec.ingressClassName: easyhaproxy` field (recommended) or the deprecated annotation
`kubernetes.io/ingress.class: easyhaproxy-ingress` (for backward compatibility). Upon finding
a matching ingress class, EasyHAProxy immediately sets up HAProxy and begins serving traffic.
:::

For Kubernetes installations, there are three available installation modes:
- DaemonSet: This mode exposes ports 80, 443, and 1936.
- NodePort: Ports 31080, 31443, and 31936 are exposed.
- ClusterIP: In this mode, no ports are exposed externally, and HAProxy is accessible only 
  within the cluster.

To install EasyHAProxy in your Kubernetes cluster, follow these steps:


### 1) Identify the node where your EasyHAProxy container will run

:::warning Single Node Deployment
EasyHAProxy will be limited to a single node. To understand why, see the [limitations](limitations.md) page.
:::

```bash title="List available nodes"
$ kubectl get nodes

NAME      STATUS   ROLES    AGE    VERSION
node-01   Ready    <none>   561d   v1.21.13-3
node-02   Ready    <none>   561d   v1.21.13-3
```

Add the EasyHAProxy label to the node.

```bash title="Label the node for EasyHAProxy"
kubectl label nodes node-01 "easyhaproxy/node=master"
```

### 2) Install EasyHAProxy with Kubernetes Manifest

```bash title="Install EasyHAProxy"
kubectl create namespace easyhaproxy

kubectl apply -f \
    https://raw.githubusercontent.com/byjg/docker-easy-haproxy/5.0.0/deploy/kubernetes/easyhaproxy-daemonset.yml
```

If necessary, you can configure environment variables. To get a list of the variables, please follow the [environment variable guide](environment-variable.md)

## Running containers

Your container only requires creating an ingress with the `spec.ingressClassName: easyhaproxy` field pointing to your service.

e.g.

```yaml
kind: Ingress
metadata:
  name: example-ingress
  namespace: example
spec:
  # Use ingressClassName (recommended)
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

:::note Backward Compatibility
The deprecated annotation `kubernetes.io/ingress.class: easyhaproxy-ingress` is still supported for backward compatibility, but `spec.ingressClassName` is the recommended approach for new deployments.
:::

Once the container is running, EasyHAProxy will detect automatically and start to redirect all traffic from `example.org:80` to your container at port 8080.

You don't need to expose any port in your container.

:::note Important Limitations
- The implementation doesn't support all ingress properties or wildcard domains at this time.
- The ingress will publish ports 80 and 443, plus 1936 if stats are enabled.
- EasyHAProxy will read all `spec.rules[].host` specifications, however it will parse only the **first path** `spec.rules[].http.paths[0].port.number` for each rule, and ignore the other paths.
:::

## Kubernetes annotations

| annotation                          | Description                                                                         | Default      | Example                    |
|-------------------------------------|-------------------------------------------------------------------------------------|--------------|----------------------------|
| kubernetes.io/ingress.class         | (deprecated) Activate EasyHAProxy. Use `spec.ingressClassName` instead.             | *optional*   | easyhaproxy-ingress        |
| easyhaproxy.redirect_ssl            | (optional) Boolean. Force redirect all endpoints to HTTPS.                          | false        | true or false              |
| easyhaproxy.certbot                 | (optional) Boolean. It will request certbot certificates for the ingresses domains. | false        | true or false              |
| easyhaproxy.redirect                | (optional) JSON. Key pair with a domain and its destination.                        | *empty*      | \{"domain":"redirect_url"} |
| easyhaproxy.mode                    | (optional) Set the HTTP mode for that connection.                                   | http         | http or tcp                |
| easyhaproxy.listen_port             | (optional) Override the HTTP listen port created for that ingress                   | 80           | 8081                       |
| easyhaproxy.plugins                 | (optional) Comma-separated list of plugins to enable for this ingress               | *empty*      | cloudflare,deny_pages      |
| easyhaproxy.plugin.`{name}`.`{key}` | (optional) Plugin-specific configuration (see [Using Plugins](plugins.md))          | *varies*     | See examples below         |

**Important**: The annotations are per ingress and applied to all hosts in that ingress configuration.

## Using Plugins with Kubernetes

Plugins extend HAProxy configuration with additional functionality like JWT validation, IP whitelisting, or Cloudflare IP restoration. For a complete list of available plugins, see the [Using Plugins](plugins.md) guide.

### Enabling Plugins for an Ingress

Add the `easyhaproxy.plugins` annotation with a comma-separated list of plugin names:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    easyhaproxy.plugins: "cloudflare,deny_pages"
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

### Configuring Plugin Options

Use `easyhaproxy.plugin.{plugin_name}.{option}` annotations to configure individual plugins:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    easyhaproxy.plugins: "deny_pages"
    easyhaproxy.plugin.deny_pages.paths: "/admin,/private,/config"
    easyhaproxy.plugin.deny_pages.status_code: "403"
  name: secure-app-ingress
  namespace: production
spec:
  ingressClassName: easyhaproxy
  rules:
  - host: myapp.example.com
    http:
      paths:
      - backend:
          service:
            name: myapp-service
            port:
              number: 8080
        pathType: ImplementationSpecific
```

### Common Plugin Examples

**Protect API with JWT validation:**

```yaml
metadata:
  annotations:
    easyhaproxy.plugins: "jwt_validator"
    easyhaproxy.plugin.jwt_validator.algorithm: "RS256"
    easyhaproxy.plugin.jwt_validator.issuer: "https://auth.example.com/"
    easyhaproxy.plugin.jwt_validator.audience: "https://api.example.com"
    easyhaproxy.plugin.jwt_validator.pubkey_path: "/etc/haproxy/jwt_keys/api_pubkey.pem"
spec:
  ingressClassName: easyhaproxy
```

**Note:** For JWT validation, you'll need to mount the public key file into the EasyHAProxy pod. See [Using Plugins](plugins.md#protect-api-with-jwt-authentication) for details.

**Restrict access to specific IPs:**

```yaml
metadata:
  annotations:
    easyhaproxy.plugins: "ip_whitelist"
    easyhaproxy.plugin.ip_whitelist.allowed_ips: "192.168.1.0/24,10.0.0.5"
    easyhaproxy.plugin.ip_whitelist.status_code: "403"
spec:
  ingressClassName: easyhaproxy
```

**Restore Cloudflare visitor IPs:**

```yaml
metadata:
  annotations:
    easyhaproxy.plugins: "cloudflare"
spec:
  ingressClassName: easyhaproxy
```

**Multiple plugins together:**

```yaml
metadata:
  annotations:
    easyhaproxy.plugins: "cloudflare,deny_pages"
    easyhaproxy.plugin.deny_pages.paths: "/wp-admin,/wp-login.php"
    easyhaproxy.plugin.deny_pages.status_code: "404"
spec:
  ingressClassName: easyhaproxy
```

### Global Plugin Configuration

Some plugins (like `cleanup`) are global and execute once per discovery cycle. Configure these via environment variables or YAML configuration:

**Using Helm values.yaml:**

```yaml
easyhaproxy:
  plugins:
    enabled: cleanup
    config:
      cleanup:
        max_idle_time: 600
```

**Using environment variables:**

```yaml
env:
  - name: EASYHAPROXY_PLUGINS_ENABLED
    value: "cleanup"
  - name: EASYHAPROXY_PLUGIN_CLEANUP_MAX_IDLE_TIME
    value: "600"
```

For more information on plugin types and available plugins, see the [Using Plugins](plugins.md) guide.

## Loading Plugin Configuration from Kubernetes Secrets

EasyHAProxy supports loading sensitive plugin configuration values directly from Kubernetes Secrets using the `k8s_secret` pattern. This is a **generic, plugin-agnostic feature** that works with any plugin.

### Why Use Kubernetes Secrets?

- **Security**: Keep sensitive data (API keys, passwords, certificates) out of annotations
- **Best practices**: Follows Kubernetes conventions for managing sensitive data
- **Simplicity**: No need to mount volumes or ConfigMaps for secret data
- **Encryption**: Secrets are encrypted at rest in etcd

### Annotation Format

```yaml
# Auto-detect key (tries common variations):
easyhaproxy.plugin.{plugin_name}.k8s_secret.{config_key}: "secret_name"

# Explicit key (no variations):
easyhaproxy.plugin.{plugin_name}.k8s_secret.{config_key}: "secret_name/key_name"
```

### How It Works

1. **You create** a Kubernetes Secret with your sensitive data
2. **You reference** the secret in your ingress annotation using the `k8s_secret` pattern
3. **EasyHAProxy reads** the secret from the same namespace as the ingress
4. **EasyHAProxy transforms** the annotation to inject the secret value
5. **The plugin receives** the value as if it was provided directly in the annotation

**Example transformation:**

```yaml
# Input annotation:
easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "my-jwt-secret"

# EasyHAProxy reads the secret and transforms to:
easyhaproxy.plugin.jwt_validator.pubkey: "<base64-encoded-content>"
```

### Auto-Detect vs Explicit Key

#### Auto-Detect Key Format

When you use `"secret_name"` (without `/`), EasyHAProxy tries to find the key automatically:

```yaml
easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "my-jwt-secret"
```

EasyHAProxy will try these keys in order:
1. Exact match: `pubkey`
2. Common variations based on the config key name

**Auto-detect key variations:**

| Config Key | Tries (in order)                      |
|------------|---------------------------------------|
| `pubkey`   | `pubkey`, `public-key`, `jwt.pub`, `tls.crt` |
| `password` | `password`, `pass`, `pwd`             |
| `api_key`  | `api_key`, `apikey`, `api-key`, `key` |

#### Explicit Key Format

When you use `"secret_name/key_name"` (with `/`), EasyHAProxy only tries the exact key name:

```yaml
easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "my-jwt-secret/rsa-public-key"
```

EasyHAProxy will **only** try: `rsa-public-key` (no variations)

**Use explicit key when:**
- Your secret uses a non-standard key name
- You want to be explicit and avoid ambiguity
- Multiple keys exist in the secret

### Complete Example

```yaml
---
# 1. Create a secret with your JWT public key
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
# 2. Reference it in your ingress
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
    # Load pubkey from Kubernetes secret (auto-detect key)
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

### Example with Explicit Key Name

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: app-credentials
  namespace: production
type: Opaque
stringData:
  # Custom key name
  rsa-public-key: |
    -----BEGIN PUBLIC KEY-----
    ...
    -----END PUBLIC KEY-----

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: production
  annotations:
    easyhaproxy.plugins: "jwt_validator"
    # Use explicit key name after the slash
    easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "app-credentials/rsa-public-key"
spec:
  ingressClassName: easyhaproxy
  # ... rest of configuration
```

### Using with Any Plugin

The `k8s_secret` pattern works with **any plugin configuration**:

```yaml
# JWT Validator - load public key
easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "jwt-secret"

# Hypothetical API auth plugin - load API key
easyhaproxy.plugin.api_auth.k8s_secret.api_key: "api-credentials/key"

# Hypothetical basic auth plugin - load password
easyhaproxy.plugin.basic_auth.k8s_secret.password: "auth-secret/pwd"
```

### Priority Order

When multiple configuration methods are used, this is the priority (highest to lowest):

1. **Explicit annotation** (e.g., `easyhaproxy.plugin.jwt_validator.pubkey: "value"`)
2. **k8s_secret annotation** (e.g., `easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "secret"`)

Explicit annotations always take precedence over `k8s_secret` annotations.

### Troubleshooting

**Secret not found:**
```
WARNING: Ingress production/api-ingress - Failed to process k8s_secret annotation
'easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey' with value 'jwt-secret': ...
```
- Verify the secret exists: `kubectl get secret jwt-secret -n production`
- Check the secret is in the same namespace as the ingress

**Key not found in secret:**
```
WARNING: Ingress production/api-ingress - Secret 'jwt-secret' found but no matching
key (tried: pubkey, public-key, jwt.pub, tls.crt)
```
- List secret keys: `kubectl get secret jwt-secret -n production -o jsonpath='{.data}'`
- Use explicit key format: `"jwt-secret/actual-key-name"`

**Check EasyHAProxy logs:**
```bash
kubectl logs -n easyhaproxy -l app=easyhaproxy --tail=100
```

Look for:
- `INFO: Loaded 'pubkey' from secret 'jwt-secret'` (success)
- `WARNING: Secret 'xyz' found but no matching key` (key not found)

### Security Considerations

- Secrets are read from the **same namespace** as the ingress (no cross-namespace access)
- EasyHAProxy needs RBAC permissions to read secrets (included in default deployment)
- Secrets are encrypted at rest in etcd
- Secret values are base64-encoded by Kubernetes automatically
- Use Kubernetes RBAC to control which service accounts can read which secrets

## Certbot / ACME / Letsencrypt

It is necessary to add the annotation `easyhaproxy.certbot` to the ingress configuration:

```yaml
kind: Ingress
metadata:
  annotations:
    easyhaproxy.certbot: 'true'
  name: example-ingress
  namespace: example
spec:
  ingressClassName: easyhaproxy
  ....
```

More info [here](acme.md).

Make sure your cluster is accessible both through ports 80 and 443. 

## Custom SSL Certificates

Create a secret with your certificate and key and associate them with your ingress.

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

----
[Open source ByJG](http://opensource.byjg.com)
