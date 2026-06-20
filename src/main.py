"""EDAmbilight — main entry point."""
import sys
import os
import threading
import webbrowser
import eel
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.paths import get_base_dir
from settings import Settings

os.chdir(get_base_dir())

_init_status = {
    "ready":   False,
    "message": "Starting...",
    "step":    0,
    "total":   3,
    "error":   None,
    "openrgb": None,   # esito bootstrap OpenRGB (vedi utils.openrgb_bootstrap)
}
_settings_ref = None

SHUTDOWN_DELAY_SECS = 15
_shutdown_timer = None
_tray_icon      = None
_tray_active    = False
_web_port       = 8001


def _create_tray_image():
    from PIL import Image, ImageDraw
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size - 2, size - 2], fill=(0, 40, 60, 255))
    draw.ellipse([10, 10, size - 10, size - 10], fill=(5, 10, 18, 255))
    # Cyan horizontal bars
    for cy in [22, 32, 42]:
        draw.rectangle([18, cy - 3, 46, cy + 3], fill=(20, 245, 255, 255))
    return img


def _open_browser_from_tray(icon=None, item=None):
    webbrowser.open(f"http://localhost:{_web_port}")


def _exit_app(icon=None, item=None):
    global _tray_icon
    if _tray_icon is not None:
        try:
            _tray_icon.stop()
        except Exception:
            pass
    os._exit(0)


def _start_tray():
    global _tray_icon, _tray_active
    try:
        import pystray
        menu = pystray.Menu(
            pystray.MenuItem("EDAmbilight", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open browser", _open_browser_from_tray),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", _exit_app),
        )
        _tray_icon = pystray.Icon(
            name="EDAmbilight",
            icon=_create_tray_image(),
            title="EDAmbilight",
            menu=menu,
        )
        _tray_active = True
        _tray_icon.run_detached()
        print("[OK] System tray started")
    except Exception as e:
        print(f"[WARNING] System tray not available: {e}")
        _tray_active = False


@eel.expose
def get_init_status():
    return dict(_init_status)


@eel.expose
def cancel_shutdown():
    global _shutdown_timer
    if _shutdown_timer is not None:
        _shutdown_timer.cancel()
        _shutdown_timer = None


def _retry_openrgb_worker():
    from utils.openrgb_bootstrap import ensure_openrgb
    try:
        boot = ensure_openrgb(
            _settings_ref,
            status_cb=lambda m: _init_status["openrgb"].update({"detail": m})
                if isinstance(_init_status.get("openrgb"), dict) else None,
        )
    except Exception as e:
        boot = {"state": "error", "detail": str(e)}

    if boot.get("state") in ("connected", "launched"):
        from api.settings_api import reconnect_openrgb
        res = reconnect_openrgb()
        if res.get("ok"):
            boot["devices"] = res.get("devices", 0)
        else:
            boot["state"]  = "error"
            boot["detail"] = res.get("error", "Reconnection failed")
    _init_status["openrgb"] = boot


@eel.expose
def retry_openrgb():
    """Re-run the OpenRGB bootstrap (UI polls get_init_status for the result)."""
    if _settings_ref is None:
        return {"ok": False, "error": "Not initialized"}
    _init_status["openrgb"] = {"state": "retrying", "detail": "Retrying OpenRGB..."}
    threading.Thread(target=_retry_openrgb_worker, daemon=True,
                     name="openrgb-retry").start()
    return {"ok": True}


def _set_step(step, message):
    _init_status["step"]    = step
    _init_status["message"] = message
    print(f"  [{step}/3] {message}")


