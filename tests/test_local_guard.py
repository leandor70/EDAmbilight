"""Only this PC may use the web server (unless the user allows the network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import bottle
import pytest

from utils.local_guard import (check_request, install, is_local_host_header,
                               is_loopback_addr, origin_matches)


@pytest.mark.parametrize("addr", ["127.0.0.1", "127.5.6.7", "::1", "[::1]",
                                  "::ffff:127.0.0.1"])
def test_loopback_addresses(addr):
    assert is_loopback_addr(addr)


@pytest.mark.parametrize("addr", ["192.168.1.10", "10.0.0.2", "::ffff:192.168.1.2",
                                  "fe80::1", "0.0.0.0", "", None, "evil"])
def test_other_addresses(addr):
    assert not is_loopback_addr(addr)


@pytest.mark.parametrize("host", ["localhost:8001", "LOCALHOST:8001", "127.0.0.1:8001",
                                  "[::1]:8001", "localhost", "localhost.:8001"])
def test_local_host_headers(host):
    assert is_local_host_header(host)


@pytest.mark.parametrize("host", ["evil.example:8001", "192.168.1.10:8001",
                                  "localhost.evil.example", "", None])
def test_foreign_host_headers(host):
    assert not is_local_host_header(host)


def test_origin_rules():
    assert origin_matches(None, "localhost:8001")
    assert origin_matches("http://localhost:8001", "localhost:8001")
    assert origin_matches("http://127.0.0.1:8001", "127.0.0.1:8001")
    # another site, another port, another name for the same PC, sandboxed pages
    assert not origin_matches("https://evil.example", "localhost:8001")
    assert not origin_matches("http://localhost:3000", "localhost:8001")
    assert not origin_matches("http://127.0.0.1:8001", "localhost:8001")
    assert not origin_matches("null", "localhost:8001")
    assert not origin_matches("file://", "localhost:8001")


def test_check_request_default_is_local_only():
    ok = check_request("127.0.0.1", "localhost:8001", "http://localhost:8001")
    assert ok is None
    assert check_request("127.0.0.1", "localhost:8001", None) is None
    assert check_request("192.168.1.20", "localhost:8001", None)            # LAN peer
    assert check_request("127.0.0.1", "rebind.evil.example:8001", None)     # DNS rebinding
    assert check_request("127.0.0.1", "localhost:8001", "https://evil.example")  # CSWSH


def test_check_request_remote_allowed_keeps_origin_check():
    assert check_request("192.168.1.20", "192.168.1.5:8001", None, allow_remote=True) is None
    assert check_request("192.168.1.20", "192.168.1.5:8001",
                         "http://192.168.1.5:8001", allow_remote=True) is None
    assert check_request("192.168.1.20", "192.168.1.5:8001",
                         "https://evil.example", allow_remote=True)


def _call(app, remote, host, origin=None):
    env = {"REQUEST_METHOD": "GET", "PATH_INFO": "/x", "REMOTE_ADDR": remote,
           "HTTP_HOST": host, "SERVER_NAME": "localhost", "SERVER_PORT": "8001",
           "wsgi.url_scheme": "http", "wsgi.input": None, "wsgi.errors": sys.stderr}
    if origin:
        env["HTTP_ORIGIN"] = origin
    status = {}
    body = b"".join(app(env, lambda s, h, *a: status.setdefault("s", s)))
    return int(status["s"].split()[0]), body


def test_install_refuses_with_403():
    app = bottle.Bottle()
    app.route("/x", callback=lambda: "ok")
    install(app)
    assert _call(app, "127.0.0.1", "localhost:8001") == (200, b"ok")
    assert _call(app, "192.168.1.20", "localhost:8001")[0] == 403
    assert _call(app, "127.0.0.1", "localhost:8001", "https://evil.example")[0] == 403
