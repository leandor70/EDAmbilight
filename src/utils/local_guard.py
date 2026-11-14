"""Who may talk to the web server.

The Eel server drives the LEDs, restarts and quits the app, launches OpenRGB:
by default only this PC may use it. Three checks run before every request
(pages, eel.js and the /eel WebSocket alike):

1. the peer address must be a loopback one (127.x.x.x, ::1), unless the user
   allowed other devices of the network (Settings > Web Server);
2. the Host header must name this PC (localhost, 127.0.0.1, [::1]): a web page
   that points its own domain at 127.0.0.1 (DNS rebinding) is refused;
3. the Origin header, when the browser sends one (always for WebSockets and
   cross-site requests), must be the same host and port as the request: another
   site open in the browser cannot open ws://localhost:<port>/eel and call the
   app's functions (cross-site WebSocket hijacking).

With remote access allowed, 1 and 2 are skipped; 3 always applies.
"""
from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

LOCAL_NAMES = {"localhost", "127.0.0.1", "::1"}


def is_loopback_addr(addr: str | None) -> bool:
    """True for 127.0.0.0/8, ::1 and IPv4-mapped loopback (::ffff:127.0.0.1)."""
    if not addr:
        return False
    addr = addr.strip()
    if addr.startswith("[") and addr.endswith("]"):
        addr = addr[1:-1]
    addr = addr.split("%", 1)[0]                  # IPv6 zone id
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_loopback


def split_host(host: str | None) -> tuple[str, int | None]:
    """'localhost:8001' -> ('localhost', 8001); '[::1]:8001' -> ('::1', 8001)."""
    host = (host or "").strip().lower()
    if not host:
        return "", None
    try:
        parts = urlsplit("//" + host)
        name  = parts.hostname or ""
        port  = parts.port
    except ValueError:
        return "", None
    return name.rstrip("."), port


def is_local_host_header(host: str | None) -> bool:
    name, _ = split_host(host)
    if name in LOCAL_NAMES:
        return True
    return is_loopback_addr(name)


def origin_matches(origin: str | None, host: str | None) -> bool:
    """No Origin (plain navigation, same-origin GET) is fine; otherwise it must
    be http(s)://<the same host:port the request was sent to>."""
    if origin is None or origin == "":
        return True
    if origin == "null":                          # sandboxed frame, file:// page
        return False
    try:
        o = urlsplit(origin)
        o_name, o_port = (o.hostname or "").rstrip("."), o.port
    except ValueError:
        return False
    if o.scheme not in ("http", "https"):
        return False
    h_name, h_port = split_host(host)
    if not h_name:
        return False
    default = 443 if o.scheme == "https" else 80
    return o_name == h_name and (o_port or default) == (h_port or default)


def check_request(remote_addr: str | None, host: str | None, origin: str | None,
                  allow_remote: bool = False) -> str | None:
    """None when the request may pass, otherwise the reason it is refused."""
    if not allow_remote:
        if not is_loopback_addr(remote_addr):
            return f"connection from {remote_addr or 'unknown address'} (only this PC is allowed)"
        if not is_local_host_header(host):
            return f"Host header '{host}' is not this PC"
    if not origin_matches(origin, host):
        return f"Origin '{origin}' does not match '{host}'"
    return None


def install(app, allow_remote: bool = False) -> None:
    """Refuse requests that fail check_request() on a Bottle app (Eel's)."""
    import bottle

    @app.hook("before_request")
    def _guard():
        env    = bottle.request.environ
        reason = check_request(env.get("REMOTE_ADDR"), env.get("HTTP_HOST"),
                               env.get("HTTP_ORIGIN"), allow_remote)
        if reason:
            print(f"[SECURITY] Refused {env.get('REQUEST_METHOD', '?')} "
                  f"{env.get('PATH_INFO', '')}: {reason}")
            raise bottle.HTTPError(403, "Forbidden")
