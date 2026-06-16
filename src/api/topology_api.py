"""
topology_api.py — Topology editor API per EDAmbilight standalone.
Adattato da EDLogReader: rimossi riferimenti a try_ensure_openrgb e al
sistema effetti; usa direttamente OpenRGBManager.
"""

import eel
import json
import math
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


def init_topology_api(openrgb_manager=None, ambilight_service=None) -> None:
    global _openrgb_manager, _ambilight_service
    if openrgb_manager:
        _openrgb_manager = openrgb_manager
    if ambilight_service:
        _ambilight_service = ambilight_service
    _ensure_config_exists()
    config         = _load_topologies()
    topology_count = len(config.get("topologies", {}))
    print(f"[TopologyAPI] Initialized ({topology_count} device topologies configured)")


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
                "zone_count":   topo.get("zone_count", 0),
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
            zones         = topo.get("zones", [])
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

        openrgb_zones = []
        for zone_idx, zone in enumerate(device.zones):
            if hasattr(zone, "segments") and len(zone.segments) > 0:
                for seg_idx, segment in enumerate(zone.segments):
                    openrgb_zones.append({
                        "zone_index": seg_idx,
                        "name":       segment.name if hasattr(segment, "name") else f"Segment {seg_idx}",
                        "led_count":  getattr(segment, "leds_count", len(getattr(segment, "leds", [])))
                    })
            else:
                openrgb_zones.append({
                    "zone_index": zone_idx,
                    "name":       zone.name,
                    "led_count":  len(zone.leds),
                })

        config        = _load_topologies()
        topologies    = config.get("topologies", {})
        existing_zones = topologies.get(device_id, {}).get("zones", [])

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
            for zone in result.get("zones", []):
                z = zone.copy()
                z["device_id"] = dev["device_id"]
                all_zones.append(z)
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
    try:
        from openrgb.utils import RGBColor
        for ctrl in _openrgb_manager.devices:
            if _openrgb_manager._make_device_key(ctrl) == device_id:
                n  = ctrl.topology.led_count
                on = [RGBColor(255, 255, 255)] * n
                of = [RGBColor(0, 0, 0)] * n
                import time
                ctrl.topology.device.set_colors(on)
                time.sleep(0.15)
                ctrl.topology.device.set_colors(of)
                time.sleep(0.10)
                ctrl.topology.device.set_colors(on)
                time.sleep(0.15)
                ctrl.topology.device.set_colors(of)
                return {"success": True}
        return {"success": False, "error": f"Device not found: {device_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
            from openrgb.utils import RGBColor
        except ImportError:
            stop_event.wait(0.05)
            continue

        for ctrl, entries in by_device.items():
            colors = [RGBColor(0, 0, 0)] * ctrl.topology.led_count
            for _, hw_idx, ring_idx, is_center in entries:
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
def test_topology_calibration(effect_center: dict, ring_spacing: float,
                              blink_config: dict = None) -> dict:
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
        from effects.openrgb_manager import TopologyType
        from effects.ambilight_service import build_device_zones, _led_world_positions

        # Collect all linear LED world positions
        device_leds = []
        for ctrl in _openrgb_manager.devices:
            if ctrl.topology.topology_type != TopologyType.LINEAR:
                continue
            device_key   = _openrgb_manager._make_device_key(ctrl)
            zones, _     = build_device_zones(device_key)
            if not zones:
                continue
            topo_data  = _load_topologies().get("topologies", {}).get(device_key, {})
            zone_defs  = {z["zone_index"]: z for z in topo_data.get("zones", [])}
            off        = 0
            for z_def in sorted(topo_data.get("zones", []), key=lambda z: z["zone_index"]):
                pts = _led_world_positions(z_def)
                for local_idx, (wx, wy) in enumerate(pts):
                    device_leds.append((ctrl, off + local_idx, wx, wy))
                off += len(pts)

        if not device_leds:
            return {"success": False, "error": "No linear topology devices found"}

        min_x = min(p[2] for p in device_leds)
        max_x = max(p[2] for p in device_leds)
        min_y = min(p[3] for p in device_leds)
        max_y = max(p[3] for p in device_leds)

        cx      = min_x + (max_x - min_x) * (effect_center.get("x", 50) / 100.0)
        cy      = min_y + (max_y - min_y) * (effect_center.get("y", 50) / 100.0)
        spacing = max(0.01, float(ring_spacing))

        # Find center LED
        min_dist   = float("inf")
        center_key = None
        for ctrl, hw_idx, wx, wy in device_leds:
            d = math.hypot(wx - cx, wy - cy)
            if d < min_dist:
                min_dist   = d
                center_key = (ctrl, hw_idx)

        led_data = []
        for ctrl, hw_idx, wx, wy in device_leds:
            dist     = math.hypot(wx - cx, wy - cy)
            ring_idx = int(dist / spacing)
            is_ctr   = (ctrl, hw_idx) == center_key
            led_data.append((ctrl, hw_idx, ring_idx, is_ctr))

        write_lock = _openrgb_manager._lock if _openrgb_manager is not None else None
        _calib_stop  = threading.Event()
        _calib_thread = threading.Thread(
            target=_calibration_loop,
            args=(led_data, _calib_stop, blink_config, write_lock),
            daemon=True, name="TopologyCalibration",
        )
        _calib_thread.start()
        return {"success": True, "leds_colored": len(device_leds)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@eel.expose
def stop_topology_calibration() -> dict:
    global _calib_thread, _calib_stop
    _calib_stop.set()
    if _calib_thread and _calib_thread.is_alive():
        _calib_thread.join(timeout=0.5)
    _calib_thread = None
    # Turn off all LEDs
    if _openrgb_manager:
        try:
            from openrgb.utils import RGBColor
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
