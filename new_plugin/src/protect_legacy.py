"""Protect Legacy Application Plugin for EasyHAProxy

Provides JWT Bearer token validation with JSON error responses,
role-based access control (RBAC) per path and/or HTTP method,
and forwarding decoded JWT claims as headers to the backend app.

This plugin is designed for legacy applications that cannot implement
their own authentication or authorization.

Configuration Labels:
    easyhaproxy.app.plugins: "protect_legacy"

    # JWT Configuration
    easyhaproxy.app.plugin.protect_legacy.algorithm: RS256
    easyhaproxy.app.plugin.protect_legacy.issuer: https://auth.example.com/
    easyhaproxy.app.plugin.protect_legacy.audience: https://api.example.com
    easyhaproxy.app.plugin.protect_legacy.pubkey_path: /etc/easyhaproxy/jwt_keys/pubkey.pem
    # OR inline base64-encoded PEM:
    easyhaproxy.app.plugin.protect_legacy.pubkey: "<base64-encoded-pem>"

    # Optional path restriction (default: protect entire domain)
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
    easyhaproxy.app.plugin.protect_legacy.forward_claims: "email"

    # Optional custom error messages
    easyhaproxy.app.plugin.protect_legacy.unauthorized_message: Unauthorized
    easyhaproxy.app.plugin.protect_legacy.forbidden_message: Insufficient permissions

Deployment:
    Copy src/protect_legacy.py into the EasyHAProxy plugins directory
    (default /etc/easyhaproxy/plugins/) or set EASYHAPROXY_PLUGINS_DIR.
"""

import base64
import os
import re
import sys

from plugins import (
    InitializationResult,
    PluginContext,
    PluginInterface,
    PluginResult,
    PluginType,
    ResourceRequest,
)
from functions import Functions, logger_easyhaproxy, Consts


