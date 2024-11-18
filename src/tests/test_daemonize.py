import os

from functions import DaemonizeHAProxy, Functions


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

def test_daemonize_haproxy_get_haproxy_command_reload():
    daemon = DaemonizeHAProxy()
    command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_RELOAD)
    assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg  -p /run/haproxy.pid -x /var/run/haproxy.sock -sf "

def test_daemonize_haproxy_check_config():
    daemon = DaemonizeHAProxy(os.path.abspath(os.path.dirname(__file__))  + '/fixtures')
    filed = daemon.get_custom_config_files()
    assert filed == {
        os.path.dirname(__file__) + "/fixtures/00_haproxy.cfg": os.path.getmtime(os.path.dirname(__file__) + "/fixtures/00_haproxy.cfg"),
        os.path.dirname(__file__) + "/fixtures/10_haproxy.cfg": os.path.getmtime(os.path.dirname(__file__) + "/fixtures/10_haproxy.cfg")
    }

def test_daemonize_haproxy_get_haproxy_command_start():
    daemon = DaemonizeHAProxy(os.path.abspath(os.path.dirname(__file__))  + '/fixtures')
    command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_START)
    assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -f %s -p /run/haproxy.pid -S /var/run/haproxy.sock" % (os.path.dirname(__file__) + "/fixtures")


def test_daemonize_haproxy_get_haproxy_command_reload():
    tmp_pid_file = "/tmp/tmp_pid.txt"
    Functions.save(tmp_pid_file, "10")

    try:
        daemon = DaemonizeHAProxy(os.path.abspath(os.path.dirname(__file__))  + '/fixtures')
        command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_RELOAD, tmp_pid_file)
        assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -f %s -p %s -x /var/run/haproxy.sock -sf %s" % (os.path.dirname(__file__) + "/fixtures", tmp_pid_file, 10)
    finally:
        os.remove(tmp_pid_file)
