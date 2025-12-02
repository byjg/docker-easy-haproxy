---
sidebar_position: 2
---

# JWT Validator Plugin

**Type:** Domain Plugin
**Runs:** Once for each discovered domain/host

## Overview

The JWT Validator plugin validates JWT (JSON Web Token) authentication tokens using HAProxy's built-in JWT functionality.

## Why Use It

Protect APIs and services with JWT authentication without needing application-level code.

## Configuration Options

| Option            | Description                                                                                  | Default     |
|-------------------|----------------------------------------------------------------------------------------------|-------------|
| `enabled`         | Enable/disable plugin                                                                        | `true`      |
| `algorithm`       | JWT signing algorithm                                                                        | `RS256`     |
| `issuer`          | Expected JWT issuer (optional, set to `none`/`null` to skip validation)                      | (optional)  |
| `audience`        | Expected JWT audience (optional, set to `none`/`null` to skip validation)                    | (optional)  |
| `pubkey_path`     | Path to public key file (required if `pubkey` not provided)                                  | (required)  |
| `pubkey`          | Public key content as base64-encoded string (required if `pubkey_path` not provided)         | (optional)  |
| `paths`           | List of paths that require JWT validation (optional)                                         | (all paths) |
| `only_paths`      | If `true`, only specified paths are accessible; if `false`, only specified paths require JWT | `false`     |
| `allow_anonymous` | If `true`, allows requests without Authorization header (validates JWT if present)           | `false`     |

## Path Validation Logic

- **No paths configured:** ALL requests to the domain require JWT validation (default behavior)
- **Paths configured + `only_paths=false`:** Only specified paths require JWT validation, other paths pass through without validation
- **Paths configured + `only_paths=true`:** Only specified paths are accessible (with JWT validation), all other paths are denied

## Anonymous Access Logic

- **`allow_anonymous=false` (default):** Requests without `Authorization` header are denied with "Missing Authorization HTTP header"
- **`allow_anonymous=true`:** Requests without `Authorization` header are allowed to pass through, but JWTs are validated if the header is present

**Use Cases for `allow_anonymous=true`:**
- Optional authentication (show different content for authenticated vs anonymous users)
- Mixed public/private content where some users have enhanced access with JWT
- Gradual JWT authentication rollout
- Public APIs that provide additional features to authenticated users

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
      easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
    volumes:
      - ./pubkey.pem:/etc/haproxy/jwt_keys/api_pubkey.pem:ro
```

### Protect Specific Paths Only

```yaml
labels:
  easyhaproxy.http.plugins: jwt_validator
  easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
  easyhaproxy.http.plugin.jwt_validator.paths: /api/admin,/api/sensitive
  easyhaproxy.http.plugin.jwt_validator.only_paths: false
# /api/health, /api/docs, etc. remain publicly accessible
```

### Only Allow Specific Paths

```yaml
labels:
  easyhaproxy.http.plugins: jwt_validator
  easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
  easyhaproxy.http.plugin.jwt_validator.paths: /api/public,/api/v1
  easyhaproxy.http.plugin.jwt_validator.only_paths: true
# All paths except /api/public and /api/v1 are denied
```

### Skip Issuer/Audience Validation

```yaml
labels:
  easyhaproxy.http.plugin.jwt_validator.issuer: none
  easyhaproxy.http.plugin.jwt_validator.audience: none
  easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
```

### Allow Anonymous Access (Optional JWT)

```yaml
services:
  api:
    labels:
      easyhaproxy.http.host: api.example.com
      easyhaproxy.http.plugins: jwt_validator
      easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
      easyhaproxy.http.plugin.jwt_validator.allow_anonymous: true
    volumes:
      - ./pubkey.pem:/etc/haproxy/jwt_keys/api_pubkey.pem:ro
# Requests without Authorization header are allowed
# Requests with Authorization header are validated
# Invalid JWTs are rejected
```

### Kubernetes Annotations

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    easyhaproxy.plugins: "jwt_validator"
    easyhaproxy.plugin.jwt_validator.algorithm: "RS256"
    easyhaproxy.plugin.jwt_validator.issuer: "https://auth.example.com/"
    easyhaproxy.plugin.jwt_validator.audience: "https://api.example.com"
    easyhaproxy.plugin.jwt_validator.pubkey_path: "/etc/haproxy/jwt_keys/api_pubkey.pem"
    easyhaproxy.plugin.jwt_validator.paths: "/api/admin,/api/users"
    easyhaproxy.plugin.jwt_validator.only_paths: "false"
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            backend:
              service:
                name: api-service
                port:
                  number: 8080
```

### Static YAML Configuration

```yaml
# /etc/haproxy/static/config.yaml
easymapping:
  - host: api.example.com
    port: 443
    container: api-service:8080
    plugins:
      - jwt_validator
    plugin_config:
      jwt_validator:
        algorithm: RS256
        issuer: https://auth.example.com/
        audience: https://api.example.com
        pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
```

### Environment Variables

Configure JWT Validator plugin defaults for all domains:

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

**Note:** Environment variables set defaults for ALL domains. To configure per-domain, use container labels or Kubernetes annotations.

## Generated HAProxy Configuration