class ProtectLegacyPlugin(PluginInterface):
    """Protect legacy applications with JWT authentication and RBAC."""

    def __init__(self):
        self.enabled = True
        self.algorithm = "RS256"
        self.issuer = None
        self.audience = None
        self.pubkey_path = None
        self.pubkey = None  # Decoded PEM content (from base64-encoded label)
        self.paths = []
        self.allow_anonymous = False
        # {role_name: {"rules": [(method|None, path), ...], "inherits": [...]}}
        self.roles = {}
        self.strict_roles = False
        self.claim_userid = "userid"
        self.claim_role = "role"
        self.claim_name = "name"
        self.forward_claims = []
        self.unauthorized_message = "Unauthorized"
        self.forbidden_message = "Insufficient permissions"
        self.jwt_keys_dir = os.getenv(
            "EASYHAPROXY_JWT_KEYS_DIR", Consts.base_path + "/jwt_keys"
        )

    @property
    def name(self) -> str:
        return "protect_legacy"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        """Configure the plugin from label/YAML settings."""
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "algorithm" in config:
            self.algorithm = str(config["algorithm"]).strip()

        if "issuer" in config:
            issuer = str(config["issuer"]).strip()
            if issuer:
                self.issuer = issuer

        if "audience" in config:
            audience = str(config["audience"]).strip()
            if audience:
                self.audience = audience

        if "pubkey_path" in config:
            self.pubkey_path = str(config["pubkey_path"]).strip()

        if "pubkey" in config:
            self.pubkey = base64.b64decode(config["pubkey"]).decode("ascii")

        if "paths" in config:
            paths_config = config["paths"]
            if isinstance(paths_config, list):
                self.paths = [str(p).strip() for p in paths_config if str(p).strip()]
            elif isinstance(paths_config, str):
                self.paths = [p.strip() for p in paths_config.split(",") if p.strip()]

        if "allow_anonymous" in config:
            self.allow_anonymous = (
                str(config["allow_anonymous"]).lower() in ["true", "1", "yes"]
            )

        if "strict_roles" in config:
            self.strict_roles = (
                str(config["strict_roles"]).lower() in ["true", "1", "yes"]
            )

        if "claim_userid" in config:
            self.claim_userid = str(config["claim_userid"]).strip()

        if "claim_role" in config:
            self.claim_role = str(config["claim_role"]).strip()

        if "claim_name" in config:
            self.claim_name = str(config["claim_name"]).strip()

        if "forward_claims" in config:
            fc = config["forward_claims"]
            if isinstance(fc, list):
                self.forward_claims = [str(c).strip() for c in fc if str(c).strip()]
            elif isinstance(fc, str):
                self.forward_claims = [
                    c.strip() for c in fc.split(",") if c.strip()
                ]

        if "unauthorized_message" in config:
            self.unauthorized_message = str(config["unauthorized_message"])

        if "forbidden_message" in config:
            self.forbidden_message = str(config["forbidden_message"])

        # Parse role definitions: keys matching role.<name>
        for key, value in config.items():
            m = re.match(r"^role\.(.+)$", key)
            if m:
                role_name = m.group(1)
                rules, inherits = self._parse_role_rules(str(value))
                self.roles[role_name] = {"rules": rules, "inherits": inherits}

    def _parse_role_rules(self, value: str) -> tuple:
        """Parse a role rule string into (rules, inherits).

        Args:
            value: Comma-separated rule string, e.g. "GET /admin, /admin, [manager]"

        Returns:
            Tuple of (rules, inherits) where:
              - rules: list of (method|None, path) tuples
              - inherits: list of role names this role inherits from
        """
        rules = []
        inherits = []

        for item in value.split(","):
            item = item.strip()
            if not item:
                continue

            # Inheritance entry: [role_name]
            inherit_match = re.match(r"^\[(.+)\]$", item)
            if inherit_match:
                inherits.append(inherit_match.group(1).strip())
                continue

            # Method + path: "METHOD /path"
            method_path_match = re.match(r"^([A-Z]+)\s+(/.+)$", item)
            if method_path_match:
                rules.append((method_path_match.group(1), method_path_match.group(2)))
                continue

            # Path only (all methods)
            if item.startswith("/"):
                rules.append((None, item))

        return rules, inherits

    def _compute_satisfiers(self) -> dict:
        """Compute for each role the set of roles that can satisfy its requirements.

        satisfiers[R] = {R} ∪ {all roles that inherit from R, transitively}

        Returns:
            Dict mapping role_name → set of satisfier role names
        """
        all_roles = set(self.roles.keys())

        # Build direct_inheritors: roles that DIRECTLY inherit from each role
        direct_inheritors: dict = {r: set() for r in all_roles}
        for role_name, role_data in self.roles.items():
            for inherited_role in role_data["inherits"]:
                if inherited_role in direct_inheritors:
                    direct_inheritors[inherited_role].add(role_name)

        # Fixed-point iteration to compute transitive satisfiers
        satisfiers: dict = {r: {r} for r in all_roles}
        changed = True
        while changed:
            changed = False
            for role in all_roles:
                for inheritor in direct_inheritors[role]:
                    expanded = satisfiers[role] | satisfiers[inheritor]
                    if expanded != satisfiers[role]:
                        satisfiers[role] = expanded
                        changed = True

        return satisfiers

    def _role_regex(self, role_name: str) -> str:
        """Build HAProxy regex matching role_name in a comma-separated scope claim."""
        escaped = re.escape(role_name)
        return rf"(?:^|,)\s*{escaped}\s*(?:$|,)"

    def initialize(self) -> InitializationResult:
        return InitializationResult(
            resources=[ResourceRequest(resource_type="directory", path=self.jwt_keys_dir)]
        )

    def process(self, context: PluginContext) -> PluginResult:
        """Generate HAProxy config for JWT validation and RBAC."""
        if not self.enabled:
            return PluginResult()

        # Resolve public key file path
        if self.pubkey_path:
            pubkey_file = self.pubkey_path
        elif self.pubkey:
            domain_safe = (context.domain or "unknown").replace(".", "_").replace(":", "_")
            pubkey_file = f"{self.jwt_keys_dir}/{domain_safe}_pubkey.pem"
            try:
                os.makedirs(self.jwt_keys_dir, exist_ok=True)
                Functions.save(pubkey_file, self.pubkey)
            except (PermissionError, OSError) as e:
                logger_easyhaproxy.debug(f"Could not write JWT public key file: {e}")
        else:
            logger_easyhaproxy.warning(
                f"protect_legacy plugin for {context.domain}: "
                "No pubkey or pubkey_path configured"
            )
            return PluginResult()

        lines = ["# Protect Legacy Application - JWT Authentication + RBAC", ""]

        # Authorization header check
        if not self.allow_anonymous:
            lines.append("# Authorization header required")
            lines.append(
                "http-request deny deny_status 401 content-type 'application/json' "
                "string '{\"error\":\"Missing Authorization HTTP header\"}' "
                "unless { req.hdr(authorization) -m found }"
            )
            lines.append("")

        # Extract JWT header and payload
        lines.append("# Extract JWT header and payload")
        lines.append("http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg')")
        lines.append("http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss')")
        lines.append("http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud')")
        lines.append("http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int')")
        if self.roles:
            lines.append(
                "http-request set-var(txn.scope) http_auth_bearer,jwt_payload_query('$.scope')"
            )
        lines.append("")

        # Validate JWT claims
        lines.append("# Validate JWT claims")
        lines.append(
            f"http-request deny deny_status 401 content-type 'application/json' "
            f"string '{{\"error\":\"Unsupported JWT signing algorithm\"}}' "
            f"unless {{ var(txn.alg) -m str {self.algorithm} }}"
        )
        if self.issuer:
            lines.append(
                f"http-request deny deny_status 401 content-type 'application/json' "
                f"string '{{\"error\":\"Invalid JWT issuer\"}}' "
                f"unless {{ var(txn.iss) -m str {self.issuer} }}"
            )
        if self.audience:
            lines.append(
                f"http-request deny deny_status 401 content-type 'application/json' "
                f"string '{{\"error\":\"Invalid JWT audience\"}}' "
                f"unless {{ var(txn.aud) -m str {self.audience} }}"
            )
        lines.append(
            f"http-request deny deny_status 401 content-type 'application/json' "
            f"string '{{\"error\":\"Invalid JWT signature\"}}' "
            f"unless {{ http_auth_bearer,jwt_verify(txn.alg,\"{pubkey_file}\") -m int 1 }}"
        )
        lines.append("")

        # Validate expiration
        lines.append("# Validate expiration")
        lines.append("http-request set-var(txn.now) date()")
        lines.append(
            "http-request deny deny_status 401 content-type 'application/json' "
            "string '{\"error\":\"JWT has expired\"}' "
            "if { var(txn.exp),sub(txn.now) -m int lt 0 }"
        )
        lines.append("")

        # Extract and validate required claims
        lines.append(
            f"# Extract and validate required claims "
            f"({self.claim_userid}, {self.claim_role}, {self.claim_name})"
        )
        lines.append(
            f"http-request set-var(txn.userid) "
            f"http_auth_bearer,jwt_payload_query('$.{self.claim_userid}')"
        )
        lines.append(
            f"http-request set-var(txn.role)   "
            f"http_auth_bearer,jwt_payload_query('$.{self.claim_role}')"
        )
        lines.append(
            f"http-request set-var(txn.name)   "
            f"http_auth_bearer,jwt_payload_query('$.{self.claim_name}')"
        )
        lines.append(
            f"http-request deny deny_status 401 content-type 'application/json' "
            f"string '{{\"error\":\"Missing required claim: {self.claim_userid}\"}}' "
            f"unless {{ var(txn.userid) -m len gt 0 }}"
        )
        lines.append(
            f"http-request deny deny_status 401 content-type 'application/json' "
            f"string '{{\"error\":\"Missing required claim: {self.claim_role}\"}}' "
            f"unless {{ var(txn.role) -m len gt 0 }}"
        )
        lines.append(
            f"http-request deny deny_status 401 content-type 'application/json' "
            f"string '{{\"error\":\"Missing required claim: {self.claim_name}\"}}' "
            f"unless {{ var(txn.name) -m len gt 0 }}"
        )
        lines.append("")

        # Forward required claims to backend
        lines.append("# Forward required claims to backend (always present)")
        lines.append("http-request set-header X-Auth-Userid %[var(txn.userid)]")
        lines.append("http-request set-header X-Auth-Role   %[var(txn.role)]")
        lines.append("http-request set-header X-Auth-Name   %[var(txn.name)]")
        lines.append("")

        # Forward scope and additional claims
        if self.roles or self.forward_claims:
            lines.append("# Forward scope and additional configured claims")
            if self.roles:
                lines.append("http-request set-header X-Auth-Scope  %[var(txn.scope)]")
            for claim in self.forward_claims:
                header_name = f"X-Auth-{claim.capitalize()}"
                lines.append(
                    f"http-request set-header {header_name}  "
                    f"%[http_auth_bearer,jwt_payload_query('$.{claim}')]"
                )
            lines.append("")

        # RBAC
        if self.roles:
            satisfiers = self._compute_satisfiers()
            if self.strict_roles:
                lines += self._generate_strict_rbac(satisfiers)
            else:
                lines += self._generate_permissive_rbac(satisfiers)

        return PluginResult(
            haproxy_config="\n".join(lines).rstrip(),
            metadata={
                "domain": context.domain,
                "algorithm": self.algorithm,
                "pubkey_file": pubkey_file,
                "strict_roles": self.strict_roles,
                "role_count": len(self.roles),
            },
        )

    def _generate_permissive_rbac(self, satisfiers: dict) -> list:
        """Generate permissive mode RBAC (deny only on listed paths if wrong role)."""
        lines = [
            "# RBAC - permissive mode: only listed paths enforced, others pass with valid JWT"
        ]

        for role in sorted(self.roles.keys()):
            lines.append(
                f"acl protect_legacy_has_{role} "
                f"var(txn.scope) -m reg {self._role_regex(role)}"
            )
        lines.append("")

        forbidden = self.forbidden_message.replace('"', '\\"')

        for role_name, role_data in self.roles.items():
            for idx, (method, path) in enumerate(role_data["rules"]):
                acl_prefix = f"protect_legacy_role_{role_name}_{idx}"
                method_label = method if method else "all methods"
                lines.append(f"# {role_name}: {method_label} {path}")
                lines.append(f"acl {acl_prefix}_path path_beg {path}")

                if method:
                    lines.append(f"acl {acl_prefix}_method method {method}")
                    method_cond = f" {acl_prefix}_method"
                else:
                    method_cond = ""

                role_satisfiers = satisfiers.get(role_name, {role_name})
                not_roles = " ".join(
                    f"!protect_legacy_has_{r}" for r in sorted(role_satisfiers)
                )
                lines.append(
                    f"http-request deny deny_status 403 content-type 'application/json' "
                    f"string '{{\"error\":\"{forbidden}\"}}' "
                    f"if {acl_prefix}_path{method_cond} {not_roles}"
                )
                lines.append("")

        return lines

    def _generate_strict_rbac(self, satisfiers: dict) -> list:
        """Generate strict (whitelist) mode RBAC."""
        lines = ["# RBAC - strict mode: deny unless explicitly allowed"]

        for role in sorted(self.roles.keys()):
            lines.append(
                f"acl protect_legacy_has_{role} "
                f"var(txn.scope) -m reg {self._role_regex(role)}"
            )
        lines.append("")

        for role_name, role_data in self.roles.items():
            for idx, (method, path) in enumerate(role_data["rules"]):
                acl_prefix = f"protect_legacy_role_{role_name}_{idx}"
                method_label = method if method else "all methods"
                lines.append(f"# {role_name}: {method_label} {path}")
                lines.append(f"acl {acl_prefix}_path path_beg {path}")

                if method:
                    lines.append(f"acl {acl_prefix}_method method {method}")
                    method_cond = f" {acl_prefix}_method"
                else:
                    method_cond = ""

                role_satisfiers = satisfiers.get(role_name, {role_name})
                for satisfier in sorted(role_satisfiers):
                    lines.append(
                        f"http-request set-var(txn.pl_allowed) str(1) "
                        f"if {acl_prefix}_path{method_cond} protect_legacy_has_{satisfier}"
                    )
                lines.append("")

        forbidden = self.forbidden_message.replace('"', '\\"')
        lines.append("# Deny anything not explicitly allowed")
        lines.append(
            f"http-request deny deny_status 403 content-type 'application/json' "
            f"string '{{\"error\":\"{forbidden}\"}}' "
            f"unless {{ var(txn.pl_allowed) -m str 1 }}"
        )

        return lines
