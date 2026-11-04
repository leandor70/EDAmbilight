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


@eel.expose
def set_standby_preview(active: bool) -> dict:
    """Start/stop a manual test of the selected Screen standby effect."""
    if _ambilight_service is None:
        return {"ok": False, "error": "Service not initialized"}
    return {"ok": True, "active": _ambilight_service.set_standby_preview(bool(active))}


# ── Status ────────────────────────────────────────────────────────────────────


@eel.expose
def get_ambilight_status() -> dict:
    if _ambilight_service is None:
        return {"running": False, "fps": 0.0, "capturer": "—", "enabled": False,
                "active_devices": 0, "active_zones": 0, "devices_total": 0,
                "mapped_devices": 0}
    from effects.ambilight_service import is_zone_enabled
    cfg  = _ambilight_service.get_config()
    rect = _ambilight_service.content_rect

    # How many devices/zones actually receive colors right now
    active_devices = active_zones = 0
    for device_key, dev_cfg in cfg.get("devices", {}).items():
        if not dev_cfg.get("enabled", False):
            continue
        try:
            zones, _ = _ambilight_service.get_device_zones(device_key)
        except Exception:
            continue
        zones_enabled = dev_cfg.get("zones_enabled", {})
        n = sum(1 for z in zones if is_zone_enabled(zones_enabled, z))
        if n:
            active_devices += 1
            active_zones   += n

    return {
        "running":        _ambilight_service.is_running,
        "fps":            _ambilight_service.actual_fps,
        "capturer":       _ambilight_service.capturer_name,
        "enabled":        cfg.get("enabled", False),
        "standby":        bool(getattr(_ambilight_service, "standby_active", False)),
        "standby_preview": bool(getattr(_ambilight_service, "standby_preview_active", False)),
        "content_rect":   list(rect) if rect else None,
        "active_devices": active_devices,
        "active_zones":   active_zones,
        "devices_total":  len(_openrgb_manager.devices) if _openrgb_manager else 0,
        "mapped_devices": len(_mapped_device_keys()),
    }


def _mapped_device_keys() -> list:
    """Device keys (non-matrix) that have at least one mapped zone."""
    if _openrgb_manager is None or _ambilight_service is None:
        return []
    keys = []
    for ctrl in _openrgb_manager.devices:
        key = _openrgb_manager._make_device_key(ctrl)
        try:
            zones, _ = _ambilight_service.get_device_zones(key)
        except Exception:
            continue
        if zones:
            keys.append(key)
    return keys


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
        enabled      = ambi_entry.get("enabled", False)  # same default as the engine

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
def set_ambilight_zone_enabled(device_key: str, zone_index, enabled: bool) -> dict:
    """zone_index is the zone's index (legacy callers may still pass a name)."""
    if _ambilight_service is None:
        return {"ok": False, "error": "Service not initialized"}
    cfg     = _ambilight_service.get_config()
    devices = cfg.get("devices", {})
    if device_key not in devices:
        devices[device_key] = {}
    dev_entry = devices[device_key]
    if "zones_enabled" not in dev_entry:
        dev_entry["zones_enabled"] = {}
    dev_entry["zones_enabled"][str(zone_index)] = enabled
    _ambilight_service.set_config({"devices": devices})
    return {"ok": True}


@eel.expose
def get_ambilight_device_zones(device_key: str) -> list:
    from effects.ambilight_service import build_device_zones
    zones, _ = build_device_zones(device_key)
    return zones
