import os

from deepdiff import DeepDiff

from functions import (
    Certbot,
    Consts,
    DaemonizeHAProxy,
    Functions,
    logger_easyhaproxy,
    logger_init,
)
from processor import ProcessorInterface


def start():
    processor_obj = ProcessorInterface.factory(os.getenv("EASYHAPROXY_DISCOVER"))
    if processor_obj is None:
        exit(1)

    os.makedirs(Consts.certs_certbot, exist_ok=True)
    os.makedirs(Consts.certs_haproxy, exist_ok=True)

    processor_obj.save_config(Consts.haproxy_config)
    processor_obj.save_certs(Consts.certs_haproxy)
    certbot_certs_found = processor_obj.get_certbot_hosts()
    logger_easyhaproxy.info(f'Found hosts: {", ".join(processor_obj.get_hosts())}')  # Needs to run after save_config
    logger_easyhaproxy.debug(f'Object Found: {processor_obj.get_parsed_object()}')

    old_haproxy = None
    haproxy = DaemonizeHAProxy()
    current_custom_config_files = haproxy.get_custom_config_files()
    haproxy.haproxy(DaemonizeHAProxy.HAPROXY_START)
    haproxy.sleep()

    certbot = Certbot(Consts.certs_certbot)

    while True:
        if old_haproxy is not None:
            old_haproxy.kill()
            old_haproxy = None
        try:
            old_parsed = processor_obj.get_parsed_object()
            processor_obj.refresh()
            if certbot.check_certificates(certbot_certs_found) or DeepDiff(old_parsed, processor_obj.get_parsed_object()) != {} or not haproxy.is_alive() or DeepDiff(current_custom_config_files, haproxy.get_custom_config_files()) != {}:
                logger_easyhaproxy.info('New configuration found. Reloading...')
                logger_easyhaproxy.debug(f'Object Found: {processor_obj.get_parsed_object()}')
                processor_obj.save_config(Consts.haproxy_config)
                processor_obj.save_certs(Consts.certs_haproxy)
                certbot_certs_found = processor_obj.get_certbot_hosts()
                logger_easyhaproxy.info(f'Found hosts: {", ".join(processor_obj.get_hosts())}')  # Needs to after save_config
                old_haproxy = haproxy
                haproxy = DaemonizeHAProxy()
                current_custom_config_files = haproxy.get_custom_config_files()
                haproxy.haproxy(DaemonizeHAProxy.HAPROXY_RELOAD)
                old_haproxy.terminate()

        except Exception as e:
            logger_easyhaproxy.fatal(f"Err: {e}")

        logger_easyhaproxy.info('Heartbeat')
        haproxy.sleep()


def main():
    Functions.run_bash(logger_init, '/usr/sbin/haproxy -v')

    logger_init.info("                      _                               ")
    logger_init.info(" ___ __ _ ____  _ ___| |_  __ _ _ __ _ _ _____ ___  _ ")
    logger_init.info("/ -_) _` (_-< || |___| ' \\/ _` | '_ \\ '_/ _ \\ \\ / || |")
    logger_init.info("\\___\\__,_/__/\\_, |   |_||_\\__,_| .__/_| \\___/_\\_\\_, |")
    logger_init.info("             |__/              |_|               |__/ ")

    logger_init.info(f"Release: {os.getenv('RELEASE_VERSION')}")
    logger_init.debug('Environment:')
    for name, value in os.environ.items():
        if "HAPROXY" in name:
            logger_init.debug(f"- {name}: {value}")

    start()


if __name__ == '__main__':
    main()
