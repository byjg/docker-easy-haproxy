from functions import Functions
from processor import ProcessorInterface
import os
import time
from threading import Thread
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
    Functions.log('EASYHAPROXY', 'info', 'Found hosts: %s' % ", ".join(processor_obj.get_hosts())) # Needs to after save_config

    #configs = Functions.run_bash('HAPROXY', 'ls /etc/haproxy/conf.d/*.cfg', log_output=False)
    x = Thread(target=Functions.run_bash, args=("HAPROXY", "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -S /var/run/haproxy.sock", True, False))
    x.start()

    while True:
        time.sleep(10)
        try:
            old_parsed = processor_obj.get_parsed_object()
            processor_obj.refresh()
            if DeepDiff(old_parsed, processor_obj.get_parsed_object()) != {} or not x.is_alive():
                Functions.log('EASYHAPROXY', 'info', 'New configuration found. Reloading...')
                processor_obj.save_config(haproxy_config)
                processor_obj.save_certs(certs_haproxy)
                Functions.log('EASYHAPROXY', 'info', 'Found hosts: %s' % ", ".join(processor_obj.get_hosts())) # Needs to after save_config
                pid = "".join(Functions().run_bash("HAPROXY", "cat /run/haproxy.pid", log_output=False))
                x = Thread(target=Functions.run_bash, args=("HAPROXY", "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -x /var/run/haproxy.sock -sf %s" % (pid), True, False))
                x.start()
        except Exception as e:
            Functions.log('EASYHAPROXY', 'error', "Err: %s" % (e))
        Functions.log('EASYHAPROXY', 'info', 'Heartbeat')




def main():
    Functions.run_bash('INIT', '/usr/sbin/haproxy -v')

    Functions.log('INIT', 'info', "                      _                               ")
    Functions.log('INIT', 'info', " ___ __ _ ____  _ ___| |_  __ _ _ __ _ _ _____ ___  _ ")
    Functions.log('INIT', 'info', "/ -_) _` (_-< || |___| ' \/ _` | '_ \ '_/ _ \ \ / || |")
    Functions.log('INIT', 'info', "\___\__,_/__/\_, |   |_||_\__,_| .__/_| \___/_\_\\_, |")
    Functions.log('INIT', 'info', "             |__/              |_|               |__/ ")

    Functions.log('INIT', 'info', "Release: %s" % (os.getenv("RELEASE_VERSION")))
    Functions.log('INIT', 'info', 'Environment:')
    for name, value in os.environ.items():
        if "HAPROXY" in name:
            Functions.log('INIT', 'info', "- {0}: {1}".format(name, value))

    start()

if __name__ == '__main__':
    main()