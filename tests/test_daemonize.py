import os

from functions import Consts, DaemonizeHAProxy

BIN = DaemonizeHAProxy.get_haproxy_bin()


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
    assert command == f"{BIN} -W -f {Consts.haproxy_config}  -p /run/haproxy.pid -S /var/run/haproxy.sock"

def test_daemonize_haproxy_get_haproxy_command_reload_nopid():
    daemon = DaemonizeHAProxy()
    command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_RELOAD)
    assert command == f"{BIN} -W -f {Consts.haproxy_config}  -p /run/haproxy.pid -S /var/run/haproxy.sock"

def test_daemonize_haproxy_get_haproxy_command_reload_pidinvalid():
    daemon = DaemonizeHAProxy()
    try:
        with open("/tmp/temp.pid", 'w') as file:
            file.write("-1001")
        command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_RELOAD, "/tmp/temp.pid")
        assert command == f"{BIN} -W -f {Consts.haproxy_config}  -p /tmp/temp.pid -S /var/run/haproxy.sock"
    finally:
        assert not os.path.exists("/tmp/temp.pid")

def test_daemonize_haproxy_get_haproxy_command_reload_existing_pin():
    daemon = DaemonizeHAProxy()
    try:
        with open("/tmp/temp.pid", 'w') as file:
            file.write("1")
        command = daemon.get_haproxy_command(DaemonizeHAProxy.HAPROXY_RELOAD, "/tmp/temp.pid")
        assert command == f"{BIN} -W -f {Consts.haproxy_config}  -p /tmp/temp.pid -x /var/run/haproxy.sock -sf 1"
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
    assert command == f"{BIN} -W -f {Consts.haproxy_config} -f {os.path.dirname(__file__)}/fixtures -p /run/haproxy.pid -S /var/run/haproxy.sock"


def _cert(folder, name, mtime):
    path = folder / name
    path.write_text("PEM")
    os.utime(path, (mtime, mtime))
    return str(path)


def test_cert_files_missing_folder(tmp_path):
    daemon = DaemonizeHAProxy(certs_folder=str(tmp_path / "missing"))
    assert daemon.get_cert_files() == {}


def test_cert_files_lists_only_pem(tmp_path):
    a = _cert(tmp_path, "a.example.com.pem", 1000)
    b = _cert(tmp_path, "b.example.com.pem", 2000)
    _cert(tmp_path, "notes.txt", 3000)
    _cert(tmp_path, "b.example.com.pem.tmp", 4000)

    daemon = DaemonizeHAProxy(certs_folder=str(tmp_path))
    assert daemon.get_cert_files() == {a: 1000, b: 2000}


def test_cert_files_change_when_a_certificate_is_added_replaced_or_removed(tmp_path):
    """HAProxy reads the certificate folder only on start or reload: these changes must show"""
    daemon = DaemonizeHAProxy(certs_folder=str(tmp_path))
    a = _cert(tmp_path, "a.example.com.pem", 1000)
    snapshot = daemon.get_cert_files()
    assert daemon.get_cert_files() == snapshot

    b = _cert(tmp_path, "b.example.com.pem", 2000)
    assert daemon.get_cert_files() != snapshot
    snapshot = daemon.get_cert_files()

    _cert(tmp_path, "a.example.com.pem", 3000)
    assert daemon.get_cert_files() == {a: 3000, b: 2000}
    snapshot = daemon.get_cert_files()

    os.unlink(b)
    assert daemon.get_cert_files() != snapshot
    assert daemon.get_cert_files() == {a: 3000}


def test_cert_folder_defaults_to_the_haproxy_certs():
    assert DaemonizeHAProxy().certs_folder == Consts.certs_haproxy
