# Kubernetes Examples

This directory contains Kubernetes manifest examples demonstrating EasyHAProxy ingress configurations.

## Prerequisites

1. **EasyHAProxy installed in your cluster:**
   ```bash
   kubectl create namespace easyhaproxy
   kubectl apply -f https://raw.githubusercontent.com/byjg/docker-easy-haproxy/4.6.0/deploy/kubernetes/easyhaproxy-daemonset.yml
   ```

2. **Label the node where EasyHAProxy will run:**
   ```bash
   kubectl label nodes <node-name> "easyhaproxy/node=master"
   ```

See the [Kubernetes Guide](../../docs/kubernetes.md) for complete installation instructions.

---

## Examples Overview

### 1. Basic Ingress (`service.yml`)

**What it demonstrates:**
- Basic ingress configuration
- Multiple domains pointing to same service
- Complete deployment + service + ingress setup

**Components:**
- **Deployment**: `byjg/static-httpserver` container
- **Service**: ClusterIP exposing port 8080
- **Ingress**: Routes for `example.org` and `www.example.org`

**Apply:**
```bash
kubectl apply -f service.yml
```

**Test:**
```bash
# If using NodePort or port-forward:
curl -H "Host: example.org" http://<node-ip>:31080

# Or port-forward for testing:
kubectl port-forward -n easyhaproxy deployment/easyhaproxy 8080:80
curl -H "Host: example.org" http://localhost:8080
```

**Manifest breakdown:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress  # Required!
  name: container-example
spec:
  rules:
  - host: example.org           # First domain
    http:
      paths:
      - backend:
          service:
            name: container-example
            port:
              number: 8080
  - host: www.example.org       # Second domain (same service)
    ...
```

---

### 2. TLS/SSL Ingress (`service_tls.yml`)

**What it demonstrates:**
- HTTPS/TLS configuration
- Custom SSL certificates via Kubernetes secrets
- SSL redirect (HTTP → HTTPS)
- Certbot/Let's Encrypt integration

**Components:**
- **Secret**: Custom SSL certificate for `host2.local`
- **Ingress**: TLS configuration + certbot annotation

**Apply:**
```bash
kubectl apply -f service_tls.yml
```

**Features:**

1. **Custom SSL Certificate:**
   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: host2-tls
   data:
     tls.crt: <base64-encoded-certificate>
     tls.key: <base64-encoded-private-key>
   type: kubernetes.io/tls
   ```

2. **Ingress TLS Configuration:**
   ```yaml
   spec:
     tls:
     - hosts:
         - host2.local
       secretName: host2-tls  # References the secret above
   ```

3. **Certbot/Let's Encrypt:**
   ```yaml
   metadata:
     annotations:
       easyhaproxy.certbot: 'true'
       easyhaproxy.redirect_ssl: 'true'
   ```

**Test:**
```bash
# Test HTTPS (if host2.local in /etc/hosts)
curl -k https://host2.local

# Test HTTP redirect
curl -I http://host2.local
# Should return: HTTP/1.1 301 Moved Permanently
```

---

## Kubernetes Annotations Reference

All annotations are applied at the **Ingress** level and affect all hosts in that ingress.

### Required Annotation

| Annotation                    | Description           | Example               |
|-------------------------------|-----------------------|-----------------------|
| `kubernetes.io/ingress.class` | Activates EasyHAProxy | `easyhaproxy-ingress` |

### Optional Annotations

| Annotation                 | Description          | Default | Example                 |
|----------------------------|----------------------|---------|-------------------------|
| `easyhaproxy.redirect_ssl` | Force HTTPS redirect | `false` | `'true'`                |
| `easyhaproxy.certbot`      | Enable Let's Encrypt | `false` | `'true'`                |
| `easyhaproxy.mode`         | Protocol mode        | `http`  | `http` or `tcp`         |
| `easyhaproxy.listen_port`  | Override listen port | `80`    | `8080`                  |
| `easyhaproxy.plugins`      | Enable plugins       | -       | `cloudflare,deny_pages` |