def _do_init(settings):
    try:
        # ── Step 1: OpenRGB ────────────────────────────────────────────────
        _set_step(1, "Connecting to OpenRGB...")
        openrgb_manager = None

        from utils.openrgb_bootstrap import ensure_openrgb
        try:
            boot = ensure_openrgb(settings, status_cb=lambda m: _set_step(1, m))
        except Exception as e:
            boot = {"state": "error", "detail": str(e)}
        _init_status["openrgb"] = boot
        print(f"       OpenRGB bootstrap: {boot.get('state')}"
              + (f" — {boot['detail']}" if boot.get("detail") else ""))

        if boot.get("state") in ("connected", "launched"):
            try:
                from openrgb import OpenRGBClient
                from effects.openrgb_manager import OpenRGBManager
                client          = OpenRGBClient(settings.get_openrgb_host(), settings.get_openrgb_port())
                openrgb_manager = OpenRGBManager(client)
                boot["devices"] = len(openrgb_manager.devices)
                print(f"       OpenRGB connected — {len(openrgb_manager.devices)} device(s)")
            except Exception as e:
                boot["state"]  = "error"
                boot["detail"] = f"SDK server reachable but connection failed: {e}"
                print(f"       OpenRGB not available: {e}")

        # ── Step 2: Ambilight service ──────────────────────────────────────
        _set_step(2, "Starting ambilight service...")
        from effects.ambilight_service import AmbilightService
        ambilight_svc = AmbilightService(openrgb_manager)
        ambilight_svc.start()

        # ── Step 3: APIs ───────────────────────────────────────────────────
        _set_step(3, "Initializing APIs...")
        from api.ambilight_api import init_ambilight_api
        from api.topology_api  import init_topology_api
        from api.settings_api  import init_settings_api

        init_settings_api(settings, openrgb_manager, ambilight_svc)
        init_ambilight_api(ambilight_svc, openrgb_manager)
        init_topology_api(openrgb_manager, ambilight_svc)

        _init_status["ready"]   = True
        _init_status["message"] = "Ready!"
        print()
        print("[OK] EDAmbilight ready")

    except Exception as e:
        import traceback
        traceback.print_exc()
        _init_status["error"]   = str(e)
        _init_status["message"] = f"Initialization error: {e}"
        print(f"[ERROR] Initialization failed: {e}")


def _on_browser_close(route, websockets):
    global _shutdown_timer
    # Leaving the topology editor (navigation or close) must stop an active
    # calibration, otherwise its thread keeps driving the LEDs and the
    # ambilight stays paused/blacked out.
    if route and "topology-editor" in route:
        try:
            from api.topology_api import stop_topology_calibration
            stop_topology_calibration()
        except Exception:
            pass
    if websockets:
        if _shutdown_timer is not None:
            _shutdown_timer.cancel()
            _shutdown_timer = None
        return
    if _tray_active:
        print("[INFO] Browser disconnected. App continues in system tray.")
        return
    print(f"[INFO] Browser disconnected. Shutting down in {SHUTDOWN_DELAY_SECS}s...")
    _shutdown_timer = threading.Timer(SHUTDOWN_DELAY_SECS, _exit_app)
    _shutdown_timer.daemon = True
    _shutdown_timer.start()


def main():
    print("=" * 55)
    print("  EDAmbilight — Screen Ambient Lighting Controller")
    print("=" * 55)
    print()

    global _web_port, _settings_ref

    settings      = Settings()
    _settings_ref = settings
    web_folder    = get_base_dir() / "web"

    eel.init(str(web_folder))
    print(f"[OK] Eel initialized  ({web_folder})")

    web_port  = settings.get_web_port()
    _web_port = web_port

    eel.start(
        "loading.html",
        size=(1280, 780),
        port=web_port,
        mode=None,
        block=False,
        shutdown_delay=0,
        close_callback=_on_browser_close,
    )

    _start_tray()
    webbrowser.open(f"http://localhost:{web_port}/loading.html")

    print(f"[OK] Server started — http://localhost:{web_port}")
    print("[OK] Background initialization starting...")
    print()

    init_thread = threading.Thread(
        target=_do_init,
        args=(settings,),
        daemon=True,
        name="ambilight-init",
    )
    init_thread.start()

    try:
        while True:
            eel.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user. Goodbye.")
        _exit_app()


if __name__ == "__main__":
    main()
