---
sidebar_position: 1
sidebar_label: "JWT Validator"
---

# JWT Validator Plugin

**Type:** Domain Plugin
**Runs:** Once for each discovered domain/host

## Overview

The JWT Validator plugin validates JWT (JSON Web Token) authentication tokens using HAProxy's built-in JWT functionality.

## Why Use It

Protect APIs and services with JWT authentication without needing application-level code.

## Generating JWT Keys

```bash
# Generate RSA key pair (idempotent - skips if exists)
[ -f jwt_private.pem ] || openssl genrsa -out jwt_private.pem 2048
[ -f jwt_pubkey.pem ] || openssl rsa -in jwt_private.pem -pubout -out jwt_pubkey.pem
```

## Configuration Options

| Option            | Description                                                                                  | Default     |
|-------------------|----------------------------------------------------------------------------------------------|-------------|
| `enabled`         | Enable/disable plugin                                                                        | `true`      |
| `algorithm`       | JWT signing algorithm                                                                        | `RS256`     |
| `issuer`          | Expected JWT issuer (optional, set to `none`/`null` to skip validation)                      | (optional)  |
| `audience`        | Expected JWT audience (optional, set to `none`/`null` to skip validation)                    | (optional)  |
| `pubkey_path`     | Path to public key file (priority 1: explicit file path)                                    | (optional)  |
| `pubkey`          | Public key content as base64-encoded string (priority 2: inline content)                    | (optional)  |
| `k8s_secret.pubkey` | Kubernetes secret containing public key (priority 3: Kubernetes only)                    | (optional)  |
| `paths`           | List of paths that require JWT validation (optional)                                         | (all paths) |
| `only_paths`      | If `true`, only specified paths are accessible; if `false`, only specified paths require JWT | `false`     |
| `allow_anonymous` | If `true`, allows requests without Authorization header (validates JWT if present)           | `false`     |

### Public Key Configuration Priority

When multiple public key options are configured, they are evaluated in this order:
1. **`pubkey_path`** - Direct file path (explicit configuration)
2. **`pubkey`** - Base64-encoded key content (inline configuration)
3. **`k8s_secret.pubkey`** - Kubernetes secret (recommended for Kubernetes deployments)

## Path Validation Logic

- **No paths configured:** ALL requests to the domain require JWT validation (default behavior)
- **Paths configured + `only_paths=false`:** Only specified paths require JWT validation, other paths pass through without validation
- **Paths configured + `only_paths=true`:** Only specified paths are accessible (with JWT validation), all other paths are denied

## Anonymous Access Logic

- **`allow_anonymous=false` (default):** Requests without `Authorization` header are denied
- **`allow_anonymous=true`:** Requests without `Authorization` header are allowed to pass through, but JWTs are validated if the header is present

## Configuration Examples

### Docker/Docker Compose (Protect All Paths)

```yaml
services:
  api:
    labels:
      easyhaproxy.http.host: api.example.com
      easyhaproxy.http.plugins: jwt_validator
      easyhaproxy.http.plugin.jwt_validator.algorithm: RS256
      easyhaproxy.http.plugin.jwt_validator.issuer: https://auth.example.com/
      easyhaproxy.http.plugin.jwt_validator.audience: https://api.example.com
      easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/easyhaproxy/jwt_keys/api_pubkey.pem
    volumes:
      - ./pubkey.pem:/etc/easyhaproxy/jwt_keys/api_pubkey.pem:ro
```

### Protect Specific Paths Only

```yaml
labels:
  easyhaproxy.http.plugins: jwt_validator
  easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/easyhaproxy/jwt_keys/api_pubkey.pem
  easyhaproxy.http.plugin.jwt_validator.paths: /api/admin,/api/sensitive
  easyhaproxy.http.plugin.jwt_validator.only_paths: false
# /api/health, /api/docs, etc. remain publicly accessible
```

### Only Allow Specific Paths

```yaml
labels:
  easyhaproxy.http.plugins: jwt_validator
  easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/easyhaproxy/jwt_keys/api_pubkey.pem
  easyhaproxy.http.plugin.jwt_validator.paths: /api/public,/api/v1
  easyhaproxy.http.plugin.jwt_validator.only_paths: true
# All paths except /api/public and /api/v1 are denied
```

### Kubernetes with Secrets (Recommended)

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
    easyhaproxy.plugin.jwt_validator.paths: "/api/admin,/api/users"
    easyhaproxy.plugin.jwt_validator.only_paths: "false"
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

### Static YAML Configuration

```yaml
# /etc/easyhaproxy/static/config.yaml
containers:
  "api.example.com:443":
    ip: ["api-service:8080"]
    ssl: true
    plugins: [jwt_validator]
    plugin:
      jwt_validator:
        algorithm: RS256
        issuer: https://auth.example.com/
        audience: https://api.example.com
        pubkey_path: /etc/easyhaproxy/jwt_keys/api_pubkey.pem
```

### Environment Variables

| Environment Variable                               | Config Key        | Type    | Default | Description                                 |
|----------------------------------------------------|-------------------|---------|---------|---------------------------------------------|
| `EASYHAPROXY_PLUGIN_JWT_VALIDATOR_ENABLED`         | `enabled`         | boolean | `true`  | Enable/disable plugin for all domains       |
| `EASYHAPROXY_PLUGIN_JWT_VALIDATOR_ALGORITHM`       | `algorithm`       | string  | `RS256` | JWT signing algorithm                       |
| `EASYHAPROXY_PLUGIN_JWT_VALIDATOR_ISSUER`          | `issuer`          | string  | -       | Expected JWT issuer (optional)              |
| `EASYHAPROXY_PLUGIN_JWT_VALIDATOR_AUDIENCE`        | `audience`        | string  | -       | Expected JWT audience (optional)            |
| `EASYHAPROXY_PLUGIN_JWT_VALIDATOR_PUBKEY_PATH`     | `pubkey_path`     | string  | -       | Path to public key file                     |
| `EASYHAPROXY_PLUGIN_JWT_VALIDATOR_PUBKEY`          | `pubkey`          | string  | -       | Public key as base64-encoded string         |
| `EASYHAPROXY_PLUGIN_JWT_VALIDATOR_PATHS`           | `paths`           | string  | -       | Comma-separated paths requiring JWT         |
| `EASYHAPROXY_PLUGIN_JWT_VALIDATOR_ONLY_PATHS`      | `only_paths`      | boolean | `false` | If true, only specified paths accessible    |
| `EASYHAPROXY_PLUGIN_JWT_VALIDATOR_ALLOW_ANONYMOUS` | `allow_anonymous` | boolean | `false` | Allow requests without Authorization header |

## What It Validates

- ✅ Authorization header presence
- ✅ JWT signing algorithm (RS256, RS512, etc.)
- ✅ JWT issuer (if configured)
- ✅ JWT audience (if configured)
- ✅ JWT signature using public key
- ✅ JWT expiration time

## Important Notes

- **Required:** HAProxy 2.5+ with JWT support
- Mount public key file as read-only volume
- The plugin runs once per domain during the discovery cycle
- Test thoroughly with your JWT provider before deploying to production

## Related Documentation

- [Plugin System Overview](../../guides/plugins.md)
- [Container Labels Reference](../container-labels.md)
- [Kubernetes Secrets](../../getting-started/kubernetes.md#loading-plugin-configuration-from-kubernetes-secrets)
