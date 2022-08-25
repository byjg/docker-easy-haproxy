from functions import Functions, DaemonizeHAProxy, Certbot
from processor import ProcessorInterface
import os
import time
from deepdiff import DeepDiff

easyhaproxy_config = "/etc/haproxy/easyconfig.yml"
haproxy_config = "/etc/haproxy/haproxy.cfg"
certs_letsencrypt = "/certs/letsencrypt"
certs_haproxy = "/certs/haproxy"

def start():
    processor_obj = ProcessorInterface.factory(os.getenv("EASYHAPROXY_DISCOVER"))
    if processor_obj is None:
        exit(1)

    os.makedirs(certs_letsencrypt, exist_ok=True)
    os.makedirs(certs_haproxy, exist_ok=True)

    processor_obj.save_config(haproxy_config)
    processor_obj.save_certs(certs_haproxy)
    letsencrypt_certs_found = processor_obj.get_letsencrypt_hosts()
    Functions.log('EASYHAPROXY', 'debug', 'Found hosts: %s' % ", ".join(processor_obj.get_hosts())) # Needs to after save_config

    old_haproxy = None
    haproxy = DaemonizeHAProxy()
    haproxy.haproxy("start")

    certbot = Certbot(certs_letsencrypt, os.getenv("EASYHAPROXY_LETSENCRYPT_EMAIL"))

    while True:
        time.sleep(10)
        if old_haproxy is not None:
            old_haproxy.kill()
            old_haproxy = None
        try:
            old_parsed = processor_obj.get_parsed_object()
            processor_obj.refresh()
            if DeepDiff(old_parsed, processor_obj.get_parsed_object()) != {} or not haproxy.is_alive():
                Functions.log('EASYHAPROXY', 'debug', 'New configuration found. Reloading...')
                processor_obj.save_config(haproxy_config)
                processor_obj.save_certs(certs_haproxy)
                letsencrypt_certs_found = processor_obj.get_letsencrypt_hosts()
                Functions.log('EASYHAPROXY', 'debug', 'Found hosts: %s' % ", ".join(processor_obj.get_hosts())) # Needs to after save_config
                old_haproxy = haproxy
                haproxy = DaemonizeHAProxy()
                haproxy.haproxy("reload")
                old_haproxy.terminate()

            certbot.check_certificates(letsencrypt_certs_found)
        except Exception as e:
            Functions.log('EASYHAPROXY', 'fatal', "Err: %s" % (e))
        Functions.log('EASYHAPROXY', 'debug', 'Heartbeat')




def main():
    Functions.run_bash('INIT', '/usr/sbin/haproxy -v')

    Functions.log('INIT', 'info', "                      _                               ")
    Functions.log('INIT', 'info', " ___ __ _ ____  _ ___| |_  __ _ _ __ _ _ _____ ___  _ ")
    Functions.log('INIT', 'info', "/ -_) _` (_-< || |___| ' \/ _` | '_ \ '_/ _ \ \ / || |")
    Functions.log('INIT', 'info', "\___\__,_/__/\_, |   |_||_\__,_| .__/_| \___/_\_\\_, |")
    Functions.log('INIT', 'info', "             |__/              |_|               |__/ ")

    Functions.log('INIT', 'info', "Release: %s" % (os.getenv("RELEASE_VERSION")))
    Functions.log('INIT', 'debug', 'Environment:')
    for name, value in os.environ.items():
        if "HAPROXY" in name:
            Functions.log('INIT', 'debug', "- {0}: {1}".format(name, value))

    start()

if __name__ == '__main__':
    main()