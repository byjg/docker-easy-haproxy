from functions import Functions
from processor import ProcessorInterface
import os
import time
from threading import Thread

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

    Functions.save(haproxy_config, processor_obj.get_haproxy_conf())
    for cert in processor_obj.get_certs():
        Functions.save(certs_haproxy, processor_obj.get_certs(cert))

    #configs = Functions.run_bash('HAPROXY', 'ls /etc/haproxy/conf.d/*.cfg', log_output=False)
    x = Thread(target=Functions.run_bash, args=("HAPROXY", "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -S /var/run/haproxy.sock", True, False))
    x.start()

    while True:
        time.sleep(10)


def main():
    Functions.run_bash('INIT', '/usr/sbin/haproxy -v')

    Functions.log('INIT', 'info', "                      _                               ")
    Functions.log('INIT', 'info', " ___ __ _ ____  _ ___| |_  __ _ _ __ _ _ _____ ___  _ ")
    Functions.log('INIT', 'info', "/ -_) _` (_-< || |___| ' \/ _` | '_ \ '_/ _ \ \ / || |")
    Functions.log('INIT', 'info', "\___\__,_/__/\_, |   |_||_\__,_| .__/_| \___/_\_\\_, |")
    Functions.log('INIT', 'info', "             |__/              |_|               |__/ ")

    Functions.log('INIT', 'INFO', os.getenv("RELEASE_VERSION"))
    Functions.log('INIT', 'INFO', "")
    Functions.log('INIT', 'INFO', 'Environment:')
    for name, value in os.environ.items():
        if "HAPROXY" in name:
            print("- {0}: {1}".format(name, value))

if __name__ == '__main__':
    main()