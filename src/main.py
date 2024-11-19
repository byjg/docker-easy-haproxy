import os
import logging

from deepdiff import DeepDiff

from functions import Functions, DaemonizeHAProxy, Certbot, Consts, loggerInit, loggerEasyHaproxy, loggerHaproxy, \
    loggerCertbot
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
    loggerEasyHaproxy.info('Found hosts: %s' % ", ".join(processor_obj.get_hosts()))  # Needs to run after save_config
    loggerEasyHaproxy.debug('Object Found: %s' % (processor_obj.get_parsed_object()))

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
                loggerEasyHaproxy.info('New configuration found. Reloading...')
                loggerEasyHaproxy.debug('Object Found: %s' % (processor_obj.get_parsed_object()))
                processor_obj.save_config(Consts.haproxy_config)
                processor_obj.save_certs(Consts.certs_haproxy)
                certbot_certs_found = processor_obj.get_certbot_hosts()
                loggerEasyHaproxy.info('Found hosts: %s' % ", ".join(processor_obj.get_hosts()))  # Needs to after save_config
                old_haproxy = haproxy
                haproxy = DaemonizeHAProxy()
                current_custom_config_files = haproxy.get_custom_config_files()
                haproxy.haproxy(DaemonizeHAProxy.HAPROXY_RELOAD)
                old_haproxy.terminate()

        except Exception as e:
            loggerEasyHaproxy.fatal("Err: %s" % e)

        loggerEasyHaproxy.info('Heartbeat')
        haproxy.sleep()


def main():
    Functions.run_bash(loggerInit, '/usr/sbin/haproxy -v')

    loggerInit.info("                      _                               ")
    loggerInit.info(" ___ __ _ ____  _ ___| |_  __ _ _ __ _ _ _____ ___  _ ")
    loggerInit.info("/ -_) _` (_-< || |___| ' \\/ _` | '_ \\ '_/ _ \\ \\ / || |")
    loggerInit.info("\\___\\__,_/__/\\_, |   |_||_\\__,_| .__/_| \\___/_\\_\\_, |")
    loggerInit.info("             |__/              |_|               |__/ ")

    loggerInit.info("Release: %s" % (os.getenv("RELEASE_VERSION")))
    loggerInit.debug('Environment:')
    for name, value in os.environ.items():
        if "HAPROXY" in name:
            loggerInit.debug("- {0}: {1}".format(name, value))

    start()


if __name__ == '__main__':
    main()
