"""Keyboards are ordinary devices now: the user chooses in Devices whether to use one."""
import sys
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from effects.openrgb_manager import OpenRGBManager, TopologyType  # noqa: E402


def _dev(name, kind, n_leds):
    return N(name=name, type=N(name=kind), leds=[object()] * n_leds, zones=[])


class _Client:
    def __init__(self, devices):
        self.devices = devices


def test_keyboard_is_enrolled_as_linear():
    mgr = OpenRGBManager(_Client([_dev("Corsair K70", "KEYBOARD", 104)]))
    assert len(mgr.devices) == 1
    assert mgr.devices[0].topology.topology_type == TopologyType.LINEAR
    assert mgr.devices[0].device_key == "Corsair K70::linear"


def test_every_device_is_enrolled_whatever_its_type():
    mgr = OpenRGBManager(_Client([
        _dev("Strip", "LEDSTRIP", 38),
        _dev("Corsair K70", "KEYBOARD", 104),
        _dev("Logo", "MOTHERBOARD", 1),
    ]))
    kinds = {c.topology.device.name: c.topology.topology_type for c in mgr.devices}
    assert kinds == {"Strip": TopologyType.LINEAR,
                     "Corsair K70": TopologyType.LINEAR,
                     "Logo": TopologyType.SINGLE}


def test_device_list_carries_zones_and_their_state(monkeypatch):
    from api import ambilight_api
    import effects.ambilight_service as svc

    mgr = OpenRGBManager(_Client([_dev("Corsair K70", "KEYBOARD", 104)]))
    key = mgr.devices[0].device_key
    zones = [{"zone_index": 0, "name": "Keyboard", "edge": "area"},
             {"zone_index": 1, "name": "Logo", "edge": "area"}]
    monkeypatch.setattr(svc, "build_device_zones", lambda k: (zones, 104))
    monkeypatch.setattr(ambilight_api, "_openrgb_manager", mgr)
    monkeypatch.setattr(ambilight_api, "_ambilight_service", N(get_config=lambda: {
        "devices": {key: {"enabled": True, "zones_enabled": {"1": False}}}}))

    (dev,) = ambilight_api.get_ambilight_devices()
    assert dev["device_type"] == "keyboard"
    assert dev["enabled"] is True
    assert dev["zone_count"] == 2 and dev["zones_active"] == 1
    assert [(z["name"], z["enabled"]) for z in dev["zones"]] == [("Keyboard", True), ("Logo", False)]
