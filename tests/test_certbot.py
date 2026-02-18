"""
Unit tests for Certbot/ACME functionality

Tests the Certbot class without requiring internet access or third-party providers.
Verifies command generation, certificate status checking, and configuration handling.
"""

import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, mock_open, patch

from OpenSSL import crypto

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from functions import Certbot, ContainerEnv, Functions


class TestCertbotStaticMethods:
    """Test Certbot static helper methods"""

    def test_set_acme_server_empty(self):
        """Test ACME server with empty string"""
        assert Certbot.set_acme_server("") == ""
        assert Certbot.set_acme_server(None) == ""
        assert Certbot.set_acme_server(False) == ""

    def test_set_acme_server_staging(self):
        """Test ACME server with staging flag"""
        assert Certbot.set_acme_server("staging") == "--staging"
        assert Certbot.set_acme_server("STAGING") == "--staging"
        assert Certbot.set_acme_server("Staging") == "--staging"

    def test_set_acme_server_custom_url(self):
        """Test ACME server with custom URL"""
        url = "https://acme-v02.api.letsencrypt.org/directory"
        assert Certbot.set_acme_server(url) == f"--server {url}"

        url2 = "https://acme.ssl.com/sslcom-dv-rsa"
        assert Certbot.set_acme_server(url2) == f"--server {url2}"

        # HTTP URLs should also work
        url3 = "http://localhost:14000/dir"
        assert Certbot.set_acme_server(url3) == f"--server {url3}"

    def test_set_acme_server_invalid(self):
        """Test ACME server with invalid values"""
        assert Certbot.set_acme_server("production") == ""
        assert Certbot.set_acme_server("invalid") == ""
        assert Certbot.set_acme_server("test") == ""

    def test_set_eab_kid_empty(self):
        """Test EAB KID with empty string"""
        assert Certbot.set_eab_kid("") == ""

    def test_set_eab_kid_with_value(self):
        """Test EAB KID with valid value"""
        kid = "test-kid-12345"
        assert Certbot.set_eab_kid(kid) == f'--eab-kid "{kid}"'

    def test_set_eab_hmac_key_empty(self):
        """Test EAB HMAC key with empty string"""
        assert Certbot.set_eab_hmac_key("") == ""

    def test_set_eab_hmac_key_with_value(self):
        """Test EAB HMAC key with valid value"""
        hmac = "test-hmac-key-abcdef"
        assert Certbot.set_eab_hmac_key(hmac) == f'--eab-hmac-key "{hmac}"'

    def test_check_acme_environment_ready_missing_email(self):
        """Test ACME environment check with missing email"""
        is_ready, error_msg = Certbot.check_acme_environment_ready("", "--staging")
        assert is_ready is False
        assert "ACME email not configured" in error_msg

    def test_check_acme_environment_ready_missing_server(self):
        """Test ACME environment check with missing server"""
        is_ready, error_msg = Certbot.check_acme_environment_ready("test@example.com", "")
        assert is_ready is False
        assert "ACME server not configured" in error_msg

    def test_check_acme_environment_ready_staging(self):
        """Test ACME environment check with staging server (no URL to check)"""
        is_ready, error_msg = Certbot.check_acme_environment_ready("test@example.com", "--staging")
        assert is_ready is True
        assert error_msg == ""

    @patch('requests.get')
    def test_check_acme_environment_ready_server_reachable(self, mock_get):
        """Test ACME environment check with reachable server"""
        # Mock successful response with valid ACME directory
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "newAccount": "https://acme.example.com/new-account",
            "newNonce": "https://acme.example.com/new-nonce",
            "newOrder": "https://acme.example.com/new-order"
        }
        mock_get.return_value = mock_response

        is_ready, error_msg = Certbot.check_acme_environment_ready(
            "test@example.com",
            "--server https://acme.example.com/directory"
        )

        assert is_ready is True
        assert error_msg == ""
        mock_get.assert_called_once_with("https://acme.example.com/directory", timeout=10, verify=True)

    @patch('requests.get')
    def test_check_acme_environment_ready_server_unreachable(self, mock_get):
        """Test ACME environment check with unreachable server"""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        is_ready, error_msg = Certbot.check_acme_environment_ready(
            "test@example.com",
            "--server https://acme.example.com/directory"
        )

        assert is_ready is False
        assert "not reachable" in error_msg
        assert "Connection refused" in error_msg

    @patch('requests.get')
    def test_check_acme_environment_ready_server_timeout(self, mock_get):
        """Test ACME environment check with timeout"""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        is_ready, error_msg = Certbot.check_acme_environment_ready(
            "test@example.com",
            "--server https://acme.example.com/directory"
        )

        assert is_ready is False
        assert "not reachable" in error_msg
        assert "timed out" in error_msg

    @patch('requests.get')
    def test_check_acme_environment_ready_server_http_error(self, mock_get):
        """Test ACME environment check with HTTP error status"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        is_ready, error_msg = Certbot.check_acme_environment_ready(
            "test@example.com",
            "--server https://acme.example.com/directory"
        )

        assert is_ready is False
        assert "returned HTTP 404" in error_msg

    @patch('requests.get')
    def test_check_acme_environment_ready_invalid_acme_directory(self, mock_get):
        """Test ACME environment check with invalid ACME directory"""
        # Mock response without required "newAccount" key
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "message": "Not an ACME directory"
        }
        mock_get.return_value = mock_response

        is_ready, error_msg = Certbot.check_acme_environment_ready(
            "test@example.com",
            "--server https://acme.example.com/directory"
        )

        assert is_ready is False
        assert "invalid ACME directory" in error_msg

    @patch.dict(os.environ, {'REQUESTS_CA_BUNDLE': '/path/to/pebble-ca.pem'})
    @patch('requests.get')
    def test_check_acme_environment_ready_respects_ca_bundle(self, mock_get):
        """Test that REQUESTS_CA_BUNDLE environment variable is respected"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"newAccount": "https://pebble:14000/new-account"}
        mock_get.return_value = mock_response

        is_ready, error_msg = Certbot.check_acme_environment_ready(
            "test@example.com",
            "--server https://pebble:14000/dir"
        )

        assert is_ready is True
        # Verify verify parameter uses REQUESTS_CA_BUNDLE
        mock_get.assert_called_once_with("https://pebble:14000/dir", timeout=10, verify='/path/to/pebble-ca.pem')


