import logging
import os
import sys
import threading
import time

from .api import create_api_server
from .certbot_manager import CertbotManager
from .env import get_config

logging.basicConfig(
    level=logging.INFO,
    format="certbot_plugin [%(asctime)s] %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("certbot_plugin")


def renewal_loop(manager, domain_registry, registry_lock, interval):
    """Run the certificate renewal loop at the configured interval."""
    logger.info(f"Renewal loop started (interval: {interval}s)")
    while True:
        time.sleep(interval)
        with registry_lock:
            domains = list(domain_registry)
        if domains:
            logger.info(f"Running renewal check for {len(domains)} domain(s)")
            try:
                manager.check_certificates(domains)
            except Exception as e:
                logger.error(f"Renewal loop error: {e}")
        else:
            logger.debug("No domains registered, skipping renewal check")


def main():
    cfg = get_config()

    if not cfg["email"]:
        logger.error("CERTBOT_EMAIL is required but not set")
        sys.exit(1)

    os.makedirs(cfg["certs_dir"], exist_ok=True)

    manager = CertbotManager()
    domain_registry = set(cfg["domains"])
    registry_lock = threading.Lock()

    if domain_registry:
        logger.info(f"Pre-loaded domains from CERTBOT_DOMAINS: {domain_registry}")

    # Start the HTTP API server in a daemon thread
    api_server = create_api_server(manager, domain_registry, registry_lock, cfg["api_port"])
    api_thread = threading.Thread(target=api_server.serve_forever, daemon=True)
    api_thread.start()
    logger.info(f"API server listening on 0.0.0.0:{cfg['api_port']}")

    # Run the renewal loop in the main thread
    renewal_loop(manager, domain_registry, registry_lock, cfg["renewal_interval"])


if __name__ == "__main__":
    main()
