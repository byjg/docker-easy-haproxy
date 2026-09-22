# Plan: `protect_legacy` — Standalone EasyHAProxy Plugin

## Context
Legacy applications cannot be modified to implement authentication or authorization. This standalone plugin sits on top of EasyHAProxy and handles, at the proxy layer:
1. JWT Bearer token validation with JSON error responses
2. Role-based access control (RBAC) per path and/or HTTP method
3. Forwarding decoded JWT claims as headers to the backend app

It lives as its own project under `new_plugin/` — a separate, independently versioned package that is NOT merged into the main EasyHAProxy repo. It is loaded at runtime via `EASYHAPROXY_PLUGINS_DIR`.

---

## Standalone Project Structure

```
new_plugin/
├── pyproject.toml              # package metadata + deps
├── README.md                   # usage instructions
├── src/
│   └── protect_legacy.py       # single-file plugin (drop-in for EasyHAProxy)
└── tests/
    ├── conftest.py
    └── test_protect_legacy.py
```

### `pyproject.toml`
```toml
[project]
name = "easyhaproxy-protect-legacy"
version = "0.1.0"
description = "Protect Legacy Applications plugin for EasyHAProxy"
requires-python = ">=3.11"
dependencies = []                 # no runtime dependencies (EasyHAProxy provides the base)

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "easyhaproxy",               # dev dep: imports PluginInterface, PluginResult, etc.
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.0",
    "easyhaproxy",
]
```

**Deployment:** copy `src/protect_legacy.py` into the EasyHAProxy plugins directory (default `/etc/easyhaproxy/plugins/`) or set `EASYHAPROXY_PLUGINS_DIR`.

---

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
# userid → X-Auth-Userid, role → X-Auth-Role, name → X-Auth-Name
# These three are ALWAYS required and forwarded. Claim names are configurable:
easyhaproxy.app.plugin.protect_legacy.claim_userid: userid   # default
easyhaproxy.app.plugin.protect_legacy.claim_role: role       # default (informational, separate from scope)
easyhaproxy.app.plugin.protect_legacy.claim_name: name       # default

# Additional optional JWT claims to forward (comma-separated)
# Each forwarded as X-Auth-{Claim} header
easyhaproxy.app.plugin.protect_legacy.forward_claims: "email"

# Optional custom error messages
easyhaproxy.app.plugin.protect_legacy.unauthorized_message: Unauthorized
easyhaproxy.app.plugin.protect_legacy.forbidden_message: Insufficient permissions
```

---

## Role Rule Parsing

Each `role.{role_name}` value is a comma-separated list:
- `"GET /admin"` → role required for GET on paths beginning with `/admin`
- `"/admin"` → role required for **all methods** on paths beginning with `/admin`
- `"[manager]"` → inherit all permissions from the `manager` role (transitively resolved)

**Example resolution:**
```
role.admin:   "GET /admin, /admin, [manager]"
role.manager: "DELETE /orders"
```
→ `admin` satisfies: GET /admin, all-methods /admin, AND inherits DELETE /orders from `manager`
→ `DELETE /orders` satisfying roles = `{manager, admin}` (transitive closure)

---

## HAProxy Config Generated

### JWT Validation (common to both strict_roles modes)
```haproxy
# Protect Legacy Application - JWT Authentication + RBAC

# Authorization header required
http-request deny deny_status 401 content-type 'application/json' string '{"error":"Missing Authorization HTTP header"}' unless { req.hdr(authorization) -m found }

# Extract JWT header and payload
http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg')
http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss')
http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud')
http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int')
http-request set-var(txn.scope) http_auth_bearer,jwt_payload_query('$.scope')

