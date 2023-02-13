import json
import pytest
import os
import re
import random
import string
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
    command = daemon.get_haproxy_command("start")
    assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg  -p /run/haproxy.pid -S /var/run/haproxy.sock"

def test_daemonize_haproxy_get_haproxy_command_reload():
    daemon = DaemonizeHAProxy()
    command = daemon.get_haproxy_command("reload")
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
    command = daemon.get_haproxy_command("start")
    assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -f %s -p /run/haproxy.pid -S /var/run/haproxy.sock" % (os.path.dirname(__file__) + "/fixtures")

def test_daemonize_haproxy_get_haproxy_command_reload():
    daemon = DaemonizeHAProxy(os.path.abspath(os.path.dirname(__file__))  + '/fixtures')
    command = daemon.get_haproxy_command("reload")
    assert command == "/usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -f %s -p /run/haproxy.pid -x /var/run/haproxy.sock -sf " % (os.path.dirname(__file__) + "/fixtures")
