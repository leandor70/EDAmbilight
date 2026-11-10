"""Zones that OpenRGB names '???' are LEDs that do not exist: excluded from everything
(not in the Topology Editor, not driven) but kept in the config, so LED offsets hold."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import topology_api as api                                  # noqa: E402
from effects import ambilight_service as svc                         # noqa: E402
from effects.openrgb_manager import DeviceController, TopologyType   # noqa: E402

KEY = "Board::linear"


def _zone(idx, name, count=1):
    return {"zone_index": idx, "name": name, "led_count": count, "device_id": KEY,
            "position": {"x": idx, "y": 0}, "rotation": 0}


STORED = [_zone(0, "CPU"), _zone(1, "???"), _zone(2, "Logo"), _zone(3, "???", 4), _zone(4, "Case")]


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, "TOPOLOGY_CONFIG_FILE", Path("config/device_topologies.json"))
    api.TOPOLOGY_CONFIG_FILE.parent.mkdir()
    api.TOPOLOGY_CONFIG_FILE.write_text(json.dumps(
        {"version": 1, "topologies": {KEY: {"device_id": KEY, "zones": STORED}}}))

    dev = N(name="Board", type=N(name="MOTHERBOARD"), leds=[0] * 8,
            zones=[N(name=z["name"], leds=[0] * z["led_count"], segments=[]) for z in STORED])
    ctrl = DeviceController(dev, TopologyType.LINEAR)
    ctrl.device_key = KEY
    mgr = N(devices=[ctrl], _make_device_key=lambda c: c.device_key)
    api.init_topology_api(mgr)


def _stored():
    return json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())["topologies"][KEY]


def test_phantom_zone_detection():
    assert svc.is_phantom_zone({"name": "???"}) and svc.is_phantom_zone({"name": " ? "})
    assert svc.is_phantom_zone({"name": ""})
    assert not svc.is_phantom_zone({"name": "CPU?"}) and not svc.is_phantom_zone({"name": "Zone 1"})


def test_scene_hides_phantom_zones(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    scene = api.get_scene_topology()
    assert [z["name"] for z in scene["zones"]] == ["CPU", "Logo", "Case"]
    assert scene["devices"][0]["zone_count"] == 3
    assert api.get_topology_devices()["devices"][0]["zone_count"] == 3


def test_save_keeps_phantom_zones_and_offsets(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    visible = api.get_scene_topology()["zones"]
    visible[0]["position"] = {"x": 50, "y": 60}          # the user moves CPU
    assert api.save_scene_topology(visible, {"x": 50, "y": 50})["success"]

    saved = _stored()
    assert [z["zone_index"] for z in saved["zones"]] == [0, 1, 2, 3, 4]
    assert [z["name"] for z in saved["zones"]] == ["CPU", "???", "Logo", "???", "Case"]
    assert saved["zones"][0]["position"] == {"x": 50, "y": 60}
    assert saved["total_leds"] == 8                      # phantom LEDs still counted
    assert saved["zone_count"] == 5


def test_reload_does_not_show_phantom_zones(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    res = api.reload_scene_from_openrgb()
    assert [z["name"] for z in res["zones"]] == ["CPU", "Logo", "Case"]
    assert len(_stored()["zones"]) == 5                   # config still complete


def test_phantom_zones_are_out_of_the_automatic_screen(tmp_path, monkeypatch):
    far = [_zone(0, "CPU"), {**_zone(1, "???"), "position": {"x": 500, "y": 0}}]
    data = {"topologies": {KEY: {"zones": far}}}
    x0, x1, _, _ = svc.screen_frame(data)[1]
    assert x1 < 100                                       # the '???' zone at x=500 is ignored
