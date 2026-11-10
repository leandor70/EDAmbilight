"""Screen rectangle: where a LED is drawn decides what it reads, not the zone name."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from effects import ambilight_service as svc      # noqa: E402

RECT = {"x_min": 0, "x_max": 10, "y_min": 0, "y_max": 6}   # editor coordinates, y up


def zone(name, idx, x, y, rot, n):
    return {"name": name, "zone_index": idx, "led_count": n,
            "position": {"x": x, "y": y}, "rotation": rot}


def frame_zones(names=("zona_a", "zona_b", "zona_c", "zona_d")):
    a, b, c, d = names
    return [
        zone(a, 0, 0, 6, 0, 11),      # top, left -> right
        zone(b, 1, 10, 6, 270, 7),    # right, top -> bottom
        zone(c, 2, 10, 0, 180, 11),   # bottom, right -> left
        zone(d, 3, 0, 0, 90, 7),      # left, bottom -> top
    ]


@pytest.fixture
def topo(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    monkeypatch.chdir(tmp_path)

    def write(zones, rect=None, extra=None):
        data = {"topologies": {"Strip::linear": {"zones": zones}}}
        data["topologies"].update(extra or {})
        if rect:
            data["screen_rect"] = rect
        (tmp_path / "config" / "device_topologies.json").write_text(json.dumps(data))
        return data
    return write


def by_name(entries):
    out = {}
    for e in entries:
        out.setdefault(e["name"], []).append(e)
    return out


def test_any_name_works_once_the_rectangle_is_there(topo):
    topo(frame_zones(), RECT)
    zones = by_name(svc.build_device_zones("Strip::linear")[0])
    assert [(e["edge"], e["reversed"]) for e in zones["zona_a"]] == [("top", False)]
    assert [(e["edge"], e["reversed"]) for e in zones["zona_b"]] == [("right", False)]
    assert [(e["edge"], e["reversed"]) for e in zones["zona_c"]] == [("bottom", True)]
    assert [(e["edge"], e["reversed"]) for e in zones["zona_d"]] == [("left", True)]
    top = zones["zona_a"][0]
    assert (top["led_start"], top["led_end"]) == (0, 11)
    assert top["screen_start"] == 0.0 and top["screen_end"] == 1.0


def test_names_in_other_languages_do_not_matter(topo):
    topo(frame_zones(("alto", "destra", "basso", "sinistra")), RECT)
    edges = {n: e[0]["edge"] for n, e in by_name(svc.build_device_zones("Strip::linear")[0]).items()}
    assert edges == {"alto": "top", "destra": "right", "basso": "bottom", "sinistra": "left"}


def test_inside_reads_its_point_and_outside_stays_off(topo):
    topo(frame_zones() + [zone("Logo", 4, 5, 3, 0, 1), zone("Far", 5, 30, 3, 0, 1)], RECT)
    zones = by_name(svc.build_device_zones("Strip::linear")[0])
    (logo,) = zones["Logo"]
    assert logo["edge"] == "area" and (logo["x_pct"], logo["y_pct"]) == (0.5, 0.5)
    assert [e["edge"] for e in zones["Far"]] == ["off"]


def test_a_zone_longer_than_the_screen_lights_only_the_part_on_the_side(topo):
    topo([zone("long", 0, -10, 0, 0, 31)], RECT)       # x -10..20 along the bottom
    runs = [(e["edge"], e["led_start"], e["led_end"]) for e in svc.build_device_zones("Strip::linear")[0]]
    assert runs == [("off", 0, 9), ("bottom", 9, 22), ("off", 22, 31)]


def test_corner_leds_follow_the_direction_of_their_strip(topo):
    topo(frame_zones(), RECT)
    zones = by_name(svc.build_device_zones("Strip::linear")[0])
    # LED 0 of the top strip sits on the top-left corner: it stays with the top side
    assert len(zones["zona_a"]) == 1 and zones["zona_a"][0]["edge"] == "top"
    assert len(zones["zona_d"]) == 1 and zones["zona_d"][0]["edge"] == "left"


def test_without_rectangle_old_names_keep_the_old_mapping(topo):
    data = topo(frame_zones(("MonitorTop", "MonitorRight", "MonitorBottom", "MonitorLeft")))
    assert svc.screen_frame(data)[0] == "names"
    old = svc.build_device_zones("Strip::linear")[0]

    rect = svc.suggest_screen_rect(data)
    topo(frame_zones(("MonitorTop", "MonitorRight", "MonitorBottom", "MonitorLeft")), rect)
    new = svc.build_device_zones("Strip::linear")[0]

    keys = ("name", "edge", "led_start", "led_end", "reversed")
    assert [tuple(e[k] for k in keys) for e in new] == [tuple(e[k] for k in keys) for e in old]
    for a, b in zip(old, new):
        assert a["screen_start"] == pytest.approx(b["screen_start"], abs=1e-6)
        assert a["screen_end"] == pytest.approx(b["screen_end"], abs=1e-6)


def test_modes(topo):
    assert svc.screen_frame(topo(frame_zones(), RECT))[0] == "manual"
    assert svc.screen_frame(topo(frame_zones()))[0] == "auto"
    assert svc.screen_frame(topo(frame_zones(), {"x_min": 1, "x_max": 1, "y_min": 0, "y_max": 2}))[0] == "auto"


def test_summary_lists_each_zone_once():
    entries = [
        {"name": "a", "zone_index": 0, "edge": "top"},
        {"name": "a", "zone_index": 0, "edge": "right"},
        {"name": "b", "zone_index": 1, "edge": "off"},
    ]
    s = {z["name"]: z for z in svc.summarize_zones(entries)}
    assert s["a"]["edge"] == "top+right" and not s["a"]["outside"]
    assert s["b"]["edge"] == "off" and s["b"]["outside"]


def test_api_saves_and_clears_the_rectangle(tmp_path, monkeypatch):
    from api import topology_api
    f = tmp_path / "device_topologies.json"
    f.write_text(json.dumps({"version": 1, "topologies": {"Strip::linear": {"zones": frame_zones()}}}))
    monkeypatch.setattr(topology_api, "TOPOLOGY_CONFIG_FILE", f)
    monkeypatch.setattr(topology_api, "_ambilight_service", None)

    assert topology_api.get_screen_rect()["mode"] == "auto"
    assert topology_api.set_screen_rect(RECT) == {"success": True}
    got = topology_api.get_screen_rect()
    assert got["mode"] == "manual" and got["rect"] == {k: float(v) for k, v in RECT.items()}
    assert not topology_api.set_screen_rect({"x_min": 2, "x_max": 1, "y_min": 0, "y_max": 1})["success"]
    assert topology_api.set_screen_rect(None) == {"success": True}
    assert "screen_rect" not in json.loads(f.read_text())


# ── Proportions of the real screen ────────────────────────────────────────────

def test_fit_aspect_only_grows_around_the_centre():
    assert svc.fit_aspect((0, 10, 0, 10), 2.0) == (-5.0, 15.0, 0, 10)       # too narrow: wider
    assert svc.fit_aspect((0, 40, 0, 10), 2.0) == (0, 40, -5.0, 15.0)       # too flat: taller
    assert svc.fit_aspect((0, 20, 0, 10), 2.0) == (0, 20, -0.0, 10.0)
    assert svc.fit_aspect((0, 10, 0, 10), None) == (0, 10, 0, 10)


def test_automatic_rectangle_takes_the_screen_proportions(topo):
    data = topo(frame_zones())                        # no names, no rectangle: auto
    x0, x1, y0, y1 = svc.screen_frame(data, aspect=21 / 9)[1]
    assert (x1 - x0) / (y1 - y0) == pytest.approx(21 / 9)
    assert (x0, x1) == pytest.approx((0 - 2, 10 + 2))   # 6 high -> 14 wide, 2 more each side


def test_suggested_rectangle_takes_the_screen_proportions(topo):
    data = topo(frame_zones(("MonitorTop", "MonitorRight", "MonitorBottom", "MonitorLeft")))
    r = svc.suggest_screen_rect(data, aspect=16 / 9)
    assert (r["x_max"] - r["x_min"]) / (r["y_max"] - r["y_min"]) == pytest.approx(16 / 9)


def test_screen_size_comes_from_the_capture_first(monkeypatch):
    from types import SimpleNamespace as N
    from api import topology_api
    monkeypatch.setattr(topology_api, "_ambilight_service", N(frame_size=(3440, 1440)))
    assert topology_api.screen_size() == (3440, 1440)
