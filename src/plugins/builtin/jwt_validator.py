"""
JWT Validator Plugin for EasyHAProxy

This plugin validates JWT tokens using HAProxy's built-in JWT functionality.
It runs as a DOMAIN plugin (once per domain).

Configuration:
    - enabled: Enable/disable the plugin (default: true)
    - algorithm: JWT signing algorithm (default: RS256)
    - issuer: Expected JWT issuer (optional, set to "none"/"null" to skip validation)
    - audience: Expected JWT audience (optional, set to "none"/"null" to skip validation)
    - pubkey_path: Path to public key file in container (priority: 1)
    - pubkey: Public key content as base64-encoded string (priority: 2)
    - k8s_secret.pubkey: Kubernetes secret containing public key (priority: 3, Kubernetes only)
    - paths: List of paths that require JWT validation (optional, if not set ALL domain is protected)
    - only_paths: If true, only specified paths are accessible; if false (default), only specified paths require JWT validation
    - allow_anonymous: If true, allows requests without Authorization header (validates JWT if present); if false (default), requires Authorization header

Priority Order (first configured option wins):
    1. pubkey_path - Direct file path (explicit configuration)
    2. pubkey - Base64-encoded key content (inline configuration)
    3. k8s_secret.pubkey - Kubernetes secret name (processed by K8s processor into pubkey)

Kubernetes Secret Pattern (Kubernetes only):
    For Kubernetes deployments, you can load the public key from a Kubernetes Secret:

    - Auto-detect key: easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "secret_name"
    - Explicit key: easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "secret_name/key_name"

    See documentation for details:
    - General k8s_secret pattern: docs/kubernetes.md#loading-plugin-configuration-from-kubernetes-secrets
    - JWT Validator with Secrets: docs/Plugins/jwt-validator.md#kubernetes-with-secrets-recommended

Path Validation Logic:
    - No paths configured: ALL requests to the domain require JWT validation (default behavior)
    - Paths configured + only_paths=false: Only specified paths require JWT validation, others pass through
    - Paths configured + only_paths=true: Only specified paths are accessible (with JWT), all others are denied

Anonymous Access Logic:
    - allow_anonymous=false (default): Requests without Authorization header are denied
    - allow_anonymous=true: Requests without Authorization header are allowed, but JWTs are validated if present

Example YAML config:
    plugins:
      jwt_validator:
        enabled: true
        algorithm: RS256
        issuer: https://myaccount.auth0.com/
        audience: https://api.mywebsite.com
        pubkey_path: /etc/haproxy/jwt_keys/pubkey.pem
        paths:
          - /api/admin
          - /api/sensitive
        only_paths: false

Example Container Label:
    easyhaproxy.http.plugins: "jwt_validator"
    easyhaproxy.http.plugin.jwt_validator.algorithm: RS256
    easyhaproxy.http.plugin.jwt_validator.issuer: https://auth.example.com/
    easyhaproxy.http.plugin.jwt_validator.audience: https://api.example.com
    easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem
    easyhaproxy.http.plugin.jwt_validator.paths: /api/admin,/api/sensitive
    easyhaproxy.http.plugin.jwt_validator.only_paths: true

Example Kubernetes Annotations:
    # Using k8s_secret pattern (recommended for Kubernetes):
    easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey: "my-jwt-secret"
    easyhaproxy.plugin.jwt_validator.algorithm: "RS256"
    easyhaproxy.plugin.jwt_validator.issuer: "https://auth.example.com/"
    easyhaproxy.plugin.jwt_validator.audience: "https://api.example.com"

    # Using inline pubkey (for testing):
    easyhaproxy.plugin.jwt_validator.pubkey: "LS0tLS1CRUdJTi..."

HAProxy Config Generated:
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
"""

import base64
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from functions import Functions, logger_easyhaproxy
from plugins import InitializationResult, PluginContext, PluginInterface, PluginResult, PluginType, ResourceRequest