### All Paths Protected

```haproxy
# JWT Validator - Validate JWT tokens
http-request deny content-type 'text/html' string 'Missing Authorization HTTP header' unless { req.hdr(authorization) -m found }

# Extract JWT header and payload
http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg')
http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss')
http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud')
http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int')

# Validate JWT
http-request deny content-type 'text/html' string 'Unsupported JWT signing algorithm' unless { var(txn.alg) -m str RS256 }
http-request deny content-type 'text/html' string 'Invalid JWT issuer' unless { var(txn.iss) -m str https://auth.example.com/ }
http-request deny content-type 'text/html' string 'Invalid JWT audience' unless { var(txn.aud) -m str https://api.example.com }
http-request deny content-type 'text/html' string 'Invalid JWT signature' unless { http_auth_bearer,jwt_verify(txn.alg,"/etc/haproxy/jwt_keys/api_pubkey.pem") -m int 1 }

# Validate expiration
http-request set-var(txn.now) date()
http-request deny content-type 'text/html' string 'JWT has expired' if { var(txn.exp),sub(txn.now) -m int lt 0 }
```

### Specific Paths Only (only_paths=false)

```haproxy
# JWT Validator - Validate JWT tokens

# Define paths that require JWT validation
acl jwt_protected_path path_beg /api/admin
acl jwt_protected_path path_beg /api/sensitive

http-request deny content-type 'text/html' string 'Missing Authorization HTTP header' unless { req.hdr(authorization) -m found } if jwt_protected_path

# Extract JWT header and payload
http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg') if jwt_protected_path
http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss') if jwt_protected_path
http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud') if jwt_protected_path
http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int') if jwt_protected_path

# Validate JWT (only on protected paths)
http-request deny content-type 'text/html' string 'Unsupported JWT signing algorithm' unless { var(txn.alg) -m str RS256 } if jwt_protected_path
http-request deny content-type 'text/html' string 'Invalid JWT signature' unless { http_auth_bearer,jwt_verify(txn.alg,"/etc/haproxy/jwt_keys/api_pubkey.pem") -m int 1 } if jwt_protected_path

# Validate expiration
http-request set-var(txn.now) date() if jwt_protected_path
http-request deny content-type 'text/html' string 'JWT has expired' if { var(txn.exp),sub(txn.now) -m int lt 0 } if jwt_protected_path
```

### Specific Paths Only (only_paths=true)

```haproxy
# JWT Validator - Validate JWT tokens

# Define paths that require JWT validation
acl jwt_protected_path path_beg /api/public
acl jwt_protected_path path_beg /api/v1

# Deny access to paths not in the protected list
http-request deny content-type 'text/html' string 'Access denied' unless jwt_protected_path

http-request deny content-type 'text/html' string 'Missing Authorization HTTP header' unless { req.hdr(authorization) -m found }

# Extract JWT header and payload
http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg')
http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss')
http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud')
http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int')

# Validate JWT (all requests at this point are on allowed paths)
http-request deny content-type 'text/html' string 'Unsupported JWT signing algorithm' unless { var(txn.alg) -m str RS256 }
http-request deny content-type 'text/html' string 'Invalid JWT signature' unless { http_auth_bearer,jwt_verify(txn.alg,"/etc/haproxy/jwt_keys/api_pubkey.pem") -m int 1 }

# Validate expiration
http-request set-var(txn.now) date()
http-request deny content-type 'text/html' string 'JWT has expired' if { var(txn.exp),sub(txn.now) -m int lt 0 }
```

### Allow Anonymous Access (allow_anonymous=true)

```haproxy
# JWT Validator - Validate JWT tokens

# Allow anonymous access - validate JWT only if Authorization header is present

# Extract JWT header and payload
http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg') if { req.hdr(authorization) -m found }
http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss') if { req.hdr(authorization) -m found }
http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud') if { req.hdr(authorization) -m found }
http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int') if { req.hdr(authorization) -m found }

# Validate JWT (only if Authorization header is present)
http-request deny content-type 'text/html' string 'Unsupported JWT signing algorithm' unless { var(txn.alg) -m str RS256 } if { req.hdr(authorization) -m found }
http-request deny content-type 'text/html' string 'Invalid JWT issuer' unless { var(txn.iss) -m str https://auth.example.com/ } if { req.hdr(authorization) -m found }
http-request deny content-type 'text/html' string 'Invalid JWT audience' unless { var(txn.aud) -m str https://api.example.com } if { req.hdr(authorization) -m found }
http-request deny content-type 'text/html' string 'Invalid JWT signature' unless { http_auth_bearer,jwt_verify(txn.alg,"/etc/haproxy/jwt_keys/api_pubkey.pem") -m int 1 } if { req.hdr(authorization) -m found }

# Validate expiration (only if Authorization header is present)
http-request set-var(txn.now) date() if { req.hdr(authorization) -m found }
http-request deny content-type 'text/html' string 'JWT has expired' if { var(txn.exp),sub(txn.now) -m int lt 0 } if { req.hdr(authorization) -m found }
```

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

- [Plugin System Overview](../plugins.md)
- [Container Labels Reference](../container-labels.md)
