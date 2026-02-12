"""
Tests for Kubernetes Processor - k8s_secret functionality

Tests the generic k8s_secret annotation pattern that allows loading
plugin configuration values from Kubernetes Secrets.
"""

import base64
import os
import sys
from unittest.mock import MagicMock, Mock
from types import SimpleNamespace

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processor import Kubernetes


class TestKubernetesSecretPattern:
    """Test cases for k8s_secret annotation pattern"""

    def create_mock_secret(self, data):
        """Helper to create a mock Kubernetes secret"""
        secret = Mock()
        # Kubernetes stores secret data as base64-encoded strings
        secret.data = {
            key: base64.b64encode(value.encode('ascii')).decode('ascii')
            for key, value in data.items()
        }
        return secret

    def create_mock_ingress(self, annotations, namespace="default"):
        """Helper to create a mock Kubernetes ingress"""
        ingress = Mock()
        ingress.metadata = Mock()
        ingress.metadata.namespace = namespace
        ingress.metadata.name = "test-ingress"
        ingress.metadata.annotations = annotations
        ingress.metadata.creation_timestamp = Mock()
        ingress.metadata.creation_timestamp.strftime = Mock(return_value="01/01/2024 00:00:00")
        ingress.metadata.resource_version = "12345"
        ingress.spec = Mock()
        ingress.spec.tls = None
        ingress.spec.ingress_class_name = "easyhaproxy"

        # Create a proper rule with path and backend
        rule = Mock()
        rule.host = "test.example.com"
        rule.http = Mock()

        path = Mock()
        path.path = "/"
        path.path_type = "Prefix"
        path.backend = Mock()
        path.backend.service = Mock()
        path.backend.service.name = "test-service"
        path.backend.service.port = Mock()
        path.backend.service.port.number = 8080

        rule.http.paths = [path]
        ingress.spec.rules = [rule]

        return ingress

    def test_k8s_secret_auto_detect_exact_match(self):
        """Test k8s_secret with auto-detect finds exact key match"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Create a secret with exact key name "pubkey"
        secret = self.create_mock_secret({"pubkey": "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----"})
        mock_core_api.read_namespaced_secret.return_value = secret

        # Create ingress with k8s_secret annotation (auto-detect format)
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "jwt_validator",
            "easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey": "my-jwt-secret"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients (refresh is called automatically in __init__)
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Verify secret was read
        mock_core_api.read_namespaced_secret.assert_called_once_with("my-jwt-secret", "default")

        # Verify the annotation was transformed correctly
        parsed = processor.get_parsed_object()
        assert len(parsed) == 1, f"Expected 1 entry in parsed_object, got {len(parsed)}: {list(parsed.keys())}"
        # parsed_object is a dict with IP addresses as keys, get the first (and only) value
        ingress_data = list(parsed.values())[0]

        # The k8s_secret annotation should have been transformed and stored in the ingress data
        # Format: easyhaproxy.{host}_{port}.plugin.{plugin_name}.{key}
        # For test.example.com:8080 -> easyhaproxy.test-example-com_8080.plugin.jwt_validator.pubkey
        assert "easyhaproxy.test-example-com_8080.plugin.jwt_validator.pubkey" in ingress_data
        # The value should be base64-encoded (double encoding: K8s decodes, we re-encode for plugin)
        assert ingress_data["easyhaproxy.test-example-com_8080.plugin.jwt_validator.pubkey"] is not None

    def test_k8s_secret_auto_detect_variation_match(self):
        """Test k8s_secret with auto-detect finds variation key"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Create a secret with variation key name "public-key" instead of "pubkey"
        secret = self.create_mock_secret({"public-key": "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----"})
        mock_core_api.read_namespaced_secret.return_value = secret

        # Create ingress with k8s_secret annotation (auto-detect format)
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "jwt_validator",
            "easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey": "my-jwt-secret"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients (refresh is called automatically in __init__)
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Verify secret was read
        mock_core_api.read_namespaced_secret.assert_called_once_with("my-jwt-secret", "default")

        # Verify the annotation was transformed correctly
        parsed = processor.get_parsed_object()
        assert len(parsed) == 1, f"Expected 1 entry in parsed_object, got {len(parsed)}: {list(parsed.keys())}"
        # parsed_object is a dict with IP addresses as keys, get the first (and only) value
        ingress_data = list(parsed.values())[0]

        # Should find the "public-key" variation
        assert "easyhaproxy.test-example-com_8080.plugin.jwt_validator.pubkey" in ingress_data

    def test_k8s_secret_explicit_key(self):
        """Test k8s_secret with explicit key name (secret_name/key_name format)"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Create a secret with custom key name
        secret = self.create_mock_secret({"rsa-public-key": "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----"})
        mock_core_api.read_namespaced_secret.return_value = secret

        # Create ingress with explicit key format
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "jwt_validator",
            "easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey": "my-jwt-secret/rsa-public-key"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients (refresh is called automatically in __init__)
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Verify secret was read
        mock_core_api.read_namespaced_secret.assert_called_once_with("my-jwt-secret", "default")

        # Verify the annotation was transformed correctly
        parsed = processor.get_parsed_object()
        assert len(parsed) == 1, f"Expected 1 entry in parsed_object, got {len(parsed)}: {list(parsed.keys())}"
        # parsed_object is a dict with IP addresses as keys, get the first (and only) value
        ingress_data = list(parsed.values())[0]

        # Should use the explicit key
        assert "easyhaproxy.test-example-com_8080.plugin.jwt_validator.pubkey" in ingress_data

    def test_k8s_secret_explicit_key_no_variations(self):
        """Test k8s_secret with explicit key doesn't try variations"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Create a secret with ONLY "public-key", not "custom-key"
        secret = self.create_mock_secret({"public-key": "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----"})
        mock_core_api.read_namespaced_secret.return_value = secret

        # Create ingress with explicit key that doesn't exist
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "jwt_validator",
            "easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey": "my-jwt-secret/custom-key"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients (refresh is called automatically in __init__)
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Verify secret was read
        mock_core_api.read_namespaced_secret.assert_called_once_with("my-jwt-secret", "default")

        # Verify the annotation was NOT created (explicit key not found, no variations tried)
        parsed = processor.get_parsed_object()
        assert len(parsed) == 1
        ingress_data = list(parsed.values())[0]

        # Should NOT have the pubkey annotation (explicit key not found)
        assert "easyhaproxy.test-example-com_8080.plugin.jwt_validator.pubkey" not in ingress_data

    def test_k8s_secret_priority_explicit_annotation_wins(self):
        """Test that explicit annotation overrides k8s_secret annotation"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Create a secret
        secret = self.create_mock_secret({"pubkey": "-----BEGIN PUBLIC KEY-----\nfrom-secret\n-----END PUBLIC KEY-----"})
        mock_core_api.read_namespaced_secret.return_value = secret

        # Create ingress with BOTH explicit pubkey AND k8s_secret.pubkey
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "jwt_validator",
            "easyhaproxy.plugin.jwt_validator.pubkey": base64.b64encode(b"explicit-value").decode('ascii'),
            "easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey": "my-jwt-secret"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Verify the annotation kept the explicit value (not replaced by secret)
        parsed = processor.get_parsed_object()
        assert len(parsed) == 1
        ingress_data = list(parsed.values())[0]

        # Should have the explicit annotation value, NOT the secret value
        explicit_value = base64.b64encode(b"explicit-value").decode('ascii')
        assert ingress_data.get("easyhaproxy.test-example-com_8080.plugin.jwt_validator.pubkey") == explicit_value

    def test_k8s_secret_secret_not_found(self):
        """Test k8s_secret handles secret not found gracefully"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Simulate secret not found
        from kubernetes.client.rest import ApiException
        mock_core_api.read_namespaced_secret.side_effect = ApiException(status=404, reason="Not Found")

        # Create ingress with k8s_secret annotation
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "jwt_validator",
            "easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey": "nonexistent-secret"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Should not raise exception, just log warning

        # Verify the annotation was NOT created
        parsed = processor.get_parsed_object()
        assert len(parsed) == 1
        ingress_data = list(parsed.values())[0]

        # Should NOT have pubkey annotation
        assert "easyhaproxy.test-example-com_8080.plugin.jwt_validator.pubkey" not in ingress_data

    def test_k8s_secret_key_not_found(self):
        """Test k8s_secret handles key not found in secret gracefully"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Create a secret with NO matching keys
        secret = self.create_mock_secret({"some-other-key": "value"})
        mock_core_api.read_namespaced_secret.return_value = secret

        # Create ingress with k8s_secret annotation
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "jwt_validator",
            "easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey": "my-secret"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Verify the annotation was NOT created
        parsed = processor.get_parsed_object()
        assert len(parsed) == 1
        ingress_data = list(parsed.values())[0]

        # Should NOT have pubkey annotation (no matching keys)
        assert "easyhaproxy.test-example-com_8080.plugin.jwt_validator.pubkey" not in ingress_data

    def test_k8s_secret_multiple_plugins(self):
        """Test k8s_secret works with multiple plugins"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Create different secrets for different plugins
        def get_secret(name, namespace):
            if name == "jwt-secret":
                return self.create_mock_secret({"pubkey": "jwt-public-key"})
            elif name == "api-secret":
                return self.create_mock_secret({"api_key": "secret-api-key"})
            raise Exception("Secret not found")

        mock_core_api.read_namespaced_secret.side_effect = get_secret

        # Create ingress with multiple k8s_secret annotations
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "jwt_validator,api_auth",
            "easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey": "jwt-secret",
            "easyhaproxy.plugin.api_auth.k8s_secret.api_key": "api-secret"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Verify both secrets were read
        assert mock_core_api.read_namespaced_secret.call_count == 2

        # Verify both annotations were transformed
        parsed = processor.get_parsed_object()
        assert len(parsed) == 1
        ingress_data = list(parsed.values())[0]

        assert "easyhaproxy.test-example-com_8080.plugin.jwt_validator.pubkey" in ingress_data
        assert "easyhaproxy.test-example-com_8080.plugin.api_auth.api_key" in ingress_data

    def test_k8s_secret_namespace_isolation(self):
        """Test k8s_secret reads secrets from same namespace as ingress"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        secret = self.create_mock_secret({"pubkey": "test-key"})
        mock_core_api.read_namespaced_secret.return_value = secret

        # Create ingress in "production" namespace
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "jwt_validator",
            "easyhaproxy.plugin.jwt_validator.k8s_secret.pubkey": "my-secret"
        }, namespace="production")
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Verify secret was read from correct namespace
        mock_core_api.read_namespaced_secret.assert_called_once_with("my-secret", "production")

    def test_k8s_secret_malformed_annotation(self):
        """Test k8s_secret handles malformed annotation gracefully"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Create ingress with malformed k8s_secret annotation
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "jwt_validator",
            # Malformed: multiple k8s_secret in the key
            "easyhaproxy.plugin.k8s_secret.jwt_validator.k8s_secret.pubkey": "my-secret"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Should not raise exception

        # Verify no secret read was attempted
        mock_core_api.read_namespaced_secret.assert_not_called()

    def test_k8s_secret_password_variations(self):
        """Test k8s_secret auto-detect variations for password key"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Create a secret with "pass" instead of "password"
        secret = self.create_mock_secret({"pass": "secret-password"})
        mock_core_api.read_namespaced_secret.return_value = secret

        # Create ingress requesting "password" key (should find "pass" variation)
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "auth_plugin",
            "easyhaproxy.plugin.auth_plugin.k8s_secret.password": "my-secret"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Verify the annotation was created (variation found)
        parsed = processor.get_parsed_object()
        assert len(parsed) == 1
        ingress_data = list(parsed.values())[0]

        assert "easyhaproxy.test-example-com_8080.plugin.auth_plugin.password" in ingress_data

    def test_k8s_secret_api_key_variations(self):
        """Test k8s_secret auto-detect variations for api_key"""
        # Setup mocks
        mock_core_api = MagicMock()
        mock_networking_api = MagicMock()

        # Create a secret with "apikey" instead of "api_key"
        secret = self.create_mock_secret({"apikey": "secret-key-123"})
        mock_core_api.read_namespaced_secret.return_value = secret

        # Create ingress requesting "api_key" (should find "apikey" variation)
        ingress = self.create_mock_ingress({
            "easyhaproxy.plugins": "api_plugin",
            "easyhaproxy.plugin.api_plugin.k8s_secret.api_key": "my-secret"
        })
        mock_networking_api.list_ingress_for_all_namespaces.return_value = Mock(items=[ingress])

        # Create processor with mocked API clients
        processor = Kubernetes(api_instance=mock_core_api, v1=mock_networking_api)

        # Verify the annotation was created (variation found)
        parsed = processor.get_parsed_object()
        assert len(parsed) == 1
        ingress_data = list(parsed.values())[0]

        assert "easyhaproxy.test-example-com_8080.plugin.api_plugin.api_key" in ingress_data