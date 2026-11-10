"""LEDs the ambilight does not use are left free: never written (only once in black
when they stop being used), so OpenRGB or another program can colour them."""
import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace as N

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from effects.ambilight_service import AmbilightService                 # noqa: E402
from effects.openrgb_manager import OpenRGBManager                     # noqa: E402
from test_openrgb_sdk import server, _wait                             # noqa: E402,F401
from core import openrgb_sdk as sdk                                    # noqa: E402


# ── OpenRGB packets ───────────────────────────────────────────────────────────

def test_zone_update_packet(server):                                   # noqa: F811
    with sdk.OpenRGBClient("127.0.0.1", server.port) as client:
        client.devices[0].set_zone_colors(1, [(1, 2, 3)] * 4)
        assert _wait(lambda: server.commands(1051))
    _, payload = server.commands(1051)[0]
    size, zone, count = struct.unpack_from("<IiH", payload)
    assert size == len(payload) == 4 + 4 + 2 + 4 * 4 and zone == 1 and count == 4
    assert payload[10:14] == bytes((1, 2, 3, 0))


def test_single_led_packet(server):                                    # noqa: F811
    with sdk.OpenRGBClient("127.0.0.1", server.port) as client:
        client.devices[0].set_led_color(5, (9, 8, 7))
        assert _wait(lambda: server.commands(1052))
    _, payload = server.commands(1052)[0]
    assert payload == struct.pack("<i", 5) + bytes((9, 8, 7, 0))


# ── Manager: write only what is asked ────────────────────────────────────────

class _Dev:
    def __init__(self, sizes, names=None):
        names = names or ["z%d" % i for i in range(len(sizes))]
        self.zones = [N(leds=[0] * n, name=nm) for n, nm in zip(sizes, names)]
        self.leds = [0] * sum(sizes)
        self.name, self.type, self._direct_mode_set = "D", N(name="LEDSTRIP"), True
        self.calls = []

    def set_colors(self, colors):           self.calls.append(("all", len(colors)))
    def set_zone_colors(self, zone, colors): self.calls.append(("zone", zone, len(colors)))
    def set_led_color(self, i, color):      self.calls.append(("led", i))


def _mgr(dev):
    m = OpenRGBManager(N(devices=[]))
    m.devices = [N(topology=N(device=dev), device_key="D")]
    m._make_device_key = lambda c: c.device_key
    return m


def test_everything_used_is_one_packet():
    dev = _Dev([3, 4])
    _mgr(dev).apply_direct_colors("D", [(0, 0, 0)] * 7, [True] * 7)
    _mgr(dev).apply_direct_colors("D", [(0, 0, 0)] * 7)
    assert dev.calls == [("all", 7), ("all", 7)]


def test_a_zone_used_in_part_is_written_whole_a_free_zone_not_at_all():
    dev = _Dev([3, 4, 3])
    mask = [True] * 3 + [False] * 4 + [False, True, True]
    _mgr(dev).apply_direct_colors("D", [(0, 0, 0)] * 10, mask)
    assert dev.calls == [("zone", 0, 3), ("zone", 2, 3)]


def test_every_zone_touched_is_one_packet():
    dev = _Dev([3, 4])
    mask = [True, False, False] + [False, False, False, True]   # both zones used in part
    _mgr(dev).apply_direct_colors("D", [(0, 0, 0)] * 7, mask)
    assert dev.calls == [("all", 7)]


def test_phantom_zones_do_not_split_the_packet():
    dev = _Dev([1, 2, 1], names=["CPU", "???", "Logo"])
    mask = [True, False, False, True]                           # the ??? LEDs are never used
    _mgr(dev).apply_direct_colors("D", [(0, 0, 0)] * 4, mask)
    assert dev.calls == [("all", 4)]


def test_nothing_used_writes_nothing():
    dev = _Dev([3])
    _mgr(dev).apply_direct_colors("D", [(0, 0, 0)] * 3, [False] * 3)
    assert dev.calls == []


# ── Service: LEDs outside the screen are never written ──────────────────────

KEY = "Strip::linear"
RECT = {"x_min": 0, "x_max": 10, "y_min": 0, "y_max": 6}


class _Rec:
    def __init__(self):
        self.writes = []

    def get_device_led_count(self, key):
        return 31

    def apply_direct_colors(self, key, colors, mask=None):
        self.writes.append((list(colors), None if mask is None else [bool(m) for m in mask]))


def _service(tmp_path, monkeypatch, x):
    monkeypatch.chdir(tmp_path)
    Path("config").mkdir(exist_ok=True)
    zone = {"zone_index": 0, "name": "long", "led_count": 31,
            "position": {"x": x, "y": 0}, "rotation": 0}
    Path("config/device_topologies.json").write_text(
        json.dumps({"topologies": {KEY: {"zones": [zone]}}, "screen_rect": RECT}))
    return zone


def test_outside_leds_are_not_written_and_freed_ones_get_black_once(tmp_path, monkeypatch):
    _service(tmp_path, monkeypatch, -10)              # x -10..20: LEDs 10..20 on the bottom side
    mgr = _Rec()
    svc = AmbilightService(mgr)
    svc._config = {"enabled": True, "strategy": "mean", "depth": 10, "saturation_boost": 1.0,
                   "min_luminance": 0, "black_bar_detect": False, "devices": {KEY: {"enabled": True}}}
    frame = np.full((60, 100, 3), 200, dtype=np.uint8)
    svc._process_frame(frame, svc._config)
    _, mask = mgr.writes[-1]
    assert [i for i, m in enumerate(mask) if m] == list(range(10, 21))

    # the zone moves right: LEDs 11..20 leave the screen -> written once (black), then free
    _service(tmp_path, monkeypatch, 0)               # x 0..30: LEDs 0..10 on the side
    svc.refresh_zones(KEY)
    svc._process_frame(frame, svc._config)
    colors, mask = mgr.writes[-1]
    used = set(range(0, 11))
    assert [i for i, m in enumerate(mask) if m] == list(range(0, 21))
    assert all(colors[i] == (0, 0, 0) for i in range(11, 21))
    svc._process_frame(frame, svc._config)
    _, mask = mgr.writes[-1]
    assert {i for i, m in enumerate(mask) if m} == used
