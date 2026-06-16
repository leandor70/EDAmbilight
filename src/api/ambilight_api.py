"""
Ambilight API — Eel endpoints per EDAmbilight standalone.

Fonte unica di verita': ambilight_config.json
(il device_config.json del progetto principale non esiste qui).
"""

import eel
import json
from pathlib import Path
from typing import Optional

_ambilight_service: Optional[object] = None
_openrgb_manager:   Optional[object] = None


def init_ambilight_api(ambilight_service, openrgb_manager) -> None:
    global _ambilight_service, _openrgb_manager
    _ambilight_service = ambilight_service
    _openrgb_manager   = openrgb_manager
    print("[OK] Ambilight API initialized")


# ── Config ────────────────────────────────────────────────────────────────────


@eel.expose
def get_ambilight_config() -> dict:
    if _ambilight_service is None:
        return {}
    return _ambilight_service.get_config()


@eel.expose
def set_ambilight_config(updates: dict) -> dict:
    if _ambilight_service is None:
        return {"ok": False, "error": "Service not initialized"}
    try:
        _ambilight_service.set_config(updates)
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Status ────────────────────────────────────────────────────────────────────


@eel.expose
def get_ambilight_status() -> dict:
    if _ambilight_service is None:
        return {"running": False, "fps": 0.0, "capturer": "—", "enabled": False}
    cfg  = _ambilight_service.get_config()
    rect = _ambilight_service.content_rect
    return {
        "running":      _ambilight_service.is_running,
        "fps":          _ambilight_service.actual_fps,
        "capturer":     _ambilight_service.capturer_name,
        "enabled":      cfg.get("enabled", False),
        "content_rect": list(rect) if rect else None,
    }


# ── Device enumeration ────────────────────────────────────────────────────────


@eel.expose
def get_ambilight_devices() -> list:
    """Ritorna la lista dei device disponibili (no MATRIX/keyboard)."""
    if _openrgb_manager is None:
        return []

    from effects.ambilight_service import build_device_zones
    from effects.openrgb_manager import TopologyType

    ambi_cfg     = _ambilight_service.get_config() if _ambilight_service else {}
    ambi_devices = ambi_cfg.get("devices", {})
    result       = []

    for ctrl in _openrgb_manager.devices:
        if ctrl.topology.topology_type == TopologyType.MATRIX:
            continue

        device_key   = _openrgb_manager._make_device_key(ctrl)
        zones, _     = build_device_zones(device_key)
        ambi_entry   = ambi_devices.get(device_key, {})
        enabled      = ambi_entry.get("enabled", True)

        result.append({
            "device_key":    device_key,
            "name":          ctrl.topology.device.name,
            "led_count":     ctrl.topology.led_count,
            "topology_type": ctrl.topology.topology_type.value,
            "has_topology":  bool(zones),
            "zone_count":    len(zones),
            "enabled":       enabled,
        })

    return result


@eel.expose
def set_ambilight_device_enabled(device_key: str, enabled: bool) -> dict:
    if _ambilight_service is None:
        return {"ok": False, "error": "Service not initialized"}
    try:
        cfg     = _ambilight_service.get_config()
        devices = cfg.get("devices", {})
        if device_key not in devices:
            devices[device_key] = {}
        devices[device_key]["enabled"] = enabled
        _ambilight_service.set_config({"devices": devices})
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@eel.expose
def set_ambilight_zone_enabled(device_key: str, zone_name: str, enabled: bool) -> dict:
    if _ambilight_service is None:
        return {"ok": False, "error": "Service not initialized"}
    cfg     = _ambilight_service.get_config()
    devices = cfg.get("devices", {})
    if device_key not in devices:
        devices[device_key] = {}
    dev_entry = devices[device_key]
    if "zones_enabled" not in dev_entry:
        dev_entry["zones_enabled"] = {}
    dev_entry["zones_enabled"][zone_name] = enabled
    _ambilight_service.set_config({"devices": devices})
    return {"ok": True}


@eel.expose
def get_ambilight_device_zones(device_key: str) -> list:
    from effects.ambilight_service import build_device_zones
    zones, _ = build_device_zones(device_key)
    return zones
