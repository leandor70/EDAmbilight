"""LED order and screen position follow the topology (editor: y points UP).

Layout below is the real desk strip: Desktop under the monitor, MonitorRight
going UP from the bottom, MonitorTop right->left, MonitorLeft going DOWN from
the top. The check is on what each LED receives.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from effects.ambilight_service import AmbilightService, build_device_zones  # noqa: E402

KEY = "Strip::linear"
W, H = 400, 200

ZONES = [
    {"zone_index": 0, "name": "Desktop", "led_count": 16, "led_spacing": 7.5,
     "position": {"x": -54, "y": -11}, "rotation": 0},
    {"zone_index": 1, "name": "MonitorRight", "led_count": 5, "led_spacing": 7,
     "position": {"x": 66, "y": -7}, "rotation": 90},
    {"zone_index": 2, "name": "MonitorTop", "led_count": 12, "led_spacing": 6.667,
     "position": {"x": 67, "y": 29}, "rotation": 180},
    {"zone_index": 3, "name": "MonitorLeft", "led_count": 5, "led_spacing": 7,
     "position": {"x": -12, "y": 27}, "rotation": 270},
    # not on the monitor frame: one high (y=25), one low (y=-10) in the editor
    {"zone_index": 4, "name": "CPU", "led_count": 1, "led_spacing": 1,
     "position": {"x": 30, "y": 25}, "rotation": 0},
    {"zone_index": 5, "name": "Case", "led_count": 1, "led_spacing": 1,
     "position": {"x": 30, "y": -10}, "rotation": 0},
]
OFFSET = {"Desktop": 0, "MonitorRight": 16, "MonitorTop": 21, "MonitorLeft": 33}


class _Manager:
    def __init__(self):
        self.colors = None

    def get_device_led_count(self, key):
        return 38

    def apply_direct_colors(self, key, colors):
        self.colors = list(colors)


def _service(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("config").mkdir()
    Path("config/device_topologies.json").write_text(
        json.dumps({"topologies": {KEY: {"zones": ZONES}}}))
    mgr = _Manager()
    svc = AmbilightService(mgr)
    svc._config = {
        "enabled": True, "strategy": "mean", "depth": 10,
        "saturation_boost": 1.0, "min_luminance": 0, "black_bar_detect": False,
        "devices": {KEY: {"enabled": True}},
    }
    return svc, mgr


def _run(svc, mgr, frame):
    svc._process_frame(frame, svc._config)
    return mgr.colors


def _is(color, name):
    r, g, b = color
    if name == "red":
        return r > 200 and b < 60
    if name == "blue":
        return b > 200 and r < 60
    if name == "green":
        return g > 200 and r < 60 and b < 60
    if name == "white":
        return min(color) > 200
    raise ValueError(name)


def test_right_and_left_follow_physical_order(tmp_path, monkeypatch):
    svc, mgr = _service(tmp_path, monkeypatch)
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[: H // 2, :, 2] = 255        # top half red   (BGR channel 2)
    frame[H // 2:, :, 0] = 255         # bottom half blue
    c = _run(svc, mgr, frame)

    r = OFFSET["MonitorRight"]         # LED 0 is at the BOTTOM, LED 4 at the TOP
    assert _is(c[r + 0], "blue") and _is(c[r + 1], "blue")
    assert _is(c[r + 3], "red") and _is(c[r + 4], "red")

    l = OFFSET["MonitorLeft"]          # LED 0 is at the TOP, LED 4 at the BOTTOM
    assert _is(c[l + 0], "red") and _is(c[l + 1], "red")
    assert _is(c[l + 3], "blue") and _is(c[l + 4], "blue")


def test_top_and_bottom_follow_physical_order(tmp_path, monkeypatch):
    svc, mgr = _service(tmp_path, monkeypatch)
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:, : W // 2, 1] = 255                        # left half green
    frame[:, W // 2:, :] = 255                         # right half white
    c = _run(svc, mgr, frame)

    t = OFFSET["MonitorTop"]           # LED 0 is at the RIGHT, last LED at the LEFT
    assert _is(c[t + 0], "white") and _is(c[t + 11], "green")

    zones = {z["name"]: z for z in build_device_zones(KEY)[0]}
    d = zones["Desktop"]               # LED 0 on the left: first lit LED = leftmost
    first = d["led_offset"] + d["led_start"]
    last = d["led_offset"] + d["led_end"] - 1
    assert _is(c[first], "green") and _is(c[last], "white")


def test_reversed_flags_come_from_geometry():
    zones = {z["name"]: z for z in build_device_zones_from(ZONES)}
    assert zones["Desktop"]["reversed"] is False       # left -> right
    assert zones["MonitorTop"]["reversed"] is True     # right -> left
    assert zones["MonitorRight"]["reversed"] is True   # bottom -> top
    assert zones["MonitorLeft"]["reversed"] is False   # top -> bottom


def test_area_zone_high_in_editor_is_high_on_screen(tmp_path, monkeypatch):
    _service(tmp_path, monkeypatch)
    zones = {z["name"]: z for z in build_device_zones(KEY)[0]}
    assert zones["CPU"]["y_pct"] < zones["Case"]["y_pct"]   # 0 = top of the screen
    assert zones["CPU"]["y_pct"] < 0.2 and zones["Case"]["y_pct"] > 0.8


def build_device_zones_from(zones):
    """build_device_zones for an in-memory topology (temp dir, restored after)."""
    import os
    import tempfile
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            Path("config").mkdir()
            Path("config/device_topologies.json").write_text(
                json.dumps({"topologies": {KEY: {"zones": zones}}}))
            return build_device_zones(KEY)[0]
        finally:
            os.chdir(old)
