import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

logger = logging.getLogger("certbot_plugin")


class CertbotAPIHandler(BaseHTTPRequestHandler):
    """HTTP API handler for certbot plugin."""

    manager = None
    domain_registry = None
    registry_lock = None

    def log_message(self, format, *args):
        logger.debug(f"API {self.address_string()} - {format % args}")

    def _send_json(self, status_code, data):
        body = json.dumps(data).encode()
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def _get_domain_from_path(self):
        """Extract domain from path like /certificates/example.com"""
        parts = self.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "certificates":
            return "/".join(parts[1:])
        return None

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")

        if path == "/health":
            self._send_json(200, {"status": "ok"})

        elif path == "/certificates":
            with self.__class__.registry_lock:
                domains = list(self.__class__.domain_registry)
            result = {}
            for domain in domains:
                result[domain] = self.__class__.manager.get_certificate_status(domain)
            self._send_json(200, {"domains": result})

        elif path.startswith("/certificates/"):
            domain = path[len("/certificates/"):]
            with self.__class__.registry_lock:
                known = domain in self.__class__.domain_registry
            if not known:
                self._send_json(404, {"error": "domain not found"})
            else:
                status = self.__class__.manager.get_certificate_status(domain)
                self._send_json(200, {"domain": domain, "status": status})

        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")

        if path == "/certificates":
            try:
                body = self._read_json_body()
                domains = body.get("domains", [])
                if not isinstance(domains, list) or not domains:
                    self._send_json(400, {"error": "domains must be a non-empty list"})
                    return
                with self.__class__.registry_lock:
                    for domain in domains:
                        self.__class__.domain_registry.add(domain)
                logger.info(f"Registered domains: {domains}")
                self._send_json(200, {"registered": domains})
            except Exception as e:
                self._send_json(400, {"error": str(e)})

        elif path == "/certificates/renew":
            with self.__class__.registry_lock:
                domains = list(self.__class__.domain_registry)
            if not domains:
                self._send_json(200, {"message": "no domains registered"})
                return
            threading.Thread(
                target=self.__class__.manager.check_certificates,
                args=(domains,),
                daemon=True,
            ).start()
            self._send_json(202, {"message": "renewal triggered", "domains": domains})

        else:
            self._send_json(404, {"error": "not found"})

    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")

        if path.startswith("/certificates/"):
            domain = path[len("/certificates/"):]
            with self.__class__.registry_lock:
                if domain in self.__class__.domain_registry:
                    self.__class__.domain_registry.discard(domain)
                    self._send_json(200, {"removed": domain})
                else:
                    self._send_json(404, {"error": "domain not found"})
        else:
            self._send_json(404, {"error": "not found"})


def create_api_server(manager, domain_registry, registry_lock, port):
    """Create and return an HTTPServer for the certbot plugin API."""
    CertbotAPIHandler.manager = manager
    CertbotAPIHandler.domain_registry = domain_registry
    CertbotAPIHandler.registry_lock = registry_lock

    server = HTTPServer(("0.0.0.0", port), CertbotAPIHandler)
    return server
