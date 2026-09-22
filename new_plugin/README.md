# protect_legacy — Standalone EasyHAProxy Plugin

Protects legacy applications at the proxy layer with:

- **JWT Bearer token validation** with JSON error responses (401)
- **Role-based access control (RBAC)** per path and/or HTTP method (403)
- **Forwarding decoded JWT claims** as headers to the backend application

## Deployment

Copy `src/protect_legacy.py` into EasyHAProxy's plugins directory:

```bash
cp src/protect_legacy.py /etc/easyhaproxy/plugins/
```

Or set the `EASYHAPROXY_PLUGINS_DIR` environment variable to `new_plugin/src/`.

## Configuration Labels

```
easyhaproxy.app.plugins: "protect_legacy"

# JWT Configuration
easyhaproxy.app.plugin.protect_legacy.algorithm: RS256
easyhaproxy.app.plugin.protect_legacy.issuer: https://auth.example.com/
easyhaproxy.app.plugin.protect_legacy.audience: https://api.example.com
easyhaproxy.app.plugin.protect_legacy.pubkey_path: /etc/easyhaproxy/jwt_keys/pubkey.pem
# OR inline base64-encoded PEM:
easyhaproxy.app.plugin.protect_legacy.pubkey: "<base64-encoded-pem>"

# Optional global path restriction (default: protect entire domain)
easyhaproxy.app.plugin.protect_legacy.paths: /api
easyhaproxy.app.plugin.protect_legacy.allow_anonymous: false

# RBAC rules — one label per role
# Value: comma-separated list of "METHOD /path", "/path" (all methods), or "[other_role]" (inherit)
easyhaproxy.app.plugin.protect_legacy.role.admin: "GET /admin, POST /admin, /admin, [manager]"
easyhaproxy.app.plugin.protect_legacy.role.manager: "DELETE /orders"

# strict_roles (default: false)
# false → valid JWT grants access; role rules protect listed paths only
# true  → deny anything not explicitly listed (whitelist mode)
easyhaproxy.app.plugin.protect_legacy.strict_roles: false

# Required JWT claims (always validated + forwarded — missing = 401)
easyhaproxy.app.plugin.protect_legacy.claim_userid: userid   # default
easyhaproxy.app.plugin.protect_legacy.claim_role: role       # default
easyhaproxy.app.plugin.protect_legacy.claim_name: name       # default

# Additional optional JWT claims to forward (comma-separated)
# Each forwarded as X-Auth-{Claim} header
easyhaproxy.app.plugin.protect_legacy.forward_claims: "email"

# Optional custom error messages
easyhaproxy.app.plugin.protect_legacy.unauthorized_message: Unauthorized
easyhaproxy.app.plugin.protect_legacy.forbidden_message: Insufficient permissions
```

## Role Inheritance

Role rules support inheritance using `[other_role]` syntax. Roles are transitively resolved:

```
role.admin:   "GET /admin, /admin, [manager]"
role.manager: "DELETE /orders"
```

- `admin` can: GET /admin, all-methods /admin, AND DELETE /orders (inherited from manager)
- `DELETE /orders` is satisfied by either `manager` or `admin`

## RBAC Modes

**Permissive (`strict_roles: false`, default):** Valid JWT grants access to any path not listed in role rules. Role rules protect only specific listed paths.

**Strict (`strict_roles: true`):** Deny everything not explicitly allowed. A valid JWT + matching role is required for every request.

## Running Tests

```bash
cd new_plugin
EASYHAPROXY_SRC=../src uv run pytest -s -vv tests/
```