# Validate JWT claims
http-request deny deny_status 401 content-type 'application/json' string '{"error":"Unsupported JWT signing algorithm"}' unless { var(txn.alg) -m str RS256 }
http-request deny deny_status 401 content-type 'application/json' string '{"error":"Invalid JWT issuer"}' unless { var(txn.iss) -m str https://auth.example.com/ }
http-request deny deny_status 401 content-type 'application/json' string '{"error":"Invalid JWT audience"}' unless { var(txn.aud) -m str https://api.example.com }
http-request deny deny_status 401 content-type 'application/json' string '{"error":"Invalid JWT signature"}' unless { http_auth_bearer,jwt_verify(txn.alg,"/etc/easyhaproxy/jwt_keys/pubkey.pem") -m int 1 }

# Validate expiration
http-request set-var(txn.now) date()
http-request deny deny_status 401 content-type 'application/json' string '{"error":"JWT has expired"}' if { var(txn.exp),sub(txn.now) -m int lt 0 }

# Extract and validate required claims (userid, role, name)
http-request set-var(txn.userid) http_auth_bearer,jwt_payload_query('$.userid')
http-request set-var(txn.role)   http_auth_bearer,jwt_payload_query('$.role')
http-request set-var(txn.name)   http_auth_bearer,jwt_payload_query('$.name')
http-request deny deny_status 401 content-type 'application/json' string '{"error":"Missing required claim: userid"}' unless { var(txn.userid) -m len gt 0 }
http-request deny deny_status 401 content-type 'application/json' string '{"error":"Missing required claim: role"}' unless { var(txn.role) -m len gt 0 }
http-request deny deny_status 401 content-type 'application/json' string '{"error":"Missing required claim: name"}' unless { var(txn.name) -m len gt 0 }

# Forward required claims to backend (always present)
http-request set-header X-Auth-Userid %[var(txn.userid)]
http-request set-header X-Auth-Role   %[var(txn.role)]
http-request set-header X-Auth-Name   %[var(txn.name)]

# Forward scope (used for RBAC) and additional configured claims
http-request set-header X-Auth-Scope  %[var(txn.scope)]
http-request set-header X-Auth-Email  %[http_auth_bearer,jwt_payload_query('$.email')]
```

### RBAC — `strict_roles: false` (permissive)
```haproxy
# RBAC - permissive mode: only listed paths enforced, others pass with valid JWT
acl protect_legacy_has_admin   var(txn.scope) -m reg (?:^|,)\s*admin\s*(?:$|,)
acl protect_legacy_has_manager var(txn.scope) -m reg (?:^|,)\s*manager\s*(?:$|,)

# admin: GET /admin
acl protect_legacy_role_admin_0_path   path_beg /admin
acl protect_legacy_role_admin_0_method method GET
http-request deny deny_status 403 content-type 'application/json' string '{"error":"Insufficient permissions"}' if protect_legacy_role_admin_0_path protect_legacy_role_admin_0_method !protect_legacy_has_admin

# admin: /admin (all methods)
acl protect_legacy_role_admin_1_path path_beg /admin
http-request deny deny_status 403 content-type 'application/json' string '{"error":"Insufficient permissions"}' if protect_legacy_role_admin_1_path !protect_legacy_has_admin

# manager: DELETE /orders (also satisfied by admin via inheritance)
acl protect_legacy_role_manager_0_path   path_beg /orders
acl protect_legacy_role_manager_0_method method DELETE
http-request deny deny_status 403 content-type 'application/json' string '{"error":"Insufficient permissions"}' if protect_legacy_role_manager_0_path protect_legacy_role_manager_0_method !protect_legacy_has_manager !protect_legacy_has_admin
# !has_manager !has_admin = deny unless (has_manager OR has_admin)
```

### RBAC — `strict_roles: true` (whitelist)
```haproxy
# RBAC - strict mode: deny unless explicitly allowed
acl protect_legacy_has_admin   var(txn.scope) -m reg (?:^|,)\s*admin\s*(?:$|,)
acl protect_legacy_has_manager var(txn.scope) -m reg (?:^|,)\s*manager\s*(?:$|,)

acl protect_legacy_role_admin_0_path   path_beg /admin
acl protect_legacy_role_admin_0_method method GET
http-request set-var(txn.pl_allowed) str(1) if protect_legacy_role_admin_0_path protect_legacy_role_admin_0_method protect_legacy_has_admin

acl protect_legacy_role_admin_1_path path_beg /admin
http-request set-var(txn.pl_allowed) str(1) if protect_legacy_role_admin_1_path protect_legacy_has_admin

acl protect_legacy_role_manager_0_path   path_beg /orders
acl protect_legacy_role_manager_0_method method DELETE
http-request set-var(txn.pl_allowed) str(1) if protect_legacy_role_manager_0_path protect_legacy_role_manager_0_method protect_legacy_has_manager
http-request set-var(txn.pl_allowed) str(1) if protect_legacy_role_manager_0_path protect_legacy_role_manager_0_method protect_legacy_has_admin

# Deny anything not explicitly allowed
http-request deny deny_status 403 content-type 'application/json' string '{"error":"Insufficient permissions"}' unless { var(txn.pl_allowed) -m str 1 }
```

---

## Files to Create

### 1. `new_plugin/src/protect_legacy.py`
Single-file plugin. Imports:
```python
import sys, os
# When loaded by EasyHAProxy, its src/ is on sys.path already
from plugins import InitializationResult, PluginContext, PluginInterface, PluginResult, PluginType, ResourceRequest
from functions import Functions, logger_easyhaproxy, Consts
```
Key methods: `configure()`, `initialize()`, `process()`.
Role parsing uses regex `^\[(.+)\]$` to detect inheritance entries. Transitive closure via fixed-point iteration. `re.escape()` on all role names before embedding in HAProxy regex.

### 2. `new_plugin/pyproject.toml`
As shown above. Dev dependency on `easyhaproxy` for test imports.

### 3. `new_plugin/tests/conftest.py`
Adds the easyhaproxy `src/` directory to `sys.path` so `from plugins import ...` works during tests:
```python
import sys, os
EASYHAPROXY_SRC = os.getenv("EASYHAPROXY_SRC", "../src")  # adjust as needed
sys.path.insert(0, os.path.abspath(EASYHAPROXY_SRC))
sys.path.insert(0, os.path.abspath("src"))
```

### 4. `new_plugin/tests/test_protect_legacy.py`
Test class `TestProtectLegacyPlugin`:
- `test_initialization` — defaults correct
- `test_configuration` — all config keys parsed
- `test_role_parsing_path_only` — `"/admin"` → method None
- `test_role_parsing_method_and_path` — `"GET /admin"` → method GET
- `test_role_inheritance_parsing` — `"[manager]"` detected as inheritance
- `test_inheritance_transitive_closure` — admin inherits manager's rules
- `test_generates_jwt_validation_json_errors` — 401 with application/json
- `test_generates_required_claim_validation` — 401 if userid/role/name missing
- `test_generates_required_claim_headers` — X-Auth-Userid, X-Auth-Role, X-Auth-Name always present
- `test_generates_permissive_rbac` — deny rules with inheritance-expanded roles
- `test_generates_strict_rbac` — set-var + final deny
- `test_generates_forward_claims_headers` — additional X-Auth-* headers from forward_claims
- `test_custom_claim_names` — configurable claim_userid/claim_role/claim_name
- `test_disabled` — empty config returned
- `test_no_pubkey` — empty config returned

---

## Key Implementation Notes

1. **Import path**: When EasyHAProxy loads the plugin file, its `src/` is on sys.path already. The plugin can import `from plugins import ...` directly — same as builtin plugins.

2. **`configure()` role label detection**: The plugin manager passes `plugin.protect_legacy.*` keys as a flat dict. Keys like `role.admin` and `role.manager` are picked up by iterating config keys matching `^role\.(.+)$`.

3. **Transitive closure algorithm**:
   ```python
   # inheritors[R] = set of roles that satisfy rules requiring R
   for role, data in roles.items():
       for inherited_role in data["inherits"]:
           inheritors[inherited_role].add(role)
   # Iterate until stable for transitive chains
   ```

4. **Required claims** (`userid`, `role`, `name` — configurable via `claim_userid`, `claim_role`, `claim_name`): extracted into `txn.userid`, `txn.role`, `txn.name`, validated with `unless { var(...) -m len gt 0 }`, then forwarded as `X-Auth-Userid`, `X-Auth-Role`, `X-Auth-Name`. Always present in the output config when enabled (default on).

5. **Header prefix**: `X-Auth-{Claim-Capitalized}` — e.g., claim `email` → `X-Auth-Email`. Required claims use fixed header names. Optional `forward_claims` claims use the same `X-Auth-{name}` pattern. `scope` is forwarded as `X-Auth-Scope` when RBAC rules exist.

6. **No changes to the main EasyHAProxy repo** — this is fully standalone.

---

## Verification

```bash
cd new_plugin
EASYHAPROXY_SRC=../src uv run pytest -s -vv tests/
```
End-to-end: add the plugin to a running EasyHAProxy container by setting `EASYHAPROXY_PLUGINS_DIR` to the `new_plugin/src/` directory, then configure a service with the plugin labels.