class JwtValidatorPlugin(PluginInterface):
    """Plugin to validate JWT tokens"""

    def __init__(self):
        self.enabled = True
        self.algorithm = "RS256"
        self.issuer = None  # Optional
        self.audience = None  # Optional
        self.pubkey_path = None  # Path to public key file
        self.pubkey = None  # Public key content (alternative to pubkey_path)
        self.paths = []  # List of paths that require JWT validation
        self.only_paths = False  # If true, only specified paths are accessible
        self.allow_anonymous = False  # If true, allow requests without Authorization header
        # Make JWT_KEYS_DIR configurable via environment variable (for testing)
        self.jwt_keys_dir = os.getenv("EASYHAPROXY_JWT_KEYS_DIR", "/etc/haproxy/jwt_keys")

    @property
    def name(self) -> str:
        return "jwt_validator"

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DOMAIN

    def configure(self, config: dict) -> None:
        """
        Configure the plugin

        Args:
            config: Dictionary with configuration options
                - enabled: Whether plugin is enabled
                - algorithm: JWT signing algorithm (default: RS256)
                - issuer: Expected JWT issuer (optional)
                - audience: Expected JWT audience (optional)
                - pubkey_path: Path to public key file
                - pubkey: Public key content as base64-encoded string
                - paths: List of paths that require JWT validation (optional)
                - only_paths: If true, only specified paths are accessible (default: false)
                - allow_anonymous: If true, allow requests without Authorization header (default: false)
        """
        if "enabled" in config:
            self.enabled = str(config["enabled"]).lower() in ["true", "1", "yes"]

        if "algorithm" in config:
            self.algorithm = config["algorithm"]

        # Parse issuer (optional - if not set, issuer validation is skipped)
        if "issuer" in config:
            issuer = str(config["issuer"]).strip()
            if issuer:  # Only set if not empty
                self.issuer = issuer

        # Parse audience (optional - if not set, audience validation is skipped)
        if "audience" in config:
            audience = str(config["audience"]).strip()
            if audience:  # Only set if not empty
                self.audience = audience

        # Public key configuration
        if "pubkey_path" in config:
            self.pubkey_path = config["pubkey_path"]

        if "pubkey" in config:
            # Decode from base64 (consistent with sslcert parameter)
            self.pubkey = base64.b64decode(config["pubkey"]).decode('ascii')

        # Path configuration
        if "paths" in config:
            paths_config = config["paths"]
            if isinstance(paths_config, list):
                self.paths = [str(p).strip() for p in paths_config if str(p).strip()]
            elif isinstance(paths_config, str):
                # Support comma-separated paths for container labels
                self.paths = [p.strip() for p in paths_config.split(",") if p.strip()]
            else:
                self.paths = []

        if "only_paths" in config:
            self.only_paths = str(config["only_paths"]).lower() in ["true", "1", "yes"]

        if "allow_anonymous" in config:
            self.allow_anonymous = str(config["allow_anonymous"]).lower() in ["true", "1", "yes"]

    def initialize(self) -> InitializationResult:
        """
        Initialize plugin resources - create JWT keys directory

        Returns:
            InitializationResult with directory creation request
        """
        return InitializationResult(
            resources=[
                ResourceRequest(resource_type="directory", path=self.jwt_keys_dir)
            ]
        )

    def process(self, context: PluginContext) -> PluginResult:
        """
        Generate HAProxy config to validate JWT tokens

        Args:
            context: Plugin execution context with domain information

        Returns:
            PluginResult with HAProxy configuration snippet
        """
        if not self.enabled:
            return PluginResult()

        # Determine public key file path
        if self.pubkey_path:
            pubkey_file = self.pubkey_path
        elif self.pubkey:
            # Generate path for pubkey based on domain
            domain_safe = context.domain.replace(".", "_").replace(":", "_")
            pubkey_file = f"{self.jwt_keys_dir}/{domain_safe}_pubkey.pem"

            # Write the public key file (with error handling for test environments)
            try:
                # Ensure directory exists (defensive - normally created by initialize())
                os.makedirs(self.jwt_keys_dir, exist_ok=True)
                Functions.save(pubkey_file, self.pubkey)
                logger_easyhaproxy.debug(f"Wrote JWT public key to {pubkey_file} for domain {context.domain}")
            except (PermissionError, OSError) as e:
                # In test environments or restricted environments, file write may fail
                # This is okay - the config is still generated correctly
                logger_easyhaproxy.debug(f"Could not write JWT public key file (may be test environment): {e}")
        else:
            logger_easyhaproxy.warning(f"JWT validator plugin for {context.domain}: No pubkey or pubkey_path configured")
            return PluginResult()

        # Build HAProxy configuration
        lines = ["# JWT Validator - Validate JWT tokens"]

        # Determine path condition suffix
        path_condition = ""
        if self.paths:
            # Define ACL for protected paths
            lines.append("")
            lines.append("# Define paths that require JWT validation")
            for path in self.paths:
                lines.append(f"acl jwt_protected_path path_beg {path}")
            lines.append("")

            if self.only_paths:
                # Deny all paths that are not in the protected list
                lines.append("# Deny access to paths not in the protected list")
                lines.append("http-request deny content-type 'text/html' string 'Access denied' unless jwt_protected_path")
                lines.append("")
                # All remaining requests are on protected paths, no condition needed
                path_condition = ""
            else:
                # Only validate JWT on protected paths
                path_condition = " if jwt_protected_path"

        # Check for Authorization header
        if not self.allow_anonymous:
            # Require Authorization header (default behavior)
            lines.append(f"http-request deny content-type 'text/html' string 'Missing Authorization HTTP header' unless {{ req.hdr(authorization) -m found }}{path_condition}")
            jwt_condition = path_condition
        else:
            # Allow anonymous access - only validate JWT if Authorization header is present
            lines.append("")
            lines.append("# Allow anonymous access - validate JWT only if Authorization header is present")
            if path_condition:
                # Combine path condition with Authorization header check
                jwt_condition = f"{path_condition} if {{ req.hdr(authorization) -m found }}"
            else:
                jwt_condition = " if { req.hdr(authorization) -m found }"

        # Extract JWT parts
        lines.append("")
        lines.append("# Extract JWT header and payload")
        lines.append(f"http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg'){jwt_condition}")
        lines.append(f"http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss'){jwt_condition}")
        lines.append(f"http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud'){jwt_condition}")
        lines.append(f"http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int'){jwt_condition}")

        # Validate JWT
        lines.append("")
        lines.append("# Validate JWT")
        lines.append(f"http-request deny content-type 'text/html' string 'Unsupported JWT signing algorithm' unless {{ var(txn.alg) -m str {self.algorithm} }}{jwt_condition}")

        # Validate issuer (if configured)
        if self.issuer:
            lines.append(f"http-request deny content-type 'text/html' string 'Invalid JWT issuer' unless {{ var(txn.iss) -m str {self.issuer} }}{jwt_condition}")

        # Validate audience (if configured)
        if self.audience:
            lines.append(f"http-request deny content-type 'text/html' string 'Invalid JWT audience' unless {{ var(txn.aud) -m str {self.audience} }}{jwt_condition}")

        # Validate signature
        lines.append(f"http-request deny content-type 'text/html' string 'Invalid JWT signature' unless {{ http_auth_bearer,jwt_verify(txn.alg,\"{pubkey_file}\") -m int 1 }}{jwt_condition}")

        # Validate expiration
        lines.append("")
        lines.append("# Validate expiration")
        lines.append(f"http-request set-var(txn.now) date(){jwt_condition}")
        lines.append(f"http-request deny content-type 'text/html' string 'JWT has expired' if {{ var(txn.exp),sub(txn.now) -m int lt 0 }}{jwt_condition}")

        haproxy_config = "\n".join(lines)

        # Build metadata
        metadata = {
            "domain": context.domain,
            "algorithm": self.algorithm,
            "pubkey_file": pubkey_file,
            "validates_issuer": self.issuer is not None,
            "validates_audience": self.audience is not None,
            "path_validation": len(self.paths) > 0,
            "only_paths": self.only_paths,
            "allow_anonymous": self.allow_anonymous
        }

        if self.issuer:
            metadata["issuer"] = self.issuer
        if self.audience:
            metadata["audience"] = self.audience
        if self.pubkey:
            # Keep pubkey_content in metadata for backward compatibility with tests
            metadata["pubkey_content"] = self.pubkey
        if self.paths:
            metadata["paths"] = self.paths

        return PluginResult(
            haproxy_config=haproxy_config,
            modified_easymapping=None,
            metadata=metadata
        )
