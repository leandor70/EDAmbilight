"""OpenRGB detection and auto-launch with SDK server (Windows).

States returned by ensure_openrgb():
  connected   — SDK server already reachable
  launched    — OpenRGB started (elevated) and SDK server came up
  no_server   — OpenRGB process running but SDK server port closed
  not_found   — OpenRGB not installed in any known location
  uac_denied  — user refused the UAC elevation prompt
  timeout     — OpenRGB launched but the SDK port never opened
  remote      — configured host is not local, cannot auto-launch
  disabled    — auto-launch disabled in settings
  error       — unexpected failure (see detail)
"""
import ctypes
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

DOWNLOAD_URL     = "https://openrgb.org"
DEFAULT_SDK_PORT = 6742
_LOCAL_HOSTS     = {"localhost", "127.0.0.1", "::1"}

# ShellExecuteW: return values <= 32 are errors; 5 = access denied (UAC refused)
_SE_ERR_ACCESSDENIED = 5


def _known_paths():
    candidates = []
    for env in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if base:
            candidates.append(Path(base) / "OpenRGB" / "OpenRGB.exe")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "Programs" / "OpenRGB" / "OpenRGB.exe")
    return candidates


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def find_openrgb(settings=None) -> Path | None:
    """User-configured path first, then known install locations."""
    if settings is not None:
        custom = settings.get_openrgb_path()
        if custom:
            p = Path(custom)
            if p.is_file():
                return p
    for p in _known_paths():
        if p.is_file():
            return p
    return None


def is_openrgb_running() -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq OpenRGB.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return "OpenRGB.exe" in out.stdout
    except Exception:
        return False


def launch_as_admin(exe: Path, sdk_port: int) -> str:
    """Start OpenRGB elevated with the SDK server active. Returns
    'launched', 'uac_denied' or 'error'."""
    # --gui keeps the window and tray icon: with only command-line options
    # OpenRGB 1.x runs headless, with nothing to open afterwards.
    params = "--gui --server --startminimized"
    if sdk_port != DEFAULT_SDK_PORT:
        params += f" --server-port {sdk_port}"
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", str(exe), params, str(exe.parent), 1
        )
    except Exception:
        return "error"
    if rc > 32:
        return "launched"
    if rc == _SE_ERR_ACCESSDENIED:
        return "uac_denied"
    return "error"


def wait_for_port(host: str, port: int, timeout: float = 30.0, status_cb=None) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_port_open(host, port, timeout=1.0):
            return True
        if status_cb:
            remaining = int(deadline - time.monotonic())
            status_cb(f"Waiting for OpenRGB SDK server... ({remaining}s)")
        time.sleep(1.0)
    return False


def ensure_openrgb(settings, status_cb=None) -> dict:
    """Make the OpenRGB SDK server reachable if at all possible."""
    def report(msg):
        if status_cb:
            status_cb(msg)

    host = settings.get_openrgb_host()
    port = settings.get_openrgb_port()

    if is_port_open(host, port):
        return {"state": "connected"}

    if host not in _LOCAL_HOSTS:
        return {
            "state":  "remote",
            "detail": f"OpenRGB host {host}:{port} is remote and unreachable.",
        }

    if not settings.get_openrgb_autostart():
        return {"state": "disabled", "detail": "OpenRGB auto-start disabled in settings."}

    if sys.platform != "win32":
        return {"state": "error", "detail": "Auto-launch is only supported on Windows."}

    if is_openrgb_running():
        # A second instance would fight over SMBus access: never force it.
        return {
            "state":  "no_server",
            "detail": ("OpenRGB is running but its SDK server is off. "
                       "In OpenRGB open Settings → SDK Server and press Start Server."),
        }

    exe = find_openrgb(settings)
    if exe is None:
        return {
            "state":        "not_found",
            "detail":       ("OpenRGB is not installed (or not in a known location). After installing "
                         "it, also install the PawnIO driver (pawnio.eu): without it memory modules "
                         "and motherboards are not detected."),
            "download_url": DOWNLOAD_URL,
        }

    report("Starting OpenRGB (administrator prompt)...")
    result = launch_as_admin(exe, port)
    if result == "uac_denied":
        return {
            "state":  "uac_denied",
            "detail": "Administrator permission was denied. OpenRGB needs it for hardware access.",
            "path":   str(exe),
        }
    if result != "launched":
        return {"state": "error", "detail": f"Could not start {exe}.", "path": str(exe)}

    report("OpenRGB starting, waiting for SDK server...")
    if wait_for_port(host, port, timeout=30.0, status_cb=status_cb):
        return {"state": "launched", "path": str(exe)}

    return {
        "state":  "timeout",
        "detail": ("OpenRGB was started but the SDK server did not come up. "
                   "In OpenRGB check Settings → SDK Server."),
        "path":   str(exe),
    }


def device_names_of_keys(keys) -> Counter:
    """Device names, with repeats, from device keys ("name::linear", "name::linear#2")."""
    return Counter(str(k).split("::")[0] for k in (keys or []))


def wait_devices_settled(client, stable_secs=5.0, timeout=45.0, expected=None,
                         missing_stable_secs=15.0, status_cb=None) -> bool:
    """Poll the device list of OpenRGB until its detection looks finished.

    OpenRGB opens its SDK server before it has finished detecting hardware, and
    detection does not take the same time at every start: on the same PC once
    3 s, once 13 s with 10 s without any new device in the middle (slow I2C
    memory modules). A count that stays still for a few seconds is therefore
    not enough when the PC has devices that come late.

    expected: the device names (Counter, repeats count) seen at the previous
    start. Done as soon as all of them are there. While some are missing the
    count must stay still for missing_stable_secs (a device really unplugged
    costs that once: the next start no longer expects it).
    Without expected: done when the count is non-zero and still for stable_secs.
    Returns True when every expected device is there (or nothing was expected).
    """
    expected = Counter(expected or {})
    deadline     = time.monotonic() + timeout
    last_count   = -1
    stable_since = time.monotonic()
    complete     = not expected
    while time.monotonic() < deadline:
        try:
            client.refresh()
        except Exception as e:
            print(f"       OpenRGB device poll failed: {e}")
            return complete
        count = len(client.devices)
        now   = time.monotonic()
        if expected:
            names = Counter(getattr(d, "name", "") for d in client.devices)
            have = sum(min(names[n], c) for n, c in expected.items())
            complete = have >= sum(expected.values())
            if complete:
                break
            if status_cb:
                status_cb(f"OpenRGB detecting devices... ({have} of {sum(expected.values())})")
        if count != last_count:
            last_count, stable_since = count, now
        elif count > 0 and now - stable_since >= (missing_stable_secs if expected else stable_secs):
            break
        time.sleep(1.0)
    missing = "" if complete else " (some devices of the last start are missing)"
    print(f"       OpenRGB detection settled: {len(client.devices)} device(s){missing}")
    return complete
