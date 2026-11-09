"""
topology_api.py — Topology editor API per EDAmbilight standalone.
Adattato da EDLogReader: rimossi riferimenti a try_ensure_openrgb e al
sistema effetti; usa direttamente OpenRGBManager.
"""

import eel
import json
import threading
import time as _time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

TOPOLOGY_CONFIG_FILE = Path("config/device_topologies.json")

_calib_thread: Optional[threading.Thread] = None
_calib_stop = threading.Event()

_openrgb_manager = None
_ambilight_service = None

# What changed on the hardware since the last start, shown to the user until
# dismissed. Each notice: {"kind": "added" | "changed" | "removed", "device", "text"}.
_hardware_notices: List[dict] = []
_notices_lock = threading.Lock()


def _seen_file() -> Path:
    """Devices detected at the previous start (next to the topology file)."""
    return TOPOLOGY_CONFIG_FILE.with_name("hardware_seen.json")


def _load_seen() -> Optional[List[str]]:
    """Device keys seen last time, or None when there is no record yet."""
    try:
        data = json.loads(_seen_file().read_text(encoding="utf-8"))
        return [str(k) for k in data.get("devices", [])]
    except Exception:
        return None


def _save_seen(keys: List[str]) -> None:
    try:
        _seen_file().write_text(
            json.dumps({"devices": sorted(keys)}, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        print(f"[TopologyAPI] Cannot save the list of detected devices: {e}")


def _add_notice(kind: str, device_key: str, text: str) -> None:
    with _notices_lock:
        if not any(n["kind"] == kind and n["device"] == device_key and n["text"] == text
                   for n in _hardware_notices):
            _hardware_notices.append({"kind": kind, "device": device_key, "text": text})


def add_hardware_notice(kind: str, key: str, text: str) -> None:
    """Show a notice at the top of the pages (see _add_notice)."""
    _add_notice(kind, key, text)


def _display_name(device_key: str) -> str:
    """'Strip::linear#2' -> 'Strip #2'."""
    name, _, rest = device_key.partition("::")
    suffix = f" {rest[rest.index('#'):]}" if "#" in rest else ""
    return name + suffix


@eel.expose
def get_hardware_notices() -> List[dict]:
    with _notices_lock:
        return [dict(n) for n in _hardware_notices]


@eel.expose
def dismiss_hardware_notices() -> dict:
    with _notices_lock:
        _hardware_notices.clear()
    return {"ok": True}


def init_topology_api(openrgb_manager=None, ambilight_service=None) -> None:
    global _openrgb_manager, _ambilight_service
    if openrgb_manager:
        _openrgb_manager = openrgb_manager
    if ambilight_service:
        _ambilight_service = ambilight_service
    _ensure_config_exists()
    sync_topologies_with_hardware()
    config         = _load_topologies()
    topology_count = len(config.get("topologies", {}))
    print(f"[TopologyAPI] Initialized ({topology_count} device topologies configured)")


def sync_topologies_with_hardware() -> List[str]:
    """At startup, make device_topologies.json agree with the hardware OpenRGB
    reports; the hardware always wins. Hardware is not expected to change
    while the app runs, so this is the only automatic check.

    - LINEAR device without a topology: its zones are imported.
    - LINEAR device whose zones differ from the hardware (zone count, name or
      LED count): re-synced via reload_device_from_openrgb, which keeps the
      layout of the zones that still exist.
    - Topology of a device that is no longer detected: left untouched, the
      device simply receives no colors.

    Runs at startup and after every successful OpenRGB reconnect. Returns the
    keys of the devices whose topology was written.
    """
    changed: List[str] = []
    if not _openrgb_manager:
        return changed
    from effects.openrgb_manager import TopologyType

    known = _load_topologies().get("topologies", {})
    seen = _load_seen()
    notify = seen is not None            # the first run has nothing to compare with
    current: List[str] = []
    for ctrl in _openrgb_manager.devices:
        if ctrl.topology.topology_type != TopologyType.LINEAR:
            continue
        device_key = _openrgb_manager._make_device_key(ctrl)
        current.append(device_key)

        if device_key not in known:
            result = reload_device_from_openrgb(device_key)
            if result["success"]:
                changed.append(device_key)
                n = len(result["zones"])
                print(f"[TopologyAPI] New device '{device_key}': imported "
                      f"{n} zone(s) from OpenRGB")
                if notify:
                    _add_notice("added", device_key,
                                f"New device detected: {_display_name(device_key)} "
                                f"({n} zone{'s' if n != 1 else ''} imported). "
                                f"It is off until you enable it in Control.")
            else:
                print(f"[TopologyAPI] New device '{device_key}': import failed "
                      f"({result.get('error')})")
            continue

        hw   = {z["zone_index"]: z for z in _read_openrgb_zones(ctrl.topology.device)}
        saved = known[device_key].get("zones", [])
        cfg   = {z.get("zone_index"): z for z in _renumber_legacy_zones(saved)}
        diff  = []
        if _has_duplicate_indexes(saved):
            diff.append("repeated zone indexes renumbered")
        for idx in sorted(hw.keys() | cfg.keys(), key=lambda i: (i is None, i)):
            h, c = hw.get(idx), cfg.get(idx)
            if c is None:
                diff.append(f"zone '{h['name']}' added")
            elif h is None:
                diff.append(f"zone '{c.get('name')}' removed")
            else:
                if c.get("name") != h["name"]:
                    diff.append(f"zone '{c.get('name')}' renamed '{h['name']}'")
                if c.get("led_count") != h["led_count"]:
                    diff.append(f"zone '{h['name']}' LEDs {c.get('led_count')}->{h['led_count']}")
        if not diff:
            continue

        result = reload_device_from_openrgb(device_key)
        if result["success"]:
            changed.append(device_key)
        status = "re-synced" if result["success"] else f"re-sync failed ({result.get('error')})"
        print(f"[TopologyAPI] '{device_key}' differs from hardware, {status}: " + "; ".join(diff))
        if notify and result["success"]:
            _add_notice("changed", device_key,
                        f"{_display_name(device_key)} changed on the hardware ("
                        + "; ".join(diff) + "). Its layout was updated; check it in Topology.")

    # An empty list means OpenRGB has not detected anything yet (hardware still
    # starting up): that is not the same as every device being unplugged.
    if current:
        if notify:
            for key in sorted(set(seen) - set(current)):
                print(f"[TopologyAPI] Device '{key}' is no longer detected")
                _add_notice("removed", key,
                            f"Device no longer detected: {_display_name(key)}. "
                            f"Its settings are kept and it receives no colors.")
        _save_seen(current)
    return changed


def _ensure_config_exists():
    if not TOPOLOGY_CONFIG_FILE.exists():
        TOPOLOGY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOPOLOGY_CONFIG_FILE.write_text(
            json.dumps({"version": 1, "topologies": {}}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _load_topologies() -> dict:
    _ensure_config_exists()
    try:
        return json.loads(TOPOLOGY_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[TopologyAPI] Error loading topologies: {e}")
        return {"version": 1, "topologies": {}}


def _save_topologies(config: dict) -> bool:
    try:
        TOPOLOGY_CONFIG_FILE.write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return True
    except Exception as e:
        print(f"[TopologyAPI] Error saving topologies: {e}")
        return False


# ── Screen rectangle ──────────────────────────────────────────────────────────

_RECT_KEYS = ("x_min", "x_max", "y_min", "y_max")


@eel.expose
def get_screen_rect() -> dict:
    """Where the screen sits in the scene (editor coordinates, y up).

    mode: "manual" (a rectangle is saved and decides the sides), "names" (no
    rectangle: the old Monitor* zone names decide) or "auto" (no rectangle, no
    such names: the bounding box of the scene). `suggested` is a starting
    rectangle for the editor ("Fit")."""
    from effects.ambilight_service import screen_frame, suggest_screen_rect
    data = _load_topologies()
    skip = key_grid_zone_ids()
    mode, _ = screen_frame(data, skip)
    return {
        "success":   True,
        "mode":      mode,
        "rect":      data.get("screen_rect") if mode == "manual" else None,
        "suggested": suggest_screen_rect(data, skip),
    }


@eel.expose
def set_screen_rect(rect) -> dict:
    """Save the screen rectangle (None removes it: back to automatic)."""
    try:
        data = _load_topologies()
        if rect is None:
            data.pop("screen_rect", None)
        else:
            clean = {k: float(rect[k]) for k in _RECT_KEYS}
            if clean["x_max"] <= clean["x_min"] or clean["y_max"] <= clean["y_min"]:
                return {"success": False, "error": "The rectangle has no area"}
            data["screen_rect"] = clean
        if not _save_topologies(data):
            return {"success": False, "error": "Could not write device_topologies.json"}
        if _ambilight_service:
            for key in data.get("topologies", {}):
                _ambilight_service.refresh_zones(key)
        return {"success": True}
    except (KeyError, TypeError, ValueError) as e:
        return {"success": False, "error": f"Invalid rectangle: {e}"}


# ── Key grids (keyboards) ─────────────────────────────────────────────────────
# A zone that OpenRGB gives as a key grid reads the whole screen key by key: its
# place in the scene means nothing, so the editor never shows it. It stays in
# device_topologies.json (LED offsets of the device depend on it).


def _key_grid_indexes(device_id: str) -> set:
    get_layouts = getattr(_openrgb_manager, "matrix_layouts", None)
    return set(get_layouts(device_id)) if get_layouts else set()


def key_grid_zone_ids() -> set:
    """(device_id, zone_index) of every key-grid zone, for the scene geometry."""
    if _openrgb_manager is None:
        return set()
    ids = set()
    for ctrl in getattr(_openrgb_manager, "devices", []):
        key = _openrgb_manager._make_device_key(ctrl)
        ids |= {(key, i) for i in _key_grid_indexes(key)}
    return ids


def _scene_zones(device_id: str, zones: list) -> list:
    """Zones the editor shows: no hidden ('???') ones, no key grids."""
    grids = _key_grid_indexes(device_id)
    return [z for z in _visible_zones(zones) if z.get("zone_index") not in grids]


# ── Hidden zones ──────────────────────────────────────────────────────────────


def _is_hidden_zone(zone: dict) -> bool:
    """Zones OpenRGB reports as '???' cannot be recognised on the hardware and
    never receive colors (the engine skips them), so the editor does not show
    them. They stay in the config: their LEDs still count for the offsets of
    the zones that follow."""
    from effects.ambilight_service import _is_unreadable_name
    return _is_unreadable_name(zone.get("name", ""))


def _visible_zones(zones: list) -> list:
    return [z for z in zones if not _is_hidden_zone(z)]


# ── Device list ───────────────────────────────────────────────────────────────


@eel.expose
def get_topology_devices() -> dict:
    """Return all LINEAR devices available for topology editing."""
    try:
        from effects.openrgb_manager import TopologyType

        if not _openrgb_manager:
            return {"success": False, "error": "Manager not initialized", "devices": []}

        topologies   = _load_topologies().get("topologies", {})
        ambi_devices = {}
        if _ambilight_service:
            ambi_devices = _ambilight_service.get_config().get("devices", {})
        result       = []

        for idx, ctrl in enumerate(_openrgb_manager.devices):
            if ctrl.topology.topology_type != TopologyType.LINEAR:
                continue

            device_key = _openrgb_manager._make_device_key(ctrl)
            if not ambi_devices.get(device_key, {}).get("enabled", True):
                continue

            topo       = topologies.get(device_key, {})

            result.append({
                "device_id":    device_key,
                "name":         ctrl.topology.device.name,
                "led_count":    ctrl.topology.led_count,
                "zone_count":   len(_visible_zones(topo.get("zones", []))),
                "has_topology": device_key in topologies,
            })

        return {"success": True, "devices": result}
    except Exception as e:
        return {"success": False, "error": str(e), "devices": []}


# ── CRUD ──────────────────────────────────────────────────────────────────────


@eel.expose
def get_device_topology(device_id: str) -> dict:
    try:
        config     = _load_topologies()
        topologies = config.get("topologies", {})
        if device_id not in topologies:
            return {"success": False, "device_id": device_id, "zones": [],
                    "error": f"No topology for {device_id}"}
        topo = topologies[device_id]
        return {
            "success":       True,
            "device_id":     device_id,
            "zones":         topo.get("zones", []),
            "effect_center": topo.get("effect_center", {"x": 50, "y": 50}),
            "last_modified": topo.get("last_modified"),
        }
    except Exception as e:
        return {"success": False, "device_id": device_id, "zones": [], "error": str(e)}


@eel.expose
def save_device_topology(device_id: str, zones: List[dict],
                         effect_center: Optional[dict] = None) -> dict:
    try:
        if not isinstance(zones, list):
            return {"success": False, "message": "Invalid zones data"}

        if effect_center is None or not isinstance(effect_center, dict):
            effect_center = {"x": 50, "y": 50}

        config     = _load_topologies()
        topologies = config.get("topologies", {})

        if effect_center is None and device_id in topologies:
            effect_center = topologies[device_id].get("effect_center", {"x": 50, "y": 50})

        topologies[device_id] = {
            "device_id":     device_id,
            "effect_center": effect_center,
            "zones":         zones,
            "last_modified": datetime.now().isoformat(),
            "zone_count":    len(zones),
            "total_leds":    sum(z.get("led_count", 0) for z in zones),
        }
        config["topologies"] = topologies

        if _save_topologies(config):
            # Invalidate ambilight zone cache
            if _ambilight_service:
                _ambilight_service.refresh_zones(device_id)
            return {"success": True, "message": f"Topology saved: {len(zones)} zones"}
        return {"success": False, "message": "File write error"}
    except Exception as e:
        return {"success": False, "message": "Error saving topology", "error": str(e)}


@eel.expose
def get_all_device_topologies() -> dict:
    try:
        config = _load_topologies()
        return {"success": True, "topologies": config.get("topologies", {})}
    except Exception as e:
        return {"success": False, "topologies": {}, "error": str(e)}


@eel.expose
def delete_device_topology(device_id: str) -> dict:
    try:
        config     = _load_topologies()
        topologies = config.get("topologies", {})
        if device_id in topologies:
            del topologies[device_id]
            config["topologies"] = topologies
            if _save_topologies(config):
                if _ambilight_service:
                    _ambilight_service.refresh_zones(device_id)
                return {"success": True, "message": f"Topology deleted for {device_id}"}
        return {"success": False, "message": f"No topology found for {device_id}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ── Scene ─────────────────────────────────────────────────────────────────────


@eel.expose
def get_scene_topology() -> dict:
    """Load all enabled LINEAR device zones for the unified scene editor."""
    try:
        config         = _load_topologies()
        topologies     = config.get("topologies", {})
        global_center  = config.get("global_effect_center", {"x": 50, "y": 50, "enabled": False})

        devs_result = get_topology_devices()
        if not devs_result["success"]:
            return {"success": False, "error": devs_result.get("error"), "zones": [], "devices": []}

        all_zones   = []
        device_meta = []

        for dev in devs_result["devices"]:
            device_id     = dev["device_id"]
            topo          = topologies.get(device_id, {})
            stored        = _visible_zones(topo.get("zones", []))
            zones         = _scene_zones(device_id, topo.get("zones", []))
            if stored and not zones:
                continue      # only key grids (a keyboard): nothing to place
            default_color = zones[0].get("color", "#14F5FF") if zones else "#14F5FF"

            for zone in zones:
                z = zone.copy()
                z["device_id"] = device_id
                all_zones.append(z)

            device_meta.append({
                "device_id":  device_id,
                "name":       dev["name"],
                "led_count":  dev["led_count"],
                "zone_count": len(zones),
                "color":      default_color,
            })

        return {
            "success":              True,
            "zones":                all_zones,
            "devices":              device_meta,
            "global_effect_center": global_center,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "zones": [], "devices": []}


@eel.expose
def save_scene_topology(zones: list, global_effect_center: dict) -> dict:
    """Save all device zones + global effect center in one call."""
    try:
        config     = _load_topologies()
        topologies = config.get("topologies", {})

        by_device: Dict[str, list] = {}
        for zone in zones:
            did = zone.get("device_id")
            if did:
                by_device.setdefault(did, []).append(zone)

        for device_id, device_zones in by_device.items():
            if device_id not in topologies:
                topologies[device_id] = {"device_id": device_id}
            # The editor never sees hidden ('???') zones: keep the stored ones,
            # otherwise saving would drop their LEDs and shift every later zone.
            grids  = _key_grid_indexes(device_id)
            hidden = [z for z in topologies[device_id].get("zones", [])
                      if _is_hidden_zone(z) or z.get("zone_index") in grids]
            if hidden:
                device_zones = sorted(device_zones + hidden,
                                      key=lambda z: z.get("zone_index", 0))
            topologies[device_id]["zones"]         = device_zones
            topologies[device_id]["zone_count"]    = len(device_zones)
            topologies[device_id]["total_leds"]    = sum(z.get("led_count", 0) for z in device_zones)
            topologies[device_id]["last_modified"] = datetime.now().isoformat()
            if _ambilight_service:
                _ambilight_service.refresh_zones(device_id)

        config["topologies"]           = topologies
        config["global_effect_center"] = global_effect_center
        _save_topologies(config)

        total = sum(len(v) for v in by_device.values())
        return {"success": True, "message": f"Scene saved: {total} zones"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Reload from OpenRGB ───────────────────────────────────────────────────────


def _read_openrgb_zones(device) -> List[dict]:
    """Zones (or segments, when a zone has them) as reported by the hardware.

    zone_index is a progressive counter over every zone/segment of the device,
    in hardware order: unique even when several zones have segments, and equal
    to the zone position for devices without segments.
    """
    zones = []
    for zone in device.zones:
        if hasattr(zone, "segments") and len(zone.segments) > 0:
            for segment in zone.segments:
                idx = len(zones)
                zones.append({
                    "zone_index": idx,
                    "name":       segment.name if hasattr(segment, "name") else f"Segment {idx}",
                    "led_count":  getattr(segment, "leds_count", len(getattr(segment, "leds", [])))
                })
        else:
            zones.append({
                "zone_index": len(zones),
                "name":       zone.name,
                "led_count":  len(zone.leds),
            })
    return zones


def _has_duplicate_indexes(zones: List[dict]) -> bool:
    indexes = [z.get("zone_index") for z in zones]
    return len(indexes) != len(set(indexes))


def _renumber_legacy_zones(zones: List[dict]) -> List[dict]:
    """Topologies saved with segments by older versions have repeated
    zone_index values (the segment counter restarted for every zone). The
    saved list is in hardware order, so renumber it by position."""
    if not _has_duplicate_indexes(zones):
        return zones
    return [{**z, "zone_index": i} for i, z in enumerate(zones)]


@eel.expose
def reload_device_from_openrgb(device_id: str) -> dict:
    """Sync LED counts from live OpenRGB device data."""
    try:
        if not _openrgb_manager:
            return {"success": False, "device_id": device_id, "error": "Manager not initialized"}

        # Find device in manager
        device_ctrl = None
        for ctrl in _openrgb_manager.devices:
            if _openrgb_manager._make_device_key(ctrl) == device_id:
                device_ctrl = ctrl
                break

        if not device_ctrl:
            return {"success": False, "device_id": device_id,
                    "error": f"Device not found: {device_id}"}

        device = device_ctrl.topology.device

        ZONE_COLORS = ["#14F5FF", "#FF6600", "#00FF00", "#FF00FF",
                       "#FFFF00", "#FF0088", "#00FF88", "#8800FF"]

        openrgb_zones = _read_openrgb_zones(device)

        config        = _load_topologies()
        topologies    = config.get("topologies", {})
        existing_zones = _renumber_legacy_zones(topologies.get(device_id, {}).get("zones", []))

        updated_zones = []
        changes       = {"led_count_changes": [], "new_zones": [], "removed_zones": []}

        for oz in openrgb_zones:
            existing = next((e for e in existing_zones if e.get("zone_index") == oz["zone_index"]), None)
            if existing:
                old_count = existing.get("led_count", 0)
                new_count = oz["led_count"]
                upd = existing.copy()
                upd["led_count"] = new_count
                upd["name"]      = oz["name"]
                upd["color"]     = existing.get("color", ZONE_COLORS[oz["zone_index"] % len(ZONE_COLORS)])
                upd.setdefault("position",    {"x": 0, "y": oz["zone_index"]})
                upd.setdefault("rotation",    0)
                upd.setdefault("direction",   "forward")
                upd.setdefault("hasOverlap",  False)
                upd.setdefault("device_id",   device_id)
                upd.setdefault("id",          oz["zone_index"])
                upd.setdefault("zone_index",  oz["zone_index"])
                if old_count != new_count:
                    changes["led_count_changes"].append({"zone": oz["name"], "old": old_count, "new": new_count})
                updated_zones.append(upd)
            else:
                updated_zones.append({
                    "id": oz["zone_index"], "name": oz["name"], "device_id": device_id,
                    "zone_index": oz["zone_index"], "led_count": oz["led_count"],
                    "position": {"x": 0, "y": oz["zone_index"]}, "rotation": 0,
                    "direction": "forward", "color": ZONE_COLORS[oz["zone_index"] % len(ZONE_COLORS)],
                    "hasOverlap": False,
                })
                changes["new_zones"].append(oz["name"])

        for ez in existing_zones:
            if ez.get("zone_index") not in [o["zone_index"] for o in openrgb_zones]:
                changes["removed_zones"].append(ez.get("name", f"Zone {ez.get('zone_index')}"))

        existing_center = topologies.get(device_id, {}).get("effect_center", {"x": 50, "y": 50})
        topologies[device_id] = {
            "device_id":     device_id,
            "effect_center": existing_center,
            "zones":         updated_zones,
            "last_modified": datetime.now().isoformat(),
            "zone_count":    len(updated_zones),
            "total_leds":    sum(z["led_count"] for z in updated_zones),
        }
        config["topologies"] = topologies
        if not _save_topologies(config):
            return {"success": False, "device_id": device_id, "error": "File write failed"}

        if _ambilight_service:
            _ambilight_service.refresh_zones(device_id)

        return {"success": True, "device_id": device_id, "zones": updated_zones, "changes": changes,
                "message": f"Reloaded {len(updated_zones)} zones"}
    except Exception as e:
        return {"success": False, "device_id": device_id, "error": str(e)}


@eel.expose
def reload_scene_from_openrgb() -> dict:
    devs_result = get_topology_devices()
    if not devs_result["success"]:
        return {"success": False, "error": devs_result.get("error"), "zones": []}

    all_zones  = []
    all_changes = {}

    for dev in devs_result["devices"]:
        result = reload_device_from_openrgb(dev["device_id"])
        if result["success"]:
            scene = _scene_zones(dev["device_id"], result.get("zones", []))
            for zone in scene:
                z = zone.copy()
                z["device_id"] = dev["device_id"]
                all_zones.append(z)
            if scene:
                all_changes[dev["name"]] = result.get("changes", {})

    return {
        "success": True,
        "zones":   all_zones,
        "changes": all_changes,
        "message": f"Reloaded {len(all_zones)} zones",
    }


# ── Flash & Calibration ───────────────────────────────────────────────────────


@eel.expose
def flash_topology_device(device_id: str) -> dict:
    """Flash a device white for identification."""
    if not _openrgb_manager:
        return {"success": False, "error": "Manager not initialized"}
    # Pause the ambilight so the flash isn't immediately overwritten by the
    # next sampled frame, and serialize writes through the manager lock so we
    # don't interleave packets with another writer.
    if _ambilight_service:
        _ambilight_service.pause()
    try:
        import time
        from core.openrgb_sdk import RGBColor
        lock = _openrgb_manager._lock
        for ctrl in _openrgb_manager.devices:
            if _openrgb_manager._make_device_key(ctrl) == device_id:
                n  = ctrl.topology.led_count
                on = [RGBColor(255, 255, 255)] * n
                of = [RGBColor(0, 0, 0)] * n
                for frame, delay in ((on, 0.15), (of, 0.10), (on, 0.15), (of, 0.0)):
                    with lock:
                        ctrl.topology.device.set_colors(frame)
                    if delay:
                        time.sleep(delay)
                return {"success": True}
        return {"success": False, "error": f"Device not found: {device_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if _ambilight_service:
            _ambilight_service.resume()


def _calibration_loop(device_led_data: list, stop_event: threading.Event,
                      blink_config: dict, write_lock: threading.Lock = None) -> None:
    RING_COLORS = [(255, 255, 255), (255, 60, 60), (80, 140, 255), (60, 210, 70)]
    COLOR_KEYS  = ["white", "red", "blue", "green"]

    # Group by device
    by_device: Dict = {}
    for entry in device_led_data:
        by_device.setdefault(entry[0], []).append(entry)

    while not stop_event.is_set():
        t_ms = _time.monotonic() * 1000.0
        try:
            from core.openrgb_sdk import RGBColor
        except ImportError:
            stop_event.wait(0.05)
            continue

        for ctrl, entries in by_device.items():
            colors = [RGBColor(0, 0, 0)] * ctrl.topology.led_count
            for _, hw_idx, ring_idx, is_center in entries:
                # The saved topology may declare more LEDs than the hardware
                # reports; skip indices that fall outside the real LED range.
                if not (0 <= hw_idx < len(colors)):
                    continue
                if is_center:
                    cfg     = blink_config.get("center", {})
                    period  = max(100, cfg.get("period_ms", 333))
                    on_flag = int(t_ms / (period / 2)) % 2 == 0
                    c       = (255, 255, 255) if (not cfg.get("blink", True) or on_flag) else (0, 0, 0)
                else:
                    key    = COLOR_KEYS[ring_idx % 4]
                    cfg    = blink_config.get(key, {})
                    base   = RING_COLORS[ring_idx % 4]
                    if cfg.get("blink", False):
                        period  = max(100, cfg.get("period_ms", 1000))
                        on_flag = int(t_ms / (period / 2)) % 2 == 0
                        c       = base if on_flag else (0, 0, 0)
                    else:
                        c = base
                colors[hw_idx] = RGBColor(*c)
            try:
                if write_lock is not None:
                    with write_lock:
                        ctrl.topology.device.set_colors(colors)
                else:
                    ctrl.topology.device.set_colors(colors)
            except Exception:
                pass

        stop_event.wait(0.05)


@eel.expose
def test_topology_calibration(ring_map: dict, blink_config: dict = None) -> dict:
    """Apply the calibration ring colors computed by the editor canvas.

    The canvas is the single source of truth for the geometry (ring index per
    physical LED), so the backend no longer recomputes positions/center —
    physical LEDs always match the drawing. ring_map maps a device_key to a
    list of [hw_idx, ring_idx, is_center] entries."""
    if blink_config is None:
        blink_config = {"center": {"blink": True, "period_ms": 333}}
    global _calib_thread, _calib_stop

    if not _openrgb_manager:
        return {"success": False, "error": "Manager not initialized"}

    if _ambilight_service:
        _ambilight_service.pause()

    _calib_stop.set()
    if _calib_thread and _calib_thread.is_alive():
        _calib_thread.join(timeout=0.3)

    try:
        ctrl_by_key = {_openrgb_manager._make_device_key(c): c
                       for c in _openrgb_manager.devices}

        led_data = []
        for device_key, entries in (ring_map or {}).items():
            ctrl = ctrl_by_key.get(device_key)
            if ctrl is None:
                continue
            for entry in entries:
                hw_idx, ring_idx = int(entry[0]), int(entry[1])
                is_ctr = bool(entry[2]) if len(entry) > 2 else False
                led_data.append((ctrl, hw_idx, ring_idx, is_ctr))

        if not led_data:
            return {"success": False, "error": "No calibration LEDs"}

        write_lock = _openrgb_manager._lock
        _calib_stop  = threading.Event()
        _calib_thread = threading.Thread(
            target=_calibration_loop,
            args=(led_data, _calib_stop, blink_config, write_lock),
            daemon=True, name="TopologyCalibration",
        )
        _calib_thread.start()
        return {"success": True, "leds_colored": len(led_data)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@eel.expose
def stop_topology_calibration() -> dict:
    global _calib_thread, _calib_stop
    # No-op if calibration isn't running, so it's safe to call on every page
    # leave without disturbing the ambilight on normal navigation.
    if _calib_thread is None:
        return {"success": True, "already_stopped": True}
    _calib_stop.set()
    if _calib_thread.is_alive():
        _calib_thread.join(timeout=0.5)
    _calib_thread = None
    # Turn off all LEDs
    if _openrgb_manager:
        try:
            from core.openrgb_sdk import RGBColor
            from effects.openrgb_manager import TopologyType
            for ctrl in _openrgb_manager.devices:
                if ctrl.topology.topology_type == TopologyType.LINEAR:
                    off = [RGBColor(0, 0, 0)] * ctrl.topology.led_count
                    ctrl.topology.device.set_colors(off)
        except Exception:
            pass
    if _ambilight_service:
        _ambilight_service.resume()
    return {"success": True}
