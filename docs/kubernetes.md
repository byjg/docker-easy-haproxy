---
sidebar_position: 1
---

# Kubernetes

## Setup Kubernetes EasyHAProxy

:::info How it works
EasyHAProxy for Kubernetes operates by querying all ingress definitions with the annotation
`kubernetes.io/ingress.class: easyhaproxy-ingress`. Upon finding this annotation,
EasyHAProxy immediately sets up HAProxy and begins serving traffic.
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
    https://raw.githubusercontent.com/byjg/docker-easy-haproxy/4.6.0/deploy/kubernetes/easyhaproxy-daemonset.yml
```

If necessary, you can configure environment variables. To get a list of the variables, please follow the [environment variable guide](environment-variable.md)

## Running containers

Your container only requires creating an ingress with the annotation `kubernetes.io/ingress.class: easyhaproxy-ingress` pointing to your service.

e.g.

```yaml
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
  name: example-ingress
  namespace: example
spec:
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
| kubernetes.io/ingress.class         | (required) Activate EasyHAProxy.                                                    | **required** | easyhaproxy-ingress        |
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
    kubernetes.io/ingress.class: easyhaproxy-ingress
    easyhaproxy.plugins: "cloudflare,deny_pages"
  name: example-ingress
  namespace: example
spec:
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
    kubernetes.io/ingress.class: easyhaproxy-ingress
    easyhaproxy.plugins: "deny_pages"
    easyhaproxy.plugin.deny_pages.paths: "/admin,/private,/config"
    easyhaproxy.plugin.deny_pages.status_code: "403"
  name: secure-app-ingress
  namespace: production
spec:
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
    kubernetes.io/ingress.class: easyhaproxy-ingress
    easyhaproxy.plugins: "jwt_validator"
    easyhaproxy.plugin.jwt_validator.algorithm: "RS256"
    easyhaproxy.plugin.jwt_validator.issuer: "https://auth.example.com/"
    easyhaproxy.plugin.jwt_validator.audience: "https://api.example.com"
    easyhaproxy.plugin.jwt_validator.pubkey_path: "/etc/haproxy/jwt_keys/api_pubkey.pem"
```

**Note:** For JWT validation, you'll need to mount the public key file into the EasyHAProxy pod. See [Using Plugins](plugins.md#protect-api-with-jwt-authentication) for details.

**Restrict access to specific IPs:**

```yaml
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
    easyhaproxy.plugins: "ip_whitelist"
    easyhaproxy.plugin.ip_whitelist.allowed_ips: "192.168.1.0/24,10.0.0.5"
    easyhaproxy.plugin.ip_whitelist.status_code: "403"
```

**Restore Cloudflare visitor IPs:**

```yaml
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
    easyhaproxy.plugins: "cloudflare"
```

**Multiple plugins together:**

```yaml
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
    easyhaproxy.plugins: "cloudflare,deny_pages"
    easyhaproxy.plugin.deny_pages.paths: "/wp-admin,/wp-login.php"
    easyhaproxy.plugin.deny_pages.status_code: "404"
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

## Certbot / ACME / Letsencrypt

It is necessary add the annotation `easyhaproxy.certbot` to the ingress configuration:

```yaml
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
    easyhaproxy.certbot: 'true'
  name: example-ingress
  namespace: example
spec:
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
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
  name: tls-example
  namespace: default
spec:
  tls:
  - hosts:
      - host2.local
    secretName: host2-tls
  rules:
    ...
```

----
[Open source ByJG](http://opensource.byjg.com)