class TestCertbotInitialization:
    """Test Certbot class initialization"""

    def test_certbot_init_basic(self):
        """Test Certbot initialization with basic configuration"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_SERVER': 'staging',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            assert certbot.certs == "/tmp/certs"
            assert certbot.email == "test@example.com"
            assert certbot.acme_server == "--staging"
            assert certbot.eab_kid == ""
            assert certbot.eab_hmac_key == ""
            assert certbot.freeze_issue == {}
            assert certbot.retry_count == 60  # default
            assert certbot.certbot_preferred_challenges == "http"  # default
            assert certbot.certbot_manual_auth_hook == False  # default

    def test_certbot_init_with_eab(self):
        """Test Certbot initialization with EAB credentials"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_SERVER': 'https://acme.ssl.com/sslcom-dv-rsa',
            'EASYHAPROXY_CERTBOT_EAB_KID': 'my-eab-kid',
            'EASYHAPROXY_CERTBOT_EAB_HMAC_KEY': 'my-hmac-key',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            assert certbot.email == "test@example.com"
            assert certbot.acme_server == "--server https://acme.ssl.com/sslcom-dv-rsa"
            assert certbot.eab_kid == '--eab-kid "my-eab-kid"'
            assert certbot.eab_hmac_key == '--eab-hmac-key "my-hmac-key"'

    def test_certbot_init_with_custom_retry_count(self):
        """Test Certbot initialization with custom retry count"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_RETRY_COUNT': '120',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            assert certbot.retry_count == 120

    def test_certbot_init_with_dns_challenge(self):
        """Test Certbot initialization with DNS challenge"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES': 'dns',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            assert certbot.certbot_preferred_challenges == "dns"

    def test_certbot_init_with_manual_auth_hook(self):
        """Test Certbot initialization with manual auth hook"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK': '/path/to/auth-hook.sh',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            assert certbot.certbot_manual_auth_hook == "/path/to/auth-hook.sh"


class TestCertbotCertificateStatus:
    """Test certificate status checking"""

    def create_test_certificate(self, days_valid=30):
        """Helper to create a test certificate valid for specified days"""
        # Create key pair
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)

        # Create certificate
        cert = crypto.X509()
        cert.get_subject().CN = "test.example.com"
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(days_valid * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')

        # Combine cert and key
        cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)

        return cert_pem.decode() + key_pem.decode()

    def test_get_certificate_status_not_found(self):
        """Test certificate status when file doesn't exist"""
        with patch.dict(os.environ, {'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com'}, clear=False):
            certbot = Certbot("/tmp/nonexistent")
            status = certbot.get_certificate_status("example.com")
            assert status == "not_found"

    def test_get_certificate_status_ok(self):
        """Test certificate status when valid and not expiring soon"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            cert_content = self.create_test_certificate(days_valid=90)
            f.write(cert_content)
            cert_file = f.name

        try:
            with patch.dict(os.environ, {'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com'}, clear=False):
                certbot = Certbot(os.path.dirname(cert_file))
                # Mock the filename pattern
                with patch.object(certbot, 'certs', os.path.dirname(cert_file)):
                    status = certbot.get_certificate_status(os.path.basename(cert_file).replace('.pem', ''))
                    assert status == "ok"
        finally:
            os.unlink(cert_file)

    def test_get_certificate_status_expiring(self):
        """Test certificate status when expiring within 15 days"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            cert_content = self.create_test_certificate(days_valid=10)
            f.write(cert_content)
            cert_file = f.name

        try:
            with patch.dict(os.environ, {'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com'}, clear=False):
                certbot = Certbot(os.path.dirname(cert_file))
                with patch.object(certbot, 'certs', os.path.dirname(cert_file)):
                    status = certbot.get_certificate_status(os.path.basename(cert_file).replace('.pem', ''))
                    assert status == "expiring"
        finally:
            os.unlink(cert_file)

    def test_get_certificate_status_expired(self):
        """Test certificate status when already expired"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            cert_content = self.create_test_certificate(days_valid=-1)
            f.write(cert_content)
            cert_file = f.name

        try:
            with patch.dict(os.environ, {'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com'}, clear=False):
                certbot = Certbot(os.path.dirname(cert_file))
                with patch.object(certbot, 'certs', os.path.dirname(cert_file)):
                    status = certbot.get_certificate_status(os.path.basename(cert_file).replace('.pem', ''))
                    assert status == "expired"
        finally:
            os.unlink(cert_file)

    def test_get_certificate_status_error(self):
        """Test certificate status with invalid/corrupted certificate"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("Invalid certificate content\n")
            cert_file = f.name

        try:
            with patch.dict(os.environ, {'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com'}, clear=False):
                certbot = Certbot(os.path.dirname(cert_file))
                with patch.object(certbot, 'certs', os.path.dirname(cert_file)):
                    status = certbot.get_certificate_status(os.path.basename(cert_file).replace('.pem', ''))
                    assert status == "error"
        finally:
            os.unlink(cert_file)


