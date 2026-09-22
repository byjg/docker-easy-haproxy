import logging
import os
import shlex
import subprocess
import time
from datetime import datetime

import requests
from OpenSSL import crypto

from .consts import PluginConsts
from .env import get_config

logger = logging.getLogger("certbot_plugin")


class CertbotManager:
    def __init__(self):
        cfg = get_config()

        self.email = cfg["email"]
        self.acme_server = self._set_acme_server(cfg["server"] or cfg["autoconfig"])
        self.eab_kid = self._set_eab_kid(cfg["eab_kid"])
        self.eab_hmac_key = self._set_eab_hmac_key(cfg["eab_hmac_key"])
        self.retry_count = cfg["retry_count"]
        self.preferred_challenges = cfg["preferred_challenges"]
        self.manual_auth_hook = cfg["manual_auth_hook"]
        self.webhook_url = cfg["webhook_url"]
        self.freeze_issue = {}

    @staticmethod
    def _set_acme_server(acme_server):
        if not acme_server:
            return ""
        if acme_server.lower() == "staging":
            return "--staging"
        elif acme_server.lower().startswith("http"):
            return "--server " + acme_server
        else:
            return ""

    @staticmethod
    def _set_eab_kid(eab_kid):
        if eab_kid:
            return f'--eab-kid "{eab_kid}"'
        return ""

    @staticmethod
    def _set_eab_hmac_key(eab_hmac_key):
        if eab_hmac_key:
            return f'--eab-hmac-key "{eab_hmac_key}"'
        return ""

    def get_certificate_status(self, host):
        current_time = time.time()
        filename = os.path.join(PluginConsts.certs_dir(), f"{host}.pem")
        if not os.path.exists(filename):
            return "not_found"

        try:
            with open(filename, "rb") as f:
                certificate_str = f.read()
            certificate = crypto.load_certificate(crypto.FILETYPE_PEM, certificate_str)
            expiration_after = datetime.strptime(
                certificate.get_notAfter().decode()[:-1], "%Y%m%d%H%M%S"
            ).timestamp()
            if current_time >= expiration_after:
                return "expired"
            elif (expiration_after - current_time) // (24 * 3600) <= 15:
                return "expiring"
        except Exception as e:
            logger.error(f"Certificate {host} error: {e}")
            return "error"

        return "ok"

    @staticmethod
    def merge_certificate(cert, key, filename):
        with open(filename, "w") as f:
            f.write(cert + key)

    def find_live_certificates(self):
        live_dir = PluginConsts.live_dir()
        if not os.path.exists(live_dir):
            return
        for item in os.listdir(live_dir):
            path = os.path.join(live_dir, item)
            if os.path.isdir(path):
                try:
                    with open(os.path.join(path, "cert.pem")) as f:
                        cert = f.read()
                    with open(os.path.join(path, "privkey.pem")) as f:
                        key = f.read()
                    filename = os.path.join(PluginConsts.certs_dir(), f"{item}.pem")
                    self.merge_certificate(cert, key, filename)
                    logger.info(f"Merged certificate for {item}")
                except Exception as e:
                    logger.error(f"Failed to merge certificate for {item}: {e}")

    def find_missing_certificates(self, hosts):
        for host in hosts:
            if host.startswith("-d "):
                host = host[3:]
            cert_status = self.get_certificate_status(host)
            if cert_status != "ok":
                self.freeze_issue[host] = self.retry_count
                logger.debug(f"Freeze issuing ssl for {host} due failure. The certificate is {cert_status}")

    def _notify_webhook(self, event, domains):
        if not self.webhook_url:
            return
        try:
            requests.post(
                self.webhook_url,
                json={"event": event, "domains": domains},
                timeout=10,
            )
            logger.info(f"Webhook notified: {event} for {domains}")
        except Exception as e:
            logger.warning(f"Webhook notification failed: {e}")

    def _run_command(self, command):
        if isinstance(command, str):
            command = shlex.split(command)
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            stdout, stderr = process.communicate()
            if stdout:
                logger.info(stdout.strip())
            if stderr:
                logger.warning(stderr.strip())
            return process.returncode
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return -1

    def check_certificates(self, hosts):
        if not self.email or not hosts:
            return False

        try:
            request_certs = []
            renew_certs = []
            for host in hosts:
                cert_status = self.get_certificate_status(host)
                host_arg = f"-d {host}"
                if cert_status in ("ok", "error"):
                    continue
                elif host in self.freeze_issue:
                    freeze_count = self.freeze_issue.pop(host, 0)
                    if freeze_count > 0:
                        logger.debug(f"Waiting freezing period ({freeze_count}) for {host}")
                        self.freeze_issue[host] = freeze_count - 1
                elif cert_status in ("not_found", "expired"):
                    logger.debug(f"[{cert_status}] Requesting new certificate for {host}")
                    request_certs.append(host_arg)
                elif cert_status == "expiring":
                    logger.debug(f"[{cert_status}] Renewing certificate for {host}")
                    renew_certs.append(host_arg)

            certs_dir = PluginConsts.certs_dir()
            certbot_certonly = (
                f"/usr/bin/certbot certonly {self.acme_server}"
                f" --config-dir {certs_dir}"
                f" --work-dir {PluginConsts.work_dir()}"
                f" --logs-dir {PluginConsts.logs_dir()}"
                f" --preferred-challenges {self.preferred_challenges}"
                f" --agree-tos"
                f" --issuance-timeout 90"
                f" --no-eff-email"
                f" --non-interactive"
                f" --max-log-backups=0"
                f" {self.eab_kid} {self.eab_hmac_key}"
                f" {' '.join(request_certs)} --email {self.email}"
            )

            if "http" in self.preferred_challenges:
                certbot_certonly += " --http-01-port 2080 --standalone"

            if self.manual_auth_hook:
                certbot_certonly += f" --manual --manual-auth-hook '{self.manual_auth_hook}'"

            if logger.level == logging.DEBUG:
                certbot_certonly += " -v"

            ret_reload = False
            return_code_issue = 0
            return_code_renew = 0

            if request_certs:
                return_code_issue = self._run_command(certbot_certonly)
                ret_reload = True

            if renew_certs:
                certbot_renew = (
                    f"/usr/bin/certbot renew"
                    f" --config-dir {certs_dir}"
                    f" --work-dir {PluginConsts.work_dir()}"
                    f" --logs-dir {PluginConsts.logs_dir()}"
                )
                return_code_renew = self._run_command(certbot_renew)
                ret_reload = True

            if ret_reload:
                self.find_live_certificates()
                issued = [h[3:] for h in request_certs] + [h[3:] for h in renew_certs]
                self._notify_webhook("certs_updated", issued)

            if return_code_issue != 0:
                self.find_missing_certificates(request_certs)
            if return_code_renew != 0:
                self.find_missing_certificates(renew_certs)

            return ret_reload
        except Exception as e:
            logger.error(f"check_certificates error: {e}")
            return False
