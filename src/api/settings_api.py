"""Settings API — Eel endpoints per configurazione EDAmbilight."""

import eel
from typing import Optional

_settings:          Optional[object] = None
_openrgb_manager:   Optional[object] = None
_ambilight_service: Optional[object] = None


def init_settings_api(settings, openrgb_manager=None, ambilight_service=None) -> None:
    global _settings, _openrgb_manager, _ambilight_service
    _settings          = settings
    _openrgb_manager   = openrgb_manager
    _ambilight_service = ambilight_service
    print("[OK] Settings API initialized")


@eel.expose
def get_settings() -> dict:
    if _settings is None:
        return {}
    return {
        "openrgb_host":      _settings.get_openrgb_host(),
        "openrgb_port":      _settings.get_openrgb_port(),
        "openrgb_path":      _settings.get_openrgb_path(),
        "openrgb_autostart": _settings.get_openrgb_autostart(),
        "language":          _settings.get_language(),
        "theme":             _settings.get_theme(),
        "help_seen":         bool(_settings.settings.get("help_seen", False)),
    }


@eel.expose
def save_settings(updates: dict) -> dict:
    if _settings is None:
        return {"ok": False, "error": "Settings not initialized"}
    try:
        if "openrgb_host" in updates or "openrgb_port" in updates:
            host = updates.get("openrgb_host", _settings.get_openrgb_host())
            port = int(updates.get("openrgb_port", _settings.get_openrgb_port()))
            _settings.set_openrgb_connection(host, port)
        if "language" in updates:
            _settings.set_language(updates["language"])
        if "theme" in updates:
            _settings.set_theme(updates["theme"])
        if "web_port" in updates:
            _settings.settings["web_port"] = int(updates["web_port"])
            _settings._save()
        if "openrgb_path" in updates:
            _settings.settings["openrgb_path"] = str(updates["openrgb_path"])
            _settings._save()
        if "help_seen" in updates:
            _settings.settings["help_seen"] = bool(updates["help_seen"])
            _settings._save()
        if "openrgb_autostart" in updates:
            _settings.settings["openrgb_autostart"] = bool(updates["openrgb_autostart"])
            _settings._save()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@eel.expose
def reconnect_openrgb() -> dict:
    """Reconnect to OpenRGB with current settings."""
    global _openrgb_manager
    if _settings is None:
        return {"ok": False, "error": "Settings not initialized"}
    try:
        host = _settings.get_openrgb_host()
        port = _settings.get_openrgb_port()

        if _openrgb_manager is not None:
            ok = _openrgb_manager.reconnect(host, port)
            if ok:
                # The hardware may differ from before the disconnect:
                # re-align the topology (also refreshes the zone cache).
                from api.topology_api import sync_topologies_with_hardware
                sync_topologies_with_hardware()
                return {"ok": True, "devices": len(_openrgb_manager.devices)}
            return {"ok": False, "error": f"Cannot connect to {host}:{port}"}

        # Manager è None: OpenRGB non era attivo all'avvio. Connessione da zero.
        from core.openrgb_sdk import OpenRGBClient
        from effects.openrgb_manager import OpenRGBManager
        from api.ambilight_api import init_ambilight_api
        from api.topology_api  import init_topology_api

        client          = OpenRGBClient(host, port)
        new_manager     = OpenRGBManager(client)
        _openrgb_manager = new_manager

        # Aggiorna il riferimento al manager nel service in esecuzione
        if _ambilight_service is not None:
            _ambilight_service._manager = new_manager

        init_ambilight_api(_ambilight_service, new_manager)
        init_topology_api(new_manager, _ambilight_service)

        return {"ok": True, "devices": len(new_manager.devices)}

    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@eel.expose
def test_openrgb_connection(host: str, port: int) -> dict:
    """Test connectivity to OpenRGB without saving settings."""
    try:
        from core.openrgb_sdk import OpenRGBClient
        with OpenRGBClient(host, int(port)) as client:
            return {"ok": True, "devices": len(client.devices)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


