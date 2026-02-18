import logging
import os
import time
from datetime import datetime

import requests
from OpenSSL import crypto

from .consts import Consts
from .container_env import ContainerEnv
from .functions import Functions
from .loggers import logger_certbot


class Certbot:
    def __init__(self, certs):
        env = ContainerEnv.read()

        self.certs = certs
        self.email = env["certbot"]["email"]
        self.acme_server = self.set_acme_server(env["certbot"]["server"])
        self.eab_kid = self.set_eab_kid(env["certbot"]["eab_kid"])
        self.eab_hmac_key = self.set_eab_hmac_key(env["certbot"]["eab_hmac_key"])
        self.freeze_issue = {}
        self.retry_count = env["certbot"]["retry_count"]
        self.certbot_preferred_challenges = env["certbot"]["preferred_challenges"]
        self.certbot_manual_auth_hook = env["certbot"]["manual_auth_hook"]

    @staticmethod
    def set_acme_server(acme_server):
        if not acme_server:
            return ""
        if acme_server.lower() == "staging":
            return "--staging"
        elif acme_server.lower().startswith("http"):
            return "--server " + acme_server
        else:
            return ""

    @staticmethod
    def set_eab_kid(eab_kid):
        if eab_kid != "":
            return f'--eab-kid "{eab_kid}"'
        else:
            return ""

    @staticmethod
    def set_eab_hmac_key(eab_hmac_key):
        if eab_hmac_key != "":
            return f'--eab-hmac-key "{eab_hmac_key}"'
        else:
            return ""

    @staticmethod
    def check_acme_environment_ready(email, acme_server):
        """
        Check if ACME environment is ready for certificate operations.

        Args:
            email: EASYHAPROXY_CERTBOT_EMAIL value
            acme_server: Processed ACME server string from set_acme_server()

        Returns:
            tuple: (is_ready: bool, error_message: str)
        """
        # Check 1: Email configured
        if not email or email == "":
            return False, "ACME email not configured (EASYHAPROXY_CERTBOT_EMAIL)"

        # Check 2: ACME server configured
        if not acme_server or acme_server == "":
            return False, "ACME server not configured (EASYHAPROXY_CERTBOT_SERVER)"

        # Check 3: ACME server reachability (if URL provided)
        if "--server " in acme_server:
            server_url = acme_server.replace("--server ", "")
            try:
                # Use 10s timeout, respect REQUESTS_CA_BUNDLE for Pebble CA
                response = requests.get(server_url, timeout=10, verify=os.getenv("REQUESTS_CA_BUNDLE", True))
                if response.status_code != 200:
                    return False, f"ACME server {server_url} returned HTTP {response.status_code}"

                # Validate ACME directory structure (RFC 8555)
                data = response.json()
                if "newAccount" not in data:
                    return False, f"ACME server {server_url} returned invalid ACME directory"
            except requests.exceptions.RequestException as e:
                return False, f"ACME server {server_url} not reachable: {str(e)}"
            except Exception as e:
                return False, f"ACME server validation failed: {str(e)}"

        return True, ""

    def check_certificates(self, hosts):
        if self.email == "" or len(hosts) == 0:
            return False

        try:
            request_certs = []
            renew_certs = []
            for host in hosts:
                cert_status = self.get_certificate_status(host)
                host_arg = f'-d {host}'
                if cert_status == "ok" or cert_status == "error":
                    continue
                elif host in self.freeze_issue:
                    freeze_count = self.freeze_issue.pop(host, 0)
                    if freeze_count > 0:
                        logger_certbot.debug(f"Waiting freezing period ({freeze_count}) for {host} due previous errors")
                        self.freeze_issue[host] = freeze_count-1
                elif cert_status == "not_found" or cert_status == "expired":
                    logger_certbot.debug(f"[{cert_status}] Request new certificate for {host}")
                    request_certs.append(host_arg)
                elif cert_status == "expiring":
                    logger_certbot.debug(f"[{cert_status}] Renew certificate for {host}")
                    renew_certs.append(host_arg)

            certbot_certonly = ('/usr/bin/certbot certonly {acme_server}'
                                '    --config-dir {base_path}/certs'
                                '    --work-dir {base_path}/certs/work'
                                '    --logs-dir {base_path}/certs/logs'
                                '    --preferred-challenges {challenge}'
                                '    --agree-tos'
                                '    --issuance-timeout 90'
                                '    --no-eff-email'
                                '    --non-interactive'
                                '    --max-log-backups=0'
                                '    {eab_kid} {eab_hmac_key}'
                                '    {certs} --email {email}'.format(eab_kid=self.eab_kid,
                                                                     eab_hmac_key=self.eab_hmac_key,
                                                                     certs=' '.join(request_certs),
                                                                     email=self.email,
                                                                     challenge=self.certbot_preferred_challenges,
                                                                     acme_server=self.acme_server,
                                                                     base_path=Consts.base_path)
                                )

            if 'http' in self.certbot_preferred_challenges:
                certbot_certonly += ('    --http-01-port 2080'
                                     '    --standalone'
                                    )

            if self.certbot_manual_auth_hook:
                certbot_certonly += f'    --manual --manual-auth-hook \'{self.certbot_manual_auth_hook}\''

            if logger_certbot.level == logging.DEBUG:
                certbot_certonly += '    -v'

            logger_certbot.debug(f"certbot_certonly: {certbot_certonly}")

            ret_reload = False
            return_code_issue = 0
            return_code_renew = 0
            if len(request_certs) > 0:
                return_code_issue, output = Functions.run_bash(logger_certbot, certbot_certonly, return_result=False)
                ret_reload = True

            if len(renew_certs) > 0:
                certbot_renew = f"/usr/bin/certbot renew --config-dir {Consts.base_path}/certs --work-dir {Consts.base_path}/certs/work --logs-dir {Consts.base_path}/certs/logs"
                return_code_renew, output = Functions.run_bash(logger_certbot, certbot_renew, return_result=False)
                ret_reload = True

            if ret_reload:
                self.find_live_certificates()

            if return_code_issue != 0:
                self.find_missing_certificates(request_certs)
            if return_code_renew != 0:
                self.find_missing_certificates(renew_certs)

            return ret_reload
        except Exception as e:
            logger_certbot.error(f"{e}")
            return False

    @staticmethod
    def merge_certificate(cert, key, filename):
        Functions.save(filename, cert + key)

    def find_live_certificates(self):
        certbot_certs = f"{Consts.base_path}/certs/live/"
        if not os.path.exists(certbot_certs):
            return
        for item in os.listdir(certbot_certs):
            path = os.path.join(certbot_certs, item)
            if os.path.isdir(path):
                cert = Functions.load(os.path.join(path, "cert.pem"))
                key = Functions.load(os.path.join(path, "privkey.pem"))
                filename = f"{self.certs}/{item}.pem"
                self.merge_certificate(cert, key, filename)

    def get_certificate_status(self, host):
        current_time = time.time()
        filename = f"{self.certs}/{host}.pem"
        if not os.path.exists(filename):
            return "not_found"

        try:
            with open(filename, 'rb') as file:
                certificate_str = file.read()
            certificate = crypto.load_certificate(crypto.FILETYPE_PEM, certificate_str)
            expiration_after = datetime.strptime(certificate.get_notAfter().decode()[:-1], '%Y%m%d%H%M%S').timestamp()
            if current_time >= expiration_after:
                return "expired"
            elif (expiration_after - current_time) // (24 * 3600) <= 15:
                return "expiring"
        except Exception as e:
            logger_certbot.error(f"Certificate {host} error {e}")
            return "error"

        return "ok"

    def find_missing_certificates(self, hosts):
        for host in hosts:
            if host.startswith("-d "):
                host = host[3:]
            cert_status = self.get_certificate_status(host)
            if cert_status != "ok":
                self.freeze_issue[host] = self.retry_count
                logger_certbot.debug(f"Freeze issuing ssl for {host} due failure. The certificate is {cert_status}")