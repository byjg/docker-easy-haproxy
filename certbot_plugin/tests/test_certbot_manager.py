"""
Unit tests for certbot_plugin CertbotManager

Adapted from the main project's tests/test_certbot.py — verifies the plugin's
certificate management logic without requiring network access or certbot installed.
"""

import os
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from OpenSSL import crypto

# Allow imports from plugin src/
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.certbot_manager import CertbotManager
from src.consts import PluginConsts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_test_certificate(days_valid=30):
    """Create a self-signed PEM cert + key valid for *days_valid* days."""
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    cert = crypto.X509()
    cert.get_subject().CN = "test.example.com"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(days_valid * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, "sha256")

    cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode()
    key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, key).decode()
    return cert_pem + key_pem


# ---------------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------------

class TestSetAcmeServer:
    def test_empty(self):
        assert CertbotManager._set_acme_server("") == ""
        assert CertbotManager._set_acme_server(None) == ""
        assert CertbotManager._set_acme_server(False) == ""

    def test_staging(self):
        assert CertbotManager._set_acme_server("staging") == "--staging"
        assert CertbotManager._set_acme_server("STAGING") == "--staging"

    def test_custom_url(self):
        url = "https://acme-v02.api.letsencrypt.org/directory"
        assert CertbotManager._set_acme_server(url) == f"--server {url}"

    def test_http_url(self):
        url = "http://localhost:14000/dir"
        assert CertbotManager._set_acme_server(url) == f"--server {url}"

    def test_invalid(self):
        assert CertbotManager._set_acme_server("production") == ""
        assert CertbotManager._set_acme_server("invalid") == ""


class TestSetEab:
    def test_eab_kid_empty(self):
        assert CertbotManager._set_eab_kid("") == ""

    def test_eab_kid_with_value(self):
        assert CertbotManager._set_eab_kid("my-kid") == '--eab-kid "my-kid"'

    def test_eab_hmac_empty(self):
        assert CertbotManager._set_eab_hmac_key("") == ""

    def test_eab_hmac_with_value(self):
        assert CertbotManager._set_eab_hmac_key("my-hmac") == '--eab-hmac-key "my-hmac"'


# ---------------------------------------------------------------------------
# Certificate status
# ---------------------------------------------------------------------------

