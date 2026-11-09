"""A keyboard (matrix zone): every key reads its own cell of the screen."""
import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace as N

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import openrgb_sdk as sdk                                   # noqa: E402
from effects import ambilight_service as svc                          # noqa: E402
from effects.openrgb_manager import OpenRGBManager                    # noqa: E402

NO = sdk.NO_LED


def _s(text):
    raw = text.encode() + b"\x00"
    return struct.pack("<H", len(raw)) + raw


def test_sdk_keeps_the_key_map():
    grid = [[0, 1, NO], [2, 3, NO]]
    body = _s("Keyboard") + struct.pack("<iIII", 2, 4, 4, 4)
    body += struct.pack("<H", 8 + 4 * 6) + struct.pack("<II", 2, 3)
    body += b"".join(struct.pack("<I", v) for row in grid for v in row)
    body += struct.pack("<H", 0)                       # protocol 4: no segments
    zone = sdk._read_zone(sdk._Reader(body), 4)
    assert zone.matrix == (2, 3)
    assert zone.matrix_map == grid


def _device(zones):
    leds = [object()] * sum(len(z.leds) for z in zones)
    return N(name="Keys", type=N(name="KEYBOARD"), leds=leds, zones=zones)


def _zone(n_leds, grid=None, segments=()):
    return N(leds=[object()] * n_leds, matrix_map=grid, segments=list(segments))


def test_manager_lists_key_grids_with_topology_zone_indexes():
    grid = [[0, 1, NO], [2, NO, NO]]
    dev = _device([_zone(3), _zone(3, grid)])
    mgr = OpenRGBManager(N(devices=[dev]))
    key = mgr.devices[0].device_key
    assert mgr.matrix_layouts(key) == {1: {"rows": 2, "cols": 3, "cells": [(0, 0, 0), (0, 1, 1), (1, 0, 2)]}}
    assert mgr.matrix_layouts("nothing") == {}


def test_a_zone_with_segments_counts_each_segment_in_the_index():
    grid = [[0, 1], [2, 3]]
    dev = _device([_zone(4, None, segments=[object(), object()]), _zone(4, grid)])
    mgr = OpenRGBManager(N(devices=[dev]))
    layouts = mgr.matrix_layouts(mgr.devices[0].device_key)
    assert list(layouts) == [2]


def test_sample_grid_averages_each_cell():
    frame = np.zeros((40, 60, 3), dtype=np.uint8)
    frame[:, :30] = (200, 0, 0)       # left half red
    frame[:, 30:] = (0, 0, 100)       # right half blue
    grid = svc._sample_grid(frame, 2, 3)
    assert grid.shape == (2, 3, 3)
    assert tuple(grid[0, 0].round()) == (200, 0, 0)
    assert tuple(grid[1, 2].round()) == (0, 0, 100)


def test_build_device_zones_turns_a_key_grid_into_a_matrix_zone(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    topo = {"topologies": {"Keys::linear": {"zones": [{
        "zone_index": 0, "name": "Keyboard", "led_count": 4,
        "position": {"x": 0, "y": 0}, "rotation": 0}]}}}
    (tmp_path / "config" / "device_topologies.json").write_text(json.dumps(topo))
    monkeypatch.chdir(tmp_path)
    layouts = {0: {"rows": 2, "cols": 2, "cells": [(0, 0, 0), (0, 1, 1), (1, 0, 2), (1, 1, 3)]}}

    plain, _ = svc.build_device_zones("Keys::linear")
    assert [z["edge"] for z in plain] == ["area"]

    zones, total = svc.build_device_zones("Keys::linear", layouts)
    assert total == 4
    (z,) = zones
    assert z["edge"] == "matrix" and (z["rows"], z["cols"]) == (2, 2)
    assert z["cells"] == [(0, 0, 0), (0, 1, 1), (1, 0, 2), (1, 1, 3)]
