import base64

import pytest

from protect_legacy import ProtectLegacyPlugin
from plugins import PluginContext, PluginResult


def make_context(domain: str = "example.com") -> PluginContext:
    return PluginContext(
        parsed_object={},
        easymapping=[],
        container_env={},
        domain=domain,
        port="80",
        host_config={},
    )


def base_config(**overrides) -> dict:
    cfg = {
        "pubkey_path": "/etc/easyhaproxy/jwt_keys/test.pem",
        "algorithm": "RS256",
        "issuer": "https://auth.example.com/",
        "audience": "https://api.example.com",
    }
    cfg.update(overrides)
    return cfg


class TestProtectLegacyPlugin:
    def setup_method(self):
        self.plugin = ProtectLegacyPlugin()

    # ------------------------------------------------------------------ #
    # Defaults and configuration parsing                                   #
    # ------------------------------------------------------------------ #

    def test_initialization(self):
        p = self.plugin
        assert p.enabled is True
        assert p.algorithm == "RS256"
        assert p.issuer is None
        assert p.audience is None
        assert p.pubkey_path is None
        assert p.pubkey is None
        assert p.paths == []
        assert p.allow_anonymous is False
        assert p.roles == {}
        assert p.strict_roles is False
        assert p.claim_userid == "userid"
        assert p.claim_role == "role"
        assert p.claim_name == "name"
        assert p.forward_claims == []
        assert p.forbidden_message == "Insufficient permissions"
        assert p.unauthorized_message == "Unauthorized"

    def test_configuration(self):
        pubkey_b64 = base64.b64encode(
            b"-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----\n"
        ).decode()

        self.plugin.configure({
            "algorithm": "HS256",
            "issuer": "https://my.auth.com/",
            "audience": "https://my.api.com",
            "pubkey_path": "/etc/keys/pub.pem",
            "pubkey": pubkey_b64,
            "paths": "/api,/v2",
            "allow_anonymous": "true",
            "strict_roles": "true",
            "claim_userid": "sub",
            "claim_role": "scope",
            "claim_name": "preferred_username",
            "forward_claims": "email,tenant",
            "unauthorized_message": "Access denied",
            "forbidden_message": "No permission",
            "role.admin": "GET /admin",
        })

        p = self.plugin
        assert p.algorithm == "HS256"
        assert p.issuer == "https://my.auth.com/"
        assert p.audience == "https://my.api.com"
        assert p.pubkey_path == "/etc/keys/pub.pem"
        assert "BEGIN PUBLIC KEY" in p.pubkey
        assert p.paths == ["/api", "/v2"]
        assert p.allow_anonymous is True
        assert p.strict_roles is True
        assert p.claim_userid == "sub"
        assert p.claim_role == "scope"
        assert p.claim_name == "preferred_username"
        assert p.forward_claims == ["email", "tenant"]
        assert p.unauthorized_message == "Access denied"
        assert p.forbidden_message == "No permission"
        assert "admin" in p.roles

    # ------------------------------------------------------------------ #
    # Role rule parsing                                                    #
    # ------------------------------------------------------------------ #

    def test_role_parsing_path_only(self):
        rules, inherits = self.plugin._parse_role_rules("/admin")
        assert len(rules) == 1
        assert rules[0] == (None, "/admin")
        assert inherits == []

    def test_role_parsing_method_and_path(self):
        rules, inherits = self.plugin._parse_role_rules("GET /admin")
        assert len(rules) == 1
        assert rules[0] == ("GET", "/admin")
        assert inherits == []

    def test_role_inheritance_parsing(self):
        rules, inherits = self.plugin._parse_role_rules("GET /admin, [manager]")
        assert len(rules) == 1
        assert rules[0] == ("GET", "/admin")
        assert "manager" in inherits

    def test_role_parsing_combined(self):
        rules, inherits = self.plugin._parse_role_rules(
            "GET /admin, POST /admin, /admin, [manager], [viewer]"
        )
        assert len(rules) == 3
        assert ("GET", "/admin") in rules
        assert ("POST", "/admin") in rules
        assert (None, "/admin") in rules
        assert set(inherits) == {"manager", "viewer"}

    # ------------------------------------------------------------------ #
    # Transitive closure                                                   #
    # ------------------------------------------------------------------ #

    def test_inheritance_transitive_closure(self):
        self.plugin.configure({
            "pubkey_path": "/etc/test.pem",
            "role.admin": "GET /admin, [manager]",
            "role.manager": "DELETE /orders, [viewer]",
            "role.viewer": "GET /public",
        })
        satisfiers = self.plugin._compute_satisfiers()

        # admin has no inheritors — only itself satisfies admin requirements
        assert satisfiers["admin"] == {"admin"}

        # manager: manager + admin (admin inherits manager)
        assert "manager" in satisfiers["manager"]
        assert "admin" in satisfiers["manager"]
        assert "viewer" not in satisfiers["manager"]

        # viewer: all three (manager inherits viewer; admin inherits manager)
        assert "viewer" in satisfiers["viewer"]
        assert "manager" in satisfiers["viewer"]
        assert "admin" in satisfiers["viewer"]

    # ------------------------------------------------------------------ #
    # JWT validation config                                                #
    # ------------------------------------------------------------------ #

    def test_generates_jwt_validation_json_errors(self):
        self.plugin.configure(base_config())
        result = self.plugin.process(make_context())

        cfg = result.haproxy_config
        assert "deny_status 401" in cfg
        assert "content-type 'application/json'" in cfg
        assert '"error"' in cfg
        assert "Missing Authorization HTTP header" in cfg
        assert "Unsupported JWT signing algorithm" in cfg
        assert "Invalid JWT issuer" in cfg
        assert "Invalid JWT audience" in cfg
        assert "Invalid JWT signature" in cfg
        assert "JWT has expired" in cfg

    def test_generates_required_claim_validation(self):
        self.plugin.configure(base_config())
        result = self.plugin.process(make_context())

        cfg = result.haproxy_config
        assert "Missing required claim: userid" in cfg
        assert "Missing required claim: role" in cfg
        assert "Missing required claim: name" in cfg
        assert "var(txn.userid) -m len gt 0" in cfg
        assert "var(txn.role) -m len gt 0" in cfg
        assert "var(txn.name) -m len gt 0" in cfg

    def test_generates_required_claim_headers(self):
        self.plugin.configure(base_config())
        result = self.plugin.process(make_context())

        cfg = result.haproxy_config
        assert "X-Auth-Userid" in cfg
        assert "X-Auth-Role" in cfg
        assert "X-Auth-Name" in cfg
        assert "%[var(txn.userid)]" in cfg
        assert "%[var(txn.role)]" in cfg
        assert "%[var(txn.name)]" in cfg

    # ------------------------------------------------------------------ #
    # RBAC — permissive mode                                               #
    # ------------------------------------------------------------------ #

    def test_generates_permissive_rbac(self):
        self.plugin.configure(base_config(**{
            "role.admin": "GET /admin, /admin, [manager]",
            "role.manager": "DELETE /orders",
            "strict_roles": "false",
        }))
        result = self.plugin.process(make_context())

        cfg = result.haproxy_config
        assert "RBAC - permissive mode" in cfg
        assert "protect_legacy_has_admin" in cfg
        assert "protect_legacy_has_manager" in cfg
        # admin rule: deny unless has_admin
        assert "!protect_legacy_has_admin" in cfg
        # manager rule: deny unless has_manager OR has_admin (admin inherits manager)
        assert "!protect_legacy_has_manager" in cfg
        # Strict set-var pattern must NOT appear in permissive mode
        assert "set-var(txn.pl_allowed)" not in cfg
        assert "deny_status 403" in cfg

    def test_permissive_rbac_deny_includes_inherited_roles(self):
        self.plugin.configure(base_config(**{
            "role.admin": "GET /admin, [manager]",
            "role.manager": "DELETE /orders",
            "strict_roles": "false",
        }))
        result = self.plugin.process(make_context())
        cfg = result.haproxy_config

        # The manager rule's deny condition must include !has_admin
        # (admin satisfies manager requirements via inheritance)
        manager_rule_line = next(
            l for l in cfg.splitlines()
            if "protect_legacy_role_manager_0_path" in l
            and "deny" in l
        )
        assert "!protect_legacy_has_manager" in manager_rule_line
        assert "!protect_legacy_has_admin" in manager_rule_line

    # ------------------------------------------------------------------ #
    # RBAC — strict mode                                                   #
    # ------------------------------------------------------------------ #

    def test_generates_strict_rbac(self):
        self.plugin.configure(base_config(**{
            "role.admin": "GET /admin",
            "role.manager": "DELETE /orders",
            "strict_roles": "true",
        }))
        result = self.plugin.process(make_context())

        cfg = result.haproxy_config
        assert "RBAC - strict mode" in cfg
        assert "set-var(txn.pl_allowed) str(1)" in cfg
        assert "unless { var(txn.pl_allowed) -m str 1 }" in cfg
        assert "deny_status 403" in cfg
        # Permissive deny pattern must NOT appear
        assert "!protect_legacy_has_" not in cfg

    def test_strict_rbac_generates_allow_for_inherited_roles(self):
        self.plugin.configure(base_config(**{
            "role.admin": "GET /admin, [manager]",
            "role.manager": "DELETE /orders",
            "strict_roles": "true",
        }))
        result = self.plugin.process(make_context())
        cfg = result.haproxy_config

        # manager's DELETE /orders rule must generate set-var for both
        # protect_legacy_has_manager and protect_legacy_has_admin
        allow_lines = [l for l in cfg.splitlines() if "set-var(txn.pl_allowed)" in l]
        manager_allows = [l for l in allow_lines if "protect_legacy_role_manager_0" in l]
        roles_present = {
            "admin" if "protect_legacy_has_admin" in l else "manager"
            for l in manager_allows
        }
        assert "admin" in roles_present
        assert "manager" in roles_present

    # ------------------------------------------------------------------ #
    # Forward claims                                                       #
    # ------------------------------------------------------------------ #

    def test_generates_forward_claims_headers(self):
        self.plugin.configure(base_config(**{"forward_claims": "email,tenant"}))
        result = self.plugin.process(make_context())

        cfg = result.haproxy_config
        assert "X-Auth-Email" in cfg
        assert "X-Auth-Tenant" in cfg
        assert "jwt_payload_query('$.email')" in cfg
        assert "jwt_payload_query('$.tenant')" in cfg

    def test_scope_header_present_when_rbac_configured(self):
        self.plugin.configure(base_config(**{"role.admin": "GET /admin"}))
        result = self.plugin.process(make_context())

        cfg = result.haproxy_config
        assert "X-Auth-Scope" in cfg
        assert "var(txn.scope)" in cfg

    def test_scope_header_absent_when_no_rbac(self):
        self.plugin.configure(base_config())
        result = self.plugin.process(make_context())

        cfg = result.haproxy_config
        assert "X-Auth-Scope" not in cfg

    # ------------------------------------------------------------------ #
    # Custom claim names                                                   #
    # ------------------------------------------------------------------ #

    def test_custom_claim_names(self):
        self.plugin.configure(base_config(**{
            "claim_userid": "sub",
            "claim_role": "scope",
            "claim_name": "preferred_username",
        }))
        result = self.plugin.process(make_context())

        cfg = result.haproxy_config
        assert "jwt_payload_query('$.sub')" in cfg
        assert "jwt_payload_query('$.scope')" in cfg
        assert "jwt_payload_query('$.preferred_username')" in cfg
        assert "Missing required claim: sub" in cfg
        assert "Missing required claim: scope" in cfg
        assert "Missing required claim: preferred_username" in cfg

    # ------------------------------------------------------------------ #
    # Edge cases: disabled and no pubkey                                   #
    # ------------------------------------------------------------------ #

    def test_disabled(self):
        self.plugin.configure({"enabled": "false", "pubkey_path": "/etc/test.pem"})
        result = self.plugin.process(make_context())

        assert result.haproxy_config == ""

    def test_no_pubkey(self):
        self.plugin.configure({"algorithm": "RS256", "issuer": "https://auth.example.com/"})
        result = self.plugin.process(make_context())

        assert result.haproxy_config == ""

    def test_pubkey_path_appears_in_verify_line(self):
        self.plugin.configure(base_config())
        result = self.plugin.process(make_context())

        assert "/etc/easyhaproxy/jwt_keys/test.pem" in result.haproxy_config
        assert "jwt_verify" in result.haproxy_config

    def test_allow_anonymous_skips_auth_header_check(self):
        self.plugin.configure(base_config(**{"allow_anonymous": "true"}))
        result = self.plugin.process(make_context())

        assert "Missing Authorization HTTP header" not in result.haproxy_config
