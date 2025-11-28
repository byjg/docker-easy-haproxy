"""
JWT Validator Plugin for EasyHAProxy

This plugin validates JWT tokens using HAProxy's built-in JWT functionality.
It runs as a DOMAIN plugin (once per domain).

Configuration:
    - enabled: Enable/disable the plugin (default: true)
    - algorithm: JWT signing algorithm (default: RS256)
    - issuer: Expected JWT issuer (optional, set to "none"/"null" to skip validation)
    - audience: Expected JWT audience (optional, set to "none"/"null" to skip validation)
    - pubkey_path: Path to public key file (required if pubkey not provided)
    - pubkey: Public key content as string (required if pubkey_path not provided)

Example YAML config:
    plugins:
      jwt_validator:
        enabled: true
        algorithm: RS256
        issuer: https://myaccount.auth0.com/
        audience: https://api.mywebsite.com
        pubkey_path: /etc/haproxy/jwt_keys/pubkey.pem

Example Container Label:
    easyhaproxy.http.plugins: "jwt_validator"
    easyhaproxy.http.plugin.jwt_validator.algorithm: RS256
    easyhaproxy.http.plugin.jwt_validator.issuer: https://auth.example.com/
    easyhaproxy.http.plugin.jwt_validator.audience: https://api.example.com
    easyhaproxy.http.plugin.jwt_validator.pubkey_path: /etc/haproxy/jwt_keys/api_pubkey.pem

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

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import PluginInterface, PluginType, PluginContext, PluginResult
from functions import loggerEasyHaproxy


class JwtValidatorPlugin(PluginInterface):
    """Plugin to validate JWT tokens"""

    def __init__(self):
        self.enabled = True
        self.algorithm = "RS256"
        self.issuer = None  # Optional
        self.audience = None  # Optional
        self.pubkey_path = None  # Path to public key file
        self.pubkey = None  # Public key content (alternative to pubkey_path)

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
                - pubkey: Public key content as string
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
            self.pubkey = config["pubkey"]

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
            pubkey_file = f"/etc/haproxy/jwt_keys/{domain_safe}_pubkey.pem"
        else:
            loggerEasyHaproxy.warning(f"JWT validator plugin for {context.domain}: No pubkey or pubkey_path configured")
            return PluginResult()

        # Build HAProxy configuration
        lines = ["# JWT Validator - Validate JWT tokens"]

        # Check for Authorization header
        lines.append("http-request deny content-type 'text/html' string 'Missing Authorization HTTP header' unless { req.hdr(authorization) -m found }")

        # Extract JWT parts
        lines.append("")
        lines.append("# Extract JWT header and payload")
        lines.append("http-request set-var(txn.alg) http_auth_bearer,jwt_header_query('$.alg')")
        lines.append("http-request set-var(txn.iss) http_auth_bearer,jwt_payload_query('$.iss')")
        lines.append("http-request set-var(txn.aud) http_auth_bearer,jwt_payload_query('$.aud')")
        lines.append("http-request set-var(txn.exp) http_auth_bearer,jwt_payload_query('$.exp','int')")

        # Validate JWT
        lines.append("")
        lines.append("# Validate JWT")
        lines.append(f"http-request deny content-type 'text/html' string 'Unsupported JWT signing algorithm' unless {{ var(txn.alg) -m str {self.algorithm} }}")

        # Validate issuer (if configured)
        if self.issuer:
            lines.append(f"http-request deny content-type 'text/html' string 'Invalid JWT issuer' unless {{ var(txn.iss) -m str {self.issuer} }}")

        # Validate audience (if configured)
        if self.audience:
            lines.append(f"http-request deny content-type 'text/html' string 'Invalid JWT audience' unless {{ var(txn.aud) -m str {self.audience} }}")

        # Validate signature
        lines.append(f"http-request deny content-type 'text/html' string 'Invalid JWT signature' unless {{ http_auth_bearer,jwt_verify(txn.alg,\"{pubkey_file}\") -m int 1 }}")

        # Validate expiration
        lines.append("")
        lines.append("# Validate expiration")
        lines.append("http-request set-var(txn.now) date()")
        lines.append("http-request deny content-type 'text/html' string 'JWT has expired' if { var(txn.exp),sub(txn.now) -m int lt 0 }")

        haproxy_config = "\n".join(lines)

        # Build metadata
        metadata = {
            "domain": context.domain,
            "algorithm": self.algorithm,
            "pubkey_file": pubkey_file,
            "validates_issuer": self.issuer is not None,
            "validates_audience": self.audience is not None
        }

        if self.issuer:
            metadata["issuer"] = self.issuer
        if self.audience:
            metadata["audience"] = self.audience
        if self.pubkey:
            metadata["pubkey_content"] = self.pubkey

        return PluginResult(
            haproxy_config=haproxy_config,
            modified_easymapping=None,
            metadata=metadata
        )