class TestGetCertificateStatus:
    @patch.dict(os.environ, {"CERTBOT_EMAIL": "test@example.com", "CERTBOT_CERTS_DIR": "/nonexistent"})
    def test_not_found(self):
        manager = CertbotManager()
        assert manager.get_certificate_status("example.com") == "not_found"

    def test_ok(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pem = create_test_certificate(days_valid=90)
            pem_path = os.path.join(tmpdir, "example.com.pem")
            with open(pem_path, "w") as f:
                f.write(pem)

            with patch.dict(os.environ, {"CERTBOT_EMAIL": "test@example.com", "CERTBOT_CERTS_DIR": tmpdir}):
                manager = CertbotManager()
                assert manager.get_certificate_status("example.com") == "ok"

    def test_expiring(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pem = create_test_certificate(days_valid=10)
            pem_path = os.path.join(tmpdir, "example.com.pem")
            with open(pem_path, "w") as f:
                f.write(pem)

            with patch.dict(os.environ, {"CERTBOT_EMAIL": "test@example.com", "CERTBOT_CERTS_DIR": tmpdir}):
                manager = CertbotManager()
                assert manager.get_certificate_status("example.com") == "expiring"

    def test_expired(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pem = create_test_certificate(days_valid=-1)
            pem_path = os.path.join(tmpdir, "example.com.pem")
            with open(pem_path, "w") as f:
                f.write(pem)

            with patch.dict(os.environ, {"CERTBOT_EMAIL": "test@example.com", "CERTBOT_CERTS_DIR": tmpdir}):
                manager = CertbotManager()
                assert manager.get_certificate_status("example.com") == "expired"

    def test_corrupted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pem_path = os.path.join(tmpdir, "example.com.pem")
            with open(pem_path, "w") as f:
                f.write("not a certificate")

            with patch.dict(os.environ, {"CERTBOT_EMAIL": "test@example.com", "CERTBOT_CERTS_DIR": tmpdir}):
                manager = CertbotManager()
                assert manager.get_certificate_status("example.com") == "error"


# ---------------------------------------------------------------------------
# Merge certificate
# ---------------------------------------------------------------------------

class TestMergeCertificate:
    def test_merge(self):
        cert = "-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----\n"
        key = "-----BEGIN PRIVATE KEY-----\nKEY\n-----END PRIVATE KEY-----\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            fname = f.name

        try:
            CertbotManager.merge_certificate(cert, key, fname)
            with open(fname) as f:
                content = f.read()
            assert content == cert + key
        finally:
            os.unlink(fname)


# ---------------------------------------------------------------------------
# check_certificates
# ---------------------------------------------------------------------------

class TestCheckCertificates:
    @patch.dict(os.environ, {"CERTBOT_EMAIL": "", "CERTBOT_CERTS_DIR": "/tmp"})
    def test_no_email_returns_false(self):
        manager = CertbotManager()
        assert manager.check_certificates(["example.com"]) is False

    @patch.dict(os.environ, {"CERTBOT_EMAIL": "test@example.com", "CERTBOT_CERTS_DIR": "/tmp"})
    def test_no_hosts_returns_false(self):
        manager = CertbotManager()
        assert manager.check_certificates([]) is False

    @patch.dict(os.environ, {
        "CERTBOT_EMAIL": "test@example.com",
        "CERTBOT_SERVER": "staging",
        "CERTBOT_CERTS_DIR": "/tmp",
    })
    def test_request_new_cert(self):
        manager = CertbotManager()

        with patch.object(manager, "get_certificate_status", return_value="not_found"):
            with patch.object(manager, "_run_command", return_value=0) as mock_cmd:
                with patch.object(manager, "find_live_certificates"):
                    with patch.object(manager, "_notify_webhook"):
                        result = manager.check_certificates(["example.com"])

        assert result is True
        assert mock_cmd.called
        cmd = mock_cmd.call_args[0][0]
        assert "/usr/bin/certbot certonly" in cmd
        assert "--staging" in cmd
        assert "-d example.com" in cmd
        assert "--email test@example.com" in cmd
        assert "--http-01-port 2080" in cmd
        assert "--standalone" in cmd

    @patch.dict(os.environ, {
        "CERTBOT_EMAIL": "test@example.com",
        "CERTBOT_SERVER": "staging",
        "CERTBOT_PREFERRED_CHALLENGES": "dns",
        "CERTBOT_CERTS_DIR": "/tmp",
    })
    def test_dns_challenge(self):
        manager = CertbotManager()

        with patch.object(manager, "get_certificate_status", return_value="not_found"):
            with patch.object(manager, "_run_command", return_value=0) as mock_cmd:
                with patch.object(manager, "find_live_certificates"):
                    with patch.object(manager, "_notify_webhook"):
                        result = manager.check_certificates(["example.com"])

        assert result is True
        cmd = mock_cmd.call_args[0][0]
        assert "--preferred-challenges dns" in cmd
        assert "--http-01-port" not in cmd
        assert "--standalone" not in cmd

    @patch.dict(os.environ, {
        "CERTBOT_EMAIL": "test@example.com",
        "CERTBOT_CERTS_DIR": "/tmp",
    })
    def test_renew_expiring(self):
        manager = CertbotManager()

        with patch.object(manager, "get_certificate_status", return_value="expiring"):
            with patch.object(manager, "_run_command", return_value=0) as mock_cmd:
                with patch.object(manager, "find_live_certificates"):
                    with patch.object(manager, "_notify_webhook"):
                        result = manager.check_certificates(["example.com"])

        assert result is True
        cmd = mock_cmd.call_args[0][0]
        assert "/usr/bin/certbot renew" in cmd

    @patch.dict(os.environ, {
        "CERTBOT_EMAIL": "test@example.com",
        "CERTBOT_EAB_KID": "my-kid",
        "CERTBOT_EAB_HMAC_KEY": "my-hmac",
        "CERTBOT_SERVER": "https://acme.ssl.com/sslcom-dv-rsa",
        "CERTBOT_CERTS_DIR": "/tmp",
    })
    def test_eab_credentials(self):
        manager = CertbotManager()

        with patch.object(manager, "get_certificate_status", return_value="not_found"):
            with patch.object(manager, "_run_command", return_value=0) as mock_cmd:
                with patch.object(manager, "find_live_certificates"):
                    with patch.object(manager, "_notify_webhook"):
                        result = manager.check_certificates(["example.com"])

        cmd = mock_cmd.call_args[0][0]
        assert '--eab-kid "my-kid"' in cmd
        assert '--eab-hmac-key "my-hmac"' in cmd
        assert "--server https://acme.ssl.com/sslcom-dv-rsa" in cmd

    @patch.dict(os.environ, {
        "CERTBOT_EMAIL": "test@example.com",
        "CERTBOT_RETRY_COUNT": "5",
        "CERTBOT_CERTS_DIR": "/tmp",
    })
    def test_freeze_mechanism(self):
        manager = CertbotManager()

        with patch.object(manager, "get_certificate_status", return_value="not_found"):
            with patch.object(manager, "_run_command", return_value=1):
                with patch.object(manager, "find_live_certificates"):
                    with patch.object(manager, "_notify_webhook"):
                        with patch.object(manager, "find_missing_certificates") as mock_missing:
                            result = manager.check_certificates(["example.com"])

        assert result is True
        assert mock_missing.called


# ---------------------------------------------------------------------------
# find_live_certificates
# ---------------------------------------------------------------------------

class TestFindLiveCertificates:
    def test_no_live_dir(self):
        with patch.dict(os.environ, {"CERTBOT_EMAIL": "test@example.com", "CERTBOT_CERTS_DIR": "/nonexistent"}):
            manager = CertbotManager()
            manager.find_live_certificates()  # must not raise

    def test_merges_certs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            live_dir = os.path.join(tmpdir, "live", "example.com")
            os.makedirs(live_dir)

            cert = "-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----\n"
            key = "-----BEGIN PRIVATE KEY-----\nKEY\n-----END PRIVATE KEY-----\n"

            with open(os.path.join(live_dir, "cert.pem"), "w") as f:
                f.write(cert)
            with open(os.path.join(live_dir, "privkey.pem"), "w") as f:
                f.write(key)

            with patch.dict(os.environ, {"CERTBOT_EMAIL": "test@example.com", "CERTBOT_CERTS_DIR": tmpdir}):
                manager = CertbotManager()
                manager.find_live_certificates()

            merged = os.path.join(tmpdir, "example.com.pem")
            assert os.path.exists(merged)
            with open(merged) as f:
                content = f.read()
            assert content == cert + key


# ---------------------------------------------------------------------------
# find_missing_certificates / freeze
# ---------------------------------------------------------------------------

class TestFindMissingCertificates:
    @patch.dict(os.environ, {
        "CERTBOT_EMAIL": "test@example.com",
        "CERTBOT_RETRY_COUNT": "10",
        "CERTBOT_CERTS_DIR": "/tmp",
    })
    def test_sets_freeze(self):
        manager = CertbotManager()
        with patch.object(manager, "get_certificate_status", return_value="not_found"):
            manager.find_missing_certificates(["-d example.com", "-d test.com"])

        assert "example.com" in manager.freeze_issue
        assert "test.com" in manager.freeze_issue
        assert manager.freeze_issue["example.com"] == 10
        assert manager.freeze_issue["test.com"] == 10

    @patch.dict(os.environ, {
        "CERTBOT_EMAIL": "test@example.com",
        "CERTBOT_RETRY_COUNT": "10",
        "CERTBOT_CERTS_DIR": "/tmp",
    })
    def test_skips_ok(self):
        manager = CertbotManager()
        with patch.object(manager, "get_certificate_status", return_value="ok"):
            manager.find_missing_certificates(["-d example.com"])

        assert "example.com" not in manager.freeze_issue


# ---------------------------------------------------------------------------
# Webhook notification
# ---------------------------------------------------------------------------

class TestWebhook:
    @patch.dict(os.environ, {
        "CERTBOT_EMAIL": "test@example.com",
        "CERTBOT_WEBHOOK_URL": "http://easyhaproxy:9190/reload",
        "CERTBOT_CERTS_DIR": "/tmp",
    })
    def test_webhook_called_on_new_cert(self):
        manager = CertbotManager()

        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            with patch.object(manager, "get_certificate_status", return_value="not_found"):
                with patch.object(manager, "_run_command", return_value=0):
                    with patch.object(manager, "find_live_certificates"):
                        manager.check_certificates(["example.com"])

        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert "json" in call_kwargs
        assert call_kwargs["json"]["event"] == "certs_updated"
        assert "example.com" in call_kwargs["json"]["domains"]

    @patch.dict(os.environ, {
        "CERTBOT_EMAIL": "test@example.com",
        "CERTBOT_CERTS_DIR": "/tmp",
    })
    def test_no_webhook_if_not_configured(self):
        manager = CertbotManager()
        assert manager.webhook_url == ""

        with patch("requests.post") as mock_post:
            with patch.object(manager, "get_certificate_status", return_value="not_found"):
                with patch.object(manager, "_run_command", return_value=0):
                    with patch.object(manager, "find_live_certificates"):
                        manager.check_certificates(["example.com"])

        assert not mock_post.called
