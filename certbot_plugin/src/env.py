import os


def get_config():
    """Read all plugin configuration from environment variables."""
    return {
        "email": os.getenv("CERTBOT_EMAIL", ""),
        "server": os.getenv("CERTBOT_SERVER", ""),
        "autoconfig": os.getenv("CERTBOT_AUTOCONFIG", ""),
        "eab_kid": os.getenv("CERTBOT_EAB_KID", ""),
        "eab_hmac_key": os.getenv("CERTBOT_EAB_HMAC_KEY", ""),
        "retry_count": int(os.getenv("CERTBOT_RETRY_COUNT", "60")),
        "preferred_challenges": os.getenv("CERTBOT_PREFERRED_CHALLENGES", "http"),
        "manual_auth_hook": os.getenv("CERTBOT_MANUAL_AUTH_HOOK", ""),
        "domains": [d.strip() for d in os.getenv("CERTBOT_DOMAINS", "").split(",") if d.strip()],
        "webhook_url": os.getenv("CERTBOT_WEBHOOK_URL", ""),
        "certs_dir": os.getenv("CERTBOT_CERTS_DIR", "/certs"),
        "api_port": int(os.getenv("CERTBOT_API_PORT", "8088")),
        "renewal_interval": int(os.getenv("CERTBOT_RENEWAL_INTERVAL", "43200")),
    }
