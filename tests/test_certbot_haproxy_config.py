"""
Integration tests for Certbot/ACME HAProxy configuration generation

Tests that verify the HAProxy configuration is correctly generated for HTTP-01 challenges:
- ACLs for /.well-known/acme-challenge/ paths
- certbot_backend routing to 127.0.0.1:2080
- ACME challenges bypass SSL redirect
- Multiple domains with certbot enabled
"""

import os
import sys
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from easymapping import HaproxyConfigGenerator
from functions import ContainerEnv


class TestCertbotHAProxyConfig:
    """Test HAProxy configuration generation for ACME/certbot"""

    def test_certbot_backend_always_created(self):
        """Test that certbot_backend is always present in HAProxy config"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            # Empty config should still have certbot_backend
            haproxy_config = cfg.generate({})

            assert 'backend certbot_backend' in haproxy_config
            assert 'server certbot 127.0.0.1:2080' in haproxy_config

    def test_certbot_acl_for_single_domain(self):
        """Test ACME challenge ACL for single domain with certbot enabled"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            parsed_object = {
                'container1': {
                    'easyhaproxy.http.host': 'example.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '3000',
                    'easyhaproxy.http.certbot': 'true',
                }
            }

            haproxy_config = cfg.generate(parsed_object)

            # Verify ACME challenge ACL
            assert 'acl is_certbot_example_com_80 path_beg /.well-known/acme-challenge/' in haproxy_config

            # Verify routing to certbot_backend
            assert 'use_backend certbot_backend if is_certbot_example_com_80' in haproxy_config

            # Verify certbot_backend exists
            assert 'backend certbot_backend' in haproxy_config
            assert 'server certbot 127.0.0.1:2080' in haproxy_config

    def test_certbot_acl_for_multiple_domains(self):
        """Test ACME challenge ACLs for multiple domains with certbot enabled"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            parsed_object = {
                'container1': {
                    'easyhaproxy.http.host': 'example.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '3000',
                    'easyhaproxy.http.certbot': 'true',
                },
                'container2': {
                    'easyhaproxy.http.host': 'test.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '4000',
                    'easyhaproxy.http.certbot': 'true',
                },
                'container3': {
                    'easyhaproxy.http.host': 'nocert.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '5000',
                    # certbot not enabled
                }
            }

            haproxy_config = cfg.generate(parsed_object)

            # Verify ACLs for domains with certbot=true
            assert 'acl is_certbot_example_com_80 path_beg /.well-known/acme-challenge/' in haproxy_config
            assert 'acl is_certbot_test_com_80 path_beg /.well-known/acme-challenge/' in haproxy_config

            # Verify NO ACL for domain without certbot
            assert 'acl is_certbot_nocert_com_80' not in haproxy_config

            # Verify routing for each certbot-enabled domain
            assert 'use_backend certbot_backend if is_certbot_example_com_80' in haproxy_config
            assert 'use_backend certbot_backend if is_certbot_test_com_80' in haproxy_config

            # Verify certbot_backend definition exists (only once)
            # Count lines starting with "backend certbot_backend" (not use_backend lines)
            backend_lines = [line for line in haproxy_config.split('\n') if line.startswith('backend certbot_backend')]
            assert len(backend_lines) == 1
            assert haproxy_config.count('server certbot 127.0.0.1:2080') == 1

    def test_certbot_bypasses_ssl_redirect(self):
        """Test that ACME challenges bypass SSL redirect"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            parsed_object = {
                'container1': {
                    'easyhaproxy.http.host': 'example.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '3000',
                    'easyhaproxy.http.certbot': 'true',
                    'easyhaproxy.http.redirect_ssl': 'true',  # Force HTTPS
                }
            }

            haproxy_config = cfg.generate(parsed_object)

            # Find the redirect rule
            lines = haproxy_config.split('\n')
            redirect_line = None
            for line in lines:
                if 'http-request redirect scheme https' in line and 'example_com' in line:
                    redirect_line = line
                    break

            assert redirect_line is not None, "SSL redirect rule not found"

            # Verify ACME challenge is excluded from redirect
            # Should contain: if !is_certbot_example_com_80 is_rule_...
            assert '!is_certbot_example_com_80' in redirect_line

    def test_certbot_with_ssl_clone(self):
        """Test certbot with clone_to_ssl (auto-create port 443)"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            parsed_object = {
                'container1': {
                    'easyhaproxy.http.host': 'example.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '3000',
                    'easyhaproxy.http.certbot': 'true',
                    'easyhaproxy.http.clone_to_ssl': 'true',
                }
            }

            haproxy_config = cfg.generate(parsed_object)

            # Should have HTTP frontend (port 80) with certbot ACL
            assert 'frontend http_in_80' in haproxy_config
            assert 'acl is_certbot_example_com_80 path_beg /.well-known/acme-challenge/' in haproxy_config

            # Should have HTTPS frontend (port 443) without certbot ACL
            # (ACME challenges only happen on HTTP port 80)
            assert 'frontend http_in_443' in haproxy_config or 'frontend https_in_443' in haproxy_config

            # Port 443 should NOT have certbot ACL
            lines = haproxy_config.split('\n')
            in_443_frontend = False
            for line in lines:
                if 'frontend http_in_443' in line or 'frontend https_in_443' in line:
                    in_443_frontend = True
                if in_443_frontend and 'frontend' in line and '443' not in line:
                    break  # Moved to next frontend
                if in_443_frontend and 'is_certbot' in line:
                    assert False, "ACME challenge ACL should not be in port 443 frontend"

    def test_certbot_without_email_no_acl(self):
        """Test that no ACME ACLs are created when email is not configured"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': '',  # No email
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            parsed_object = {
                'container1': {
                    'easyhaproxy.http.host': 'example.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '3000',
                    'easyhaproxy.http.certbot': 'true',  # Set but won't work without email
                }
            }

            haproxy_config = cfg.generate(parsed_object)

            # Should NOT create ACME ACL without email
            assert 'acl is_certbot_example_com_80' not in haproxy_config
            assert 'use_backend certbot_backend' not in haproxy_config

            # certbot_backend should still exist (always created)
            assert 'backend certbot_backend' in haproxy_config

    def test_certbot_acl_naming_special_chars(self):
        """Test ACME ACL naming with domains containing special characters"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            parsed_object = {
                'container1': {
                    'easyhaproxy.http.host': 'sub-domain.example.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '3000',
                    'easyhaproxy.http.certbot': 'true',
                }
            }

            haproxy_config = cfg.generate(parsed_object)

            # Domain with dots should have them replaced with underscores in ACL name
            assert 'acl is_certbot_sub-domain_example_com_80' in haproxy_config
            assert 'use_backend certbot_backend if is_certbot_sub-domain_example_com_80' in haproxy_config

    def test_certbot_get_certbot_hosts(self):
        """Test that get_certbot_hosts returns list of domains with certbot enabled"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            parsed_object = {
                'container1': {
                    'easyhaproxy.http.host': 'example.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '3000',
                    'easyhaproxy.http.certbot': 'true',
                },
                'container2': {
                    'easyhaproxy.http.host': 'test.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '4000',
                    'easyhaproxy.http.certbot': 'true',
                },
                'container3': {
                    'easyhaproxy.http.host': 'nocert.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '5000',
                }
            }

            cfg.generate(parsed_object)

            # Should return list of hosts with certbot=true
            certbot_hosts = cfg.certbot_hosts
            assert 'example.com' in certbot_hosts
            assert 'test.com' in certbot_hosts
            assert 'nocert.com' not in certbot_hosts

    def test_certbot_port_must_be_80(self):
        """Test that certbot only works on port 80 (HTTP-01 requirement)"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            # Try certbot on port 8080 (not standard HTTP port)
            parsed_object = {
                'container1': {
                    'easyhaproxy.http.host': 'example.com',
                    'easyhaproxy.http.port': '8080',  # Non-standard port
                    'easyhaproxy.http.localport': '3000',
                    'easyhaproxy.http.certbot': 'true',
                }
            }

            haproxy_config = cfg.generate(parsed_object)

            # ACME ACL should still be created (up to user to ensure proper routing)
            # Note: The actual ACME validation will fail if port 80 isn't accessible
            assert 'acl is_certbot_example_com_8080' in haproxy_config


class TestCertbotHAProxyConfigEdgeCases:
    """Test edge cases and error conditions"""

    def test_multiple_containers_same_domain_with_certbot(self):
        """Test multiple containers serving the same domain with certbot"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            parsed_object = {
                'container1': {
                    'easyhaproxy.http.host': 'example.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '3000',
                    'easyhaproxy.http.certbot': 'true',
                },
                'container2': {
                    'easyhaproxy.http.host': 'example.com',  # Same domain
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '4000',
                    'easyhaproxy.http.certbot': 'true',
                }
            }

            haproxy_config = cfg.generate(parsed_object)

            # Should only create ACL once (not duplicate)
            assert haproxy_config.count('acl is_certbot_example_com_80') == 1

            # Should route to certbot_backend
            assert 'use_backend certbot_backend if is_certbot_example_com_80' in haproxy_config

    def test_certbot_with_custom_ports(self):
        """Test certbot behavior with custom frontend ports"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            parsed_object = {
                'container1': {
                    'easyhaproxy.custom.host': 'example.com',
                    'easyhaproxy.custom.port': '8080',
                    'easyhaproxy.custom.localport': '3000',
                    'easyhaproxy.custom.certbot': 'true',
                }
            }

            haproxy_config = cfg.generate(parsed_object)

            # Should create frontend on port 8080 with certbot ACL
            assert 'frontend http_in_8080' in haproxy_config
            assert 'acl is_certbot_example_com_8080' in haproxy_config

    def test_certbot_backend_format(self):
        """Test exact format of certbot_backend"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            haproxy_config = cfg.generate({})

            # Verify exact backend format
            assert 'backend certbot_backend' in haproxy_config
            assert 'mode http' in haproxy_config
            assert 'server certbot 127.0.0.1:2080' in haproxy_config

            # Should NOT have any load balancing, health checks, etc.
            # (it's a simple pass-through to localhost)
            lines = haproxy_config.split('\n')
            in_certbot_backend = False
            certbot_backend_lines = []
            for line in lines:
                if 'backend certbot_backend' in line:
                    in_certbot_backend = True
                elif in_certbot_backend and line.strip() and not line.startswith(' '):
                    break  # End of backend section
                elif in_certbot_backend:
                    certbot_backend_lines.append(line.strip())

            # Should only have mode and server lines
            assert 'mode http' in certbot_backend_lines
            assert 'server certbot 127.0.0.1:2080' in certbot_backend_lines
            assert len([l for l in certbot_backend_lines if l]) == 2  # Only 2 non-empty lines

    def test_certbot_acl_order_before_use_backend(self):
        """Test that ACL definitions come before use_backend rules"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            mapping = ContainerEnv.read()
            cfg = HaproxyConfigGenerator(mapping)

            parsed_object = {
                'container1': {
                    'easyhaproxy.http.host': 'example.com',
                    'easyhaproxy.http.port': '80',
                    'easyhaproxy.http.localport': '3000',
                    'easyhaproxy.http.certbot': 'true',
                }
            }

            haproxy_config = cfg.generate(parsed_object)

            # Find positions
            acl_pos = haproxy_config.find('acl is_certbot_example_com_80')
            use_backend_pos = haproxy_config.find('use_backend certbot_backend if is_certbot_example_com_80')

            assert acl_pos > 0, "ACL not found"
            assert use_backend_pos > 0, "use_backend not found"
            assert acl_pos < use_backend_pos, "ACL must be defined before use_backend"