import os
from pathlib import Path


class classproperty:
    """Decorator for class-level properties."""
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, owner):
        return self.func(owner)


class Consts:
    """Configuration constants with dynamic path resolution based on EASYHAPROXY_BASE_PATH."""
    _base_path = None

    @classproperty
    def base_path(cls):
        """Base directory for all EasyHAProxy files."""
        if cls._base_path is None:
            if os.getenv("EASYHAPROXY_BASE_PATH"):
                default = os.getenv("EASYHAPROXY_BASE_PATH")
            elif os.getuid() == 0:
                default = "/etc/easyhaproxy"
            else:
                default = str(Path.home() / "easyhaproxy")
            cls._base_path = default
        return cls._base_path

    @classmethod
    def reset(cls):
        """Reset cached base path to pick up environment variable changes."""
        cls._base_path = None

    @classproperty
    def easyhaproxy_config(cls):
        """Path to static configuration file."""
        return f"{cls.base_path}/static/config.yml"

    @classproperty
    def haproxy_config(cls):
        """Path to generated HAProxy configuration file."""
        return f"{cls.base_path}/haproxy/haproxy.cfg"

    @classproperty
    def custom_config_folder(cls):
        """Path to custom HAProxy config snippets directory."""
        return f"{cls.base_path}/haproxy/conf.d"

    @classproperty
    def certs_certbot(cls):
        """Path to Certbot/ACME certificates directory."""
        return f"{cls.base_path}/certs/certbot"

    @classproperty
    def certs_haproxy(cls):
        """Path to user-provided certificates directory."""
        return f"{cls.base_path}/certs/haproxy"

    @classproperty
    def www_path(cls):
        """Path to the web assets directory (dashboard, static files)."""
        return f"{cls.base_path}/www"

    DASHBOARD_SERVER_PORT = 9190