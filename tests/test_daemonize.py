import os

from functions import DaemonizeHAProxy


def test_daemonize_haproxy():
    daemon = DaemonizeHAProxy()
    assert daemon is not None

def test_daemonize_haproxy_check_config():
    daemon = DaemonizeHAProxy()
    filed = daemon.get_custom_config_files()
    assert filed == {}

def test_daemonize_haproxy_get_haproxy_command_start():
    daemon = DaemonizeHAProxy()
    command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_START)
    assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg  -p /run/haproxy.pid -S /var/run/haproxy.sock"

def test_daemonize_haproxy_get_haproxy_command_reload_nopid():
    daemon = DaemonizeHAProxy()
    command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_RELOAD)
    assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg  -p /run/haproxy.pid -S /var/run/haproxy.sock"

def test_daemonize_haproxy_get_haproxy_command_reload_pidinvalid():
    daemon = DaemonizeHAProxy()
    try:
        with open("/tmp/temp.pid", 'w') as file:
            file.write("-1001")
        command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_RELOAD, "/tmp/temp.pid")
        assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg  -p /tmp/temp.pid -S /var/run/haproxy.sock"
    finally:
        assert not os.path.exists("/tmp/temp.pid")

def test_daemonize_haproxy_get_haproxy_command_reload_existing_pin():
    daemon = DaemonizeHAProxy()
    try:
        with open("/tmp/temp.pid", 'w') as file:
            file.write("1")
        command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_RELOAD, "/tmp/temp.pid")
        assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg  -p /tmp/temp.pid -x /var/run/haproxy.sock -sf 1"
    finally:
        assert os.path.exists("/tmp/temp.pid")
        os.unlink("/tmp/temp.pid")

def test_daemonize_haproxy2_check_config():
    daemon = DaemonizeHAProxy(os.path.abspath(os.path.dirname(__file__))  + '/fixtures')
    filed = daemon.get_custom_config_files()
    assert filed == {
        os.path.dirname(__file__) + "/fixtures/00_haproxy.cfg": os.path.getmtime(os.path.dirname(__file__) + "/fixtures/00_haproxy.cfg"),
        os.path.dirname(__file__) + "/fixtures/10_haproxy.cfg": os.path.getmtime(os.path.dirname(__file__) + "/fixtures/10_haproxy.cfg")
    }

def test_daemonize_haproxy2_get_haproxy_command_start():
    daemon = DaemonizeHAProxy(os.path.abspath(os.path.dirname(__file__))  + '/fixtures')
    command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_START)
    assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -f %s -p /run/haproxy.pid -S /var/run/haproxy.sock" % (os.path.dirname(__file__) + "/fixtures")