See [Kubernetes Guide](../../docs/kubernetes.md#kubernetes-annotations) for complete reference.

---

## Common Use Cases

### Use Case 1: Simple HTTP Application

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
  name: my-app
spec:
  rules:
  - host: myapp.example.com
    http:
      paths:
      - backend:
          service:
            name: my-app-service
            port:
              number: 8080
        pathType: ImplementationSpecific
```

### Use Case 2: HTTPS with Let's Encrypt

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
    easyhaproxy.certbot: 'true'
    easyhaproxy.redirect_ssl: 'true'
  name: secure-app
spec:
  rules:
  - host: secure.example.com
    http:
      paths:
      - backend:
          service:
            name: secure-app-service
            port:
              number: 8080
        pathType: ImplementationSpecific
```

**Requirements for Let's Encrypt:**
- Cluster must be publicly accessible on ports 80 and 443
- DNS must point to cluster IP
- Configure certbot email:
  ```bash
  # Via Helm:
  helm upgrade ingress byjg/easyhaproxy \
    --set easyhaproxy.certbot.email=your-email@example.com

  # Or via environment variable in manifest
  ```

### Use Case 3: Custom SSL Certificate

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: my-tls-secret
type: kubernetes.io/tls
data:
  tls.crt: LS0tLS1CRUdJTi...  # base64 encoded certificate
  tls.key: LS0tLS1CRUdJTi...  # base64 encoded private key

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
  name: custom-ssl-app
spec:
  tls:
  - hosts:
      - myapp.example.com
    secretName: my-tls-secret
  rules:
  - host: myapp.example.com
    http:
      paths:
      - backend:
          service:
            name: my-app-service
            port:
              number: 8080
        pathType: ImplementationSpecific
```

### Use Case 4: Using Plugins (JWT, IP Whitelist, etc.)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
    # Enable plugins
    easyhaproxy.plugins: "jwt_validator,deny_pages"
    # Configure JWT validator
    easyhaproxy.plugin.jwt_validator.algorithm: "RS256"
    easyhaproxy.plugin.jwt_validator.issuer: "https://auth.example.com/"
    easyhaproxy.plugin.jwt_validator.audience: "https://api.example.com"
    easyhaproxy.plugin.jwt_validator.pubkey_path: "/etc/haproxy/jwt_keys/api_pubkey.pem"
    # Configure deny_pages
    easyhaproxy.plugin.deny_pages.paths: "/admin,/private"
  name: secure-api
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - backend:
          service:
            name: api-service
            port:
              number: 8080
        pathType: ImplementationSpecific
```

See [Using Plugins with Kubernetes](../../docs/kubernetes.md#using-plugins-with-kubernetes) for more examples.

---

## Creating SSL Secrets

### From Certificate Files

```bash
kubectl create secret tls my-tls-secret \
  --cert=path/to/cert.crt \
  --key=path/to/cert.key \
  -n default
```

### From PEM File

```bash
# Extract certificate and key
openssl x509 -in cert.pem -out cert.crt
openssl rsa -in cert.pem -out cert.key

# Create secret
kubectl create secret tls my-tls-secret \
  --cert=cert.crt \
  --key=cert.key \
  -n default
```

### Generate Self-Signed Certificate for Testing

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=myapp.example.com"

kubectl create secret tls my-tls-secret \
  --cert=tls.crt \
  --key=tls.key
```

---

## Troubleshooting

### Ingress Not Detected

**Check annotation:**
```bash
kubectl get ingress <name> -o yaml | grep annotations -A 5
```

Ensure `kubernetes.io/ingress.class: easyhaproxy-ingress` is present.

**Check EasyHAProxy logs:**
```bash
kubectl logs -n easyhaproxy deployment/easyhaproxy -f
```

### SSL Certificate Not Loading

**Verify secret exists:**
```bash
kubectl get secret <secret-name> -o yaml
```

**Check secret has correct fields:**
- `tls.crt`: base64-encoded certificate
- `tls.key`: base64-encoded private key

**Check EasyHAProxy logs** for certificate loading errors.

### Let's Encrypt Fails

**Requirements:**
- Ports 80 and 443 must be publicly accessible
- DNS must resolve to cluster IP
- Certbot email must be configured

**Check certbot logs:**
```bash
kubectl logs -n easyhaproxy deployment/easyhaproxy | grep certbot
```

### Changes Not Applied

EasyHAProxy watches ingress changes automatically. If changes aren't applied:

1. **Check discovery interval:**
   ```bash
   # Default is 10 seconds, increase if needed
   EASYHAPROXY_REFRESH: "30"
   ```

2. **Force reload:**
   ```bash
   kubectl rollout restart -n easyhaproxy deployment/easyhaproxy
   ```

---

## Tips

1. **Local Testing:**
   Add entries to `/etc/hosts`:
   ```
   <node-ip> example.org www.example.org host2.local
   ```

2. **View HAProxy Config:**
   ```bash
   kubectl exec -n easyhaproxy deployment/easyhaproxy -- cat /etc/haproxy/haproxy.cfg
   ```

3. **Access Stats Interface:**
   ```bash
   kubectl port-forward -n easyhaproxy deployment/easyhaproxy 1936:1936
   # Open: http://localhost:1936
   ```

4. **Debug Mode:**
   Enable debug logging:
   ```yaml
   env:
     - name: EASYHAPROXY_LOG_LEVEL
       value: DEBUG
   ```

---

## Further Reading

- [Kubernetes Installation Guide](../../docs/kubernetes.md)
- [Helm Installation](../../docs/helm.md)
- [Using Plugins with Kubernetes](../../docs/kubernetes.md#using-plugins-with-kubernetes)
- [ACME/Let's Encrypt](../../docs/acme.md)
- [Environment Variables](../../docs/environment-variable.md)
