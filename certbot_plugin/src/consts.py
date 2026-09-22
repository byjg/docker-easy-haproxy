import os


class PluginConsts:
    """Path constants for the certbot plugin, relative to CERTBOT_CERTS_DIR."""

    @staticmethod
    def certs_dir():
        return os.getenv("CERTBOT_CERTS_DIR", "/certs")

    @staticmethod
    def live_dir():
        return os.path.join(PluginConsts.certs_dir(), "live")

    @staticmethod
    def work_dir():
        return os.path.join(PluginConsts.certs_dir(), "work")

    @staticmethod
    def logs_dir():
        return os.path.join(PluginConsts.certs_dir(), "logs")
