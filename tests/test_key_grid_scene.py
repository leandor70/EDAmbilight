"""Key grids (keyboards) are not placed in the Topology Editor: they read the whole screen."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import topology_api as api                                  # noqa: E402
from effects import ambilight_service as svc                         # noqa: E402
from effects.openrgb_manager import DeviceController, TopologyType   # noqa: E402

KB, STRIP = "Keys::linear", "Strip::linear"


def _zone(dev, idx, name, count, x=0, y=0, rot=0):
    return {"zone_index": idx, "name": name, "led_count": count, "device_id": dev,
            "position": {"x": x, "y": y}, "rotation": rot}


KB_ZONES = [_zone(KB, 0, "Keyboard", 6, x=-50, y=-40), _zone(KB, 1, "Logo", 1, x=5, y=3)]
STRIP_ZONES = [_zone(STRIP, 0, "a", 11, 0, 6), _zone(STRIP, 1, "b", 11, 10, 0, 180)]


def _ctrl(key, zones):
    dev = N(name=key.split("::")[0], type=N(name="KEYBOARD"), leds=[0] * sum(z["led_count"] for z in zones),
            zones=[N(name=z["name"], leds=[0] * z["led_count"], segments=[]) for z in zones])
    c = DeviceController(dev, TopologyType.LINEAR)
    c.device_key = key
    return c


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, "TOPOLOGY_CONFIG_FILE", Path("config/device_topologies.json"))
    api.TOPOLOGY_CONFIG_FILE.parent.mkdir()
    api.TOPOLOGY_CONFIG_FILE.write_text(json.dumps({"version": 1, "topologies": {
        KB: {"device_id": KB, "zones": KB_ZONES}, STRIP: {"device_id": STRIP, "zones": STRIP_ZONES}}}))
    layouts = {KB: {0: {"rows": 2, "cols": 3, "cells": [(r, c, r * 3 + c) for r in range(2) for c in range(3)]}}}
    mgr = N(devices=[_ctrl(KB, KB_ZONES), _ctrl(STRIP, STRIP_ZONES)],
            _make_device_key=lambda c: c.device_key,
            matrix_layouts=lambda key: layouts.get(key, {}))
    api.init_topology_api(mgr)
    return mgr


def _stored(key):
    return json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())["topologies"][key]


def test_scene_leaves_out_the_key_grid(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    scene = api.get_scene_topology()
    assert sorted((z["device_id"], z["name"]) for z in scene["zones"]) == [
        (KB, "Logo"), (STRIP, "a"), (STRIP, "b")]


def test_a_device_made_only_of_a_key_grid_is_not_listed(tmp_path, monkeypatch):
    mgr = _setup(tmp_path, monkeypatch)
    only = {KB: {0: {"rows": 2, "cols": 3, "cells": []}, 1: {"rows": 2, "cols": 2, "cells": []}}}
    mgr.matrix_layouts = lambda key: only.get(key, {})
    scene = api.get_scene_topology()
    assert KB not in [d["device_id"] for d in scene["devices"]]


def test_saving_the_editor_keeps_the_key_grid_in_the_file(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    zones = api.get_scene_topology()["zones"]
    assert api.save_scene_topology(zones, {"x": 50, "y": 50})["success"]
    saved = _stored(KB)
    assert [z["name"] for z in saved["zones"]] == ["Keyboard", "Logo"]
    assert saved["total_leds"] == 7


def test_reload_does_not_bring_the_key_grid_back(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    res = api.reload_scene_from_openrgb()
    assert "Keyboard" not in [z["name"] for z in res["zones"]]


def test_key_grid_is_out_of_the_automatic_screen_box(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    data = json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())
    with_kb = svc.screen_frame(data)[1]
    without = svc.screen_frame(data, api.key_grid_zone_ids())[1]
    assert with_kb[0] == -50                        # the keyboard row would stretch the screen
    assert without == (0.0, 10.0, -6.0, 0.0)        # only the strip and the logo count
    monkeypatch.setattr(api, "screen_size", lambda: None)       # proportions not known here
    assert api.get_screen_rect()["suggested"] == {"x_min": 0.0, "x_max": 10.0, "y_min": 0.0, "y_max": 6.0}