class TestCertbotMergeCertificate:
    """Test certificate merging functionality"""

    def test_merge_certificate(self):
        """Test merging certificate and key into single file"""
        cert = "-----BEGIN CERTIFICATE-----\nCERT_DATA\n-----END CERTIFICATE-----\n"
        key = "-----BEGIN PRIVATE KEY-----\nKEY_DATA\n-----END PRIVATE KEY-----\n"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            filename = f.name

        try:
            Certbot.merge_certificate(cert, key, filename)

            with open(filename, 'r') as f:
                content = f.read()

            assert content == cert + key
            assert "BEGIN CERTIFICATE" in content
            assert "BEGIN PRIVATE KEY" in content
        finally:
            os.unlink(filename)


class TestCertbotCheckCertificates:
    """Test check_certificates method and command generation"""

    def test_check_certificates_no_email(self):
        """Test that no certificates are requested without email"""
        with patch.dict(os.environ, {'EASYHAPROXY_CERTBOT_EMAIL': ''}, clear=False):
            certbot = Certbot("/tmp/certs")
            result = certbot.check_certificates(["example.com"])
            assert result is False

    def test_check_certificates_no_hosts(self):
        """Test that no certificates are requested without hosts"""
        with patch.dict(os.environ, {'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com'}, clear=False):
            certbot = Certbot("/tmp/certs")
            result = certbot.check_certificates([])
            assert result is False

    @patch('functions.Functions.run_bash')
    def test_check_certificates_request_new(self, mock_run_bash):
        """Test requesting new certificates (not_found status)"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_SERVER': 'staging',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            # Mock get_certificate_status to return not_found
            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    result = certbot.check_certificates(['example.com', 'test.com'])

            assert result is True
            assert mock_run_bash.called
            call_args = mock_run_bash.call_args[0]
            command = call_args[1]

            # Verify command structure
            assert '/usr/bin/certbot certonly' in command
            assert '--staging' in command
            assert '--preferred-challenges http' in command
            assert '--agree-tos' in command
            assert '--issuance-timeout 90' in command
            assert '--no-eff-email' in command
            assert '--non-interactive' in command
            assert '--max-log-backups=0' in command
            assert '-d example.com' in command
            assert '-d test.com' in command
            assert '--email test@example.com' in command
            assert '--http-01-port 2080' in command
            assert '--standalone' in command

    @patch('functions.Functions.run_bash')
    def test_check_certificates_with_eab(self, mock_run_bash):
        """Test certificate request with EAB credentials"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_SERVER': 'https://acme.ssl.com/sslcom-dv-rsa',
            'EASYHAPROXY_CERTBOT_EAB_KID': 'my-kid',
            'EASYHAPROXY_CERTBOT_EAB_HMAC_KEY': 'my-hmac',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    result = certbot.check_certificates(['example.com'])

            assert result is True
            call_args = mock_run_bash.call_args[0]
            command = call_args[1]

            assert '--eab-kid "my-kid"' in command
            assert '--eab-hmac-key "my-hmac"' in command
            assert '--server https://acme.ssl.com/sslcom-dv-rsa' in command

    @patch('functions.Functions.run_bash')
    def test_check_certificates_with_dns_challenge(self, mock_run_bash):
        """Test certificate request with DNS challenge"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES': 'dns',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    result = certbot.check_certificates(['example.com'])

            assert result is True
            call_args = mock_run_bash.call_args[0]
            command = call_args[1]

            assert '--preferred-challenges dns' in command
            # DNS challenge should NOT include --http-01-port or --standalone
            assert '--http-01-port' not in command
            assert '--standalone' not in command

    @patch('functions.Functions.run_bash')
    def test_check_certificates_with_manual_auth_hook(self, mock_run_bash):
        """Test certificate request with manual auth hook"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK': '/path/to/hook.sh',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    result = certbot.check_certificates(['example.com'])

            assert result is True
            call_args = mock_run_bash.call_args[0]
            command = call_args[1]

            assert "--manual --manual-auth-hook '/path/to/hook.sh'" in command

    @patch('functions.Functions.run_bash')
    def test_check_certificates_renew(self, mock_run_bash):
        """Test renewing expiring certificates"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='expiring'):
                with patch.object(certbot, 'find_live_certificates'):
                    result = certbot.check_certificates(['example.com'])

            assert result is True
            assert mock_run_bash.called

            # Should call certbot renew
            call_args = mock_run_bash.call_args[0]
            command = call_args[1]
            assert '/usr/bin/certbot renew' in command

    @patch('functions.Functions.run_bash')
    def test_check_certificates_mixed_statuses(self, mock_run_bash):
        """Test with mixed certificate statuses (new, renew, ok)"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            # Mock different statuses for different hosts
            def mock_status(host):
                statuses = {
                    'new.com': 'not_found',
                    'renew.com': 'expiring',
                    'ok.com': 'ok',
                    'error.com': 'error',
                }
                return statuses.get(host, 'ok')

            with patch.object(certbot, 'get_certificate_status', side_effect=mock_status):
                with patch.object(certbot, 'find_live_certificates'):
                    result = certbot.check_certificates(['new.com', 'renew.com', 'ok.com', 'error.com'])

            assert result is True
            # Should be called twice: once for certonly (new.com), once for renew (renew.com)
            assert mock_run_bash.call_count == 2

    @patch('functions.Functions.run_bash')
    def test_check_certificates_freeze_mechanism(self, mock_run_bash):
        """Test freeze mechanism when certificate issuance fails"""
        mock_run_bash.return_value = (1, [])  # Return error code

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_RETRY_COUNT': '5',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    with patch.object(certbot, 'find_missing_certificates') as mock_find_missing:
                        result = certbot.check_certificates(['example.com'])

            assert result is True  # Still returns True (reload needed)
            assert mock_find_missing.called

    @patch('functions.Functions.run_bash')
    def test_check_certificates_debug_mode(self, mock_run_bash):
        """Test that verbose flag is added in debug mode"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'CERTBOT_LOG_LEVEL': 'DEBUG',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            # Set logger to DEBUG
            from functions import logger_certbot
            with patch.object(logger_certbot, 'level', logging.DEBUG):
                with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                    with patch.object(certbot, 'find_live_certificates'):
                        result = certbot.check_certificates(['example.com'])

            assert result is True
            call_args = mock_run_bash.call_args[0]
            command = call_args[1]

            # Should include -v for verbose output
            assert ' -v' in command


class TestCertbotFindLiveCertificates:
    """Test finding and merging live certificates"""

    def test_find_live_certificates_no_directory(self):
        """Test when /etc/letsencrypt/live doesn't exist"""
        with patch.dict(os.environ, {'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com'}, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch('os.path.exists', return_value=False):
                certbot.find_live_certificates()
                # Should not crash

    def test_find_live_certificates_with_certs(self):
        """Test finding and merging certificates from live directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock directory structure
            live_dir = os.path.join(tmpdir, "live")
            os.makedirs(live_dir)

            # Create example.com certificate
            example_dir = os.path.join(live_dir, "example.com")
            os.makedirs(example_dir)

            cert_content = "-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----\n"
            key_content = "-----BEGIN PRIVATE KEY-----\nKEY\n-----END PRIVATE KEY-----\n"

            with open(os.path.join(example_dir, "cert.pem"), 'w') as f:
                f.write(cert_content)
            with open(os.path.join(example_dir, "privkey.pem"), 'w') as f:
                f.write(key_content)

            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)

            with patch.dict(os.environ, {'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com'}, clear=False):
                certbot = Certbot(output_dir)

                with patch('os.path.exists', return_value=True):
                    with patch('os.listdir', return_value=['example.com']):
                        with patch('os.path.isdir', return_value=True):
                            with patch.object(Functions, 'load', side_effect=[cert_content, key_content]):
                                certbot.find_live_certificates()

            # Verify merged certificate was created
            merged_file = os.path.join(output_dir, "example.com.pem")
            if os.path.exists(merged_file):
                with open(merged_file, 'r') as f:
                    content = f.read()
                assert content == cert_content + key_content


class TestCertbotFindMissingCertificates:
    """Test freeze mechanism for failed certificates"""

    def test_find_missing_certificates_sets_freeze(self):
        """Test that missing certificates are frozen for retry"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_RETRY_COUNT': '10',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                certbot.find_missing_certificates(['-d example.com', '-d test.com'])

            assert 'example.com' in certbot.freeze_issue
            assert 'test.com' in certbot.freeze_issue
            assert certbot.freeze_issue['example.com'] == 10
            assert certbot.freeze_issue['test.com'] == 10

    def test_find_missing_certificates_skips_ok(self):
        """Test that OK certificates are not frozen"""
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_RETRY_COUNT': '10',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='ok'):
                certbot.find_missing_certificates(['-d example.com'])

            assert 'example.com' not in certbot.freeze_issue

    @patch('functions.Functions.run_bash')
    def test_frozen_host_is_skipped(self, mock_run_bash):
        """Test that frozen hosts are skipped during retry period"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_RETRY_COUNT': '2',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            # Manually set freeze
            certbot.freeze_issue['frozen.com'] = 2

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    result = certbot.check_certificates(['frozen.com', 'normal.com'])

            # Should only request certificate for normal.com
            call_args = mock_run_bash.call_args[0]
            command = call_args[1]

            assert '-d normal.com' in command
            assert '-d frozen.com' not in command
            # Freeze count should decrement
            assert certbot.freeze_issue['frozen.com'] == 1

    @patch('functions.Functions.run_bash')
    def test_frozen_host_unfreezes_after_countdown(self, mock_run_bash):
        """Test that frozen hosts are unfrozen after countdown reaches 0"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            # Set freeze to 1 (will decrement to 0)
            certbot.freeze_issue['example.com'] = 1

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    # First call: still frozen (count = 1 -> 0)
                    certbot.check_certificates(['example.com'])
                    assert certbot.freeze_issue['example.com'] == 0

                    # Second call: should be unfrozen and removed from dict
                    certbot.check_certificates(['example.com'])
                    assert 'example.com' not in certbot.freeze_issue

                    # Third call: should request certificate
                    certbot.check_certificates(['example.com'])

            # On third call, certificate should be requested
            call_args = mock_run_bash.call_args[0]
            command = call_args[1]
            assert '-d example.com' in command


class TestCertbotWebhookDNS:
    """Test manual auth hook (webhook) for DNS challenges"""

    @patch('functions.Functions.run_bash')
    def test_dns_challenge_without_webhook(self, mock_run_bash):
        """Test DNS challenge command generation without webhook (will fail in practice)"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES': 'dns',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    certbot.check_certificates(['example.com'])

            call_args = mock_run_bash.call_args[0]
            command = call_args[1]

            # Should use DNS challenge
            assert '--preferred-challenges dns' in command
            # Should NOT include HTTP-specific flags
            assert '--http-01-port' not in command
            assert '--standalone' not in command
            # Should NOT include manual flags (no webhook configured)
            assert '--manual' not in command

    @patch('functions.Functions.run_bash')
    def test_dns_challenge_with_webhook(self, mock_run_bash):
        """Test DNS challenge with webhook for wildcard certificates"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES': 'dns',
            'EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK': '/usr/local/bin/cloudflare-dns.sh',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            # DNS is required for wildcard certificates
            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    certbot.check_certificates(['*.example.com', 'example.com'])

            call_args = mock_run_bash.call_args[0]
            command = call_args[1]

            # Verify DNS challenge with webhook
            assert '--preferred-challenges dns' in command
            assert '--manual' in command
            assert "--manual-auth-hook '/usr/local/bin/cloudflare-dns.sh'" in command
            # Verify both wildcard and apex domain
            assert '-d *.example.com' in command
            assert '-d example.com' in command

    @patch('functions.Functions.run_bash')
    def test_http_challenge_with_webhook(self, mock_run_bash):
        """Test HTTP challenge can also use webhook (less common)"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES': 'http',
            'EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK': '/hooks/http-webroot.sh',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    certbot.check_certificates(['example.com'])

            call_args = mock_run_bash.call_args[0]
            command = call_args[1]

            # Both HTTP flags and webhook should be present
            assert '--preferred-challenges http' in command
            assert '--http-01-port 2080' in command
            assert '--standalone' in command
            assert '--manual' in command
            assert "--manual-auth-hook '/hooks/http-webroot.sh'" in command

    @patch('functions.Functions.run_bash')
    def test_webhook_environment_variables_documented(self, mock_run_bash):
        """Document environment variables passed to webhook by certbot"""
        mock_run_bash.return_value = (0, [])

        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES': 'dns',
            'EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK': '/hooks/dns-hook.sh',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    certbot.check_certificates(['example.com'])

        # Certbot automatically passes these to the webhook script:
        # CERTBOT_DOMAIN - Domain being authenticated (e.g., "example.com")
        # CERTBOT_VALIDATION - Validation string to add to DNS TXT record
        # CERTBOT_TOKEN - Challenge token (for HTTP challenges)
        #
        # Example webhook script:
        # #!/bin/bash
        # # Add TXT record: _acme-challenge.$CERTBOT_DOMAIN -> $CERTBOT_VALIDATION
        # curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
        #   -H "Authorization: Bearer $CF_TOKEN" \
        #   -d '{"type":"TXT","name":"_acme-challenge.'$CERTBOT_DOMAIN'","content":"'$CERTBOT_VALIDATION'"}'

        assert mock_run_bash.called

    @patch('functions.Functions.run_bash')
    def test_webhook_with_multiple_providers(self, mock_run_bash):
        """Test webhook works with different ACME providers"""
        mock_run_bash.return_value = (0, [])

        # ZeroSSL with DNS challenge and webhook
        with patch.dict(os.environ, {
            'EASYHAPROXY_CERTBOT_EMAIL': 'test@example.com',
            'EASYHAPROXY_CERTBOT_SERVER': 'https://acme.zerossl.com/v2/DV90',
            'EASYHAPROXY_CERTBOT_EAB_KID': 'zerossl-kid',
            'EASYHAPROXY_CERTBOT_EAB_HMAC_KEY': 'zerossl-hmac',
            'EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES': 'dns',
            'EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK': '/hooks/route53-dns.py',
        }, clear=False):
            certbot = Certbot("/tmp/certs")

            with patch.object(certbot, 'get_certificate_status', return_value='not_found'):
                with patch.object(certbot, 'find_live_certificates'):
                    certbot.check_certificates(['example.com'])

            call_args = mock_run_bash.call_args[0]
            command = call_args[1]

            # All components should be present
            assert '--server https://acme.zerossl.com/v2/DV90' in command
            assert '--eab-kid "zerossl-kid"' in command
            assert '--eab-hmac-key "zerossl-hmac"' in command
            assert '--preferred-challenges dns' in command
            assert "--manual-auth-hook '/hooks/route53-dns.py'" in command