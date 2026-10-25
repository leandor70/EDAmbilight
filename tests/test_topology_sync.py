"""Startup sync of device_topologies.json with the hardware (hardware wins)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import topology_api as api                      # noqa: E402
from effects.openrgb_manager import DeviceController, TopologyType  # noqa: E402


def _device(name, zones):
    """zones: list of (zone name, led count)."""
    return N(
        name=name,
        type=N(name="LEDSTRIP"),
        leds=[0] * sum(n for _, n in zones),
        zones=[N(name=zn, leds=[0] * n, segments=[]) for zn, n in zones],
    )


class _Manager:
    def __init__(self, *devices):
        self.devices = []
        for dev, topo in devices:
            ctrl = DeviceController(dev, topo)
            ctrl.device_key = f"{dev.name}::{topo.value}"
            self.devices.append(ctrl)

    def _make_device_key(self, ctrl):
        return ctrl.device_key


def _zone(idx, name, count, **extra):
    return {"zone_index": idx, "name": name, "led_count": count,
            "position": {"x": 5, "y": 7}, "rotation": 90, **extra}


def _run(tmp_path, monkeypatch, topologies, *devices):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, "TOPOLOGY_CONFIG_FILE", Path("config/device_topologies.json"))
    api.TOPOLOGY_CONFIG_FILE.parent.mkdir()
    api.TOPOLOGY_CONFIG_FILE.write_text(json.dumps({"version": 1, "topologies": topologies}))
    api.init_topology_api(_Manager(*devices))
    return json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())["topologies"]


def test_new_device_is_imported(tmp_path, monkeypatch):
    topo = _run(tmp_path, monkeypatch, {},
                (_device("Strip", [("Top", 60)]), TopologyType.LINEAR))
    assert topo["Strip::linear"]["zones"][0]["led_count"] == 60


def test_differences_are_resolved_in_favour_of_hardware(tmp_path, monkeypatch):
    stale = {"Strip::linear": {"zones": [
        _zone(0, "OldName", 99, led_spacing=2.5),
        _zone(1, "Gone", 10),
    ]}}
    topo = _run(tmp_path, monkeypatch, stale,
                (_device("Strip", [("Top", 60)]), TopologyType.LINEAR))
    zones = topo["Strip::linear"]["zones"]
    assert [(z["name"], z["led_count"]) for z in zones] == [("Top", 60)]
    # layout of the surviving zone is preserved
    assert zones[0]["position"] == {"x": 5, "y": 7}
    assert zones[0]["rotation"] == 90
    assert zones[0]["led_spacing"] == 2.5


def test_matching_device_and_missing_device_are_untouched(tmp_path, monkeypatch):
    current = {
        "Strip::linear": {"marker": 1, "zones": [_zone(0, "Top", 60)]},
        "Unplugged::linear": {"zones": [_zone(0, "Z", 5)]},
    }
    topo = _run(tmp_path, monkeypatch, current,
                (_device("Strip", [("Top", 60)]), TopologyType.LINEAR))
    assert topo == current


# -- zones with segments ------------------------------------------------------

def _segmented_device(name, zones):
    """zones: list of (zone name, [(segment name, led count), ...])."""
    return N(
        name=name,
        type=N(name="LEDSTRIP"),
        leds=[0] * sum(n for _, segs in zones for _, n in segs),
        zones=[
            N(name=zn, leds=[0] * sum(n for _, n in segs),
              segments=[N(name=sn, leds_count=n) for sn, n in segs])
            for zn, segs in zones
        ],
    )


TWO_SEGMENTED_ZONES = [
    ("Left",  [("L1", 10), ("L2", 20)]),
    ("Right", [("R1", 30), ("R2", 40)]),
]


def test_segment_zone_indexes_are_unique_per_device():
    indexes = [z["zone_index"] for z in
               api._read_openrgb_zones(_segmented_device("Strip", TWO_SEGMENTED_ZONES))]
    assert len(indexes) == len(set(indexes)) == 4


def test_segmented_device_is_stable_across_startups(tmp_path, monkeypatch, capsys):
    dev = _segmented_device("Strip", TWO_SEGMENTED_ZONES)
    first = _run(tmp_path, monkeypatch, {}, (dev, TopologyType.LINEAR))
    assert [z["led_count"] for z in first["Strip::linear"]["zones"]] == [10, 20, 30, 40]

    capsys.readouterr()
    api.init_topology_api(_Manager((dev, TopologyType.LINEAR)))   # second startup
    assert "differs from hardware" not in capsys.readouterr().out
    second = json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())["topologies"]
    assert second["Strip::linear"]["zones"] == first["Strip::linear"]["zones"]


def test_change_on_a_segment_is_detected(tmp_path, monkeypatch):
    dev = _segmented_device("Strip", TWO_SEGMENTED_ZONES)
    first = _run(tmp_path, monkeypatch, {}, (dev, TopologyType.LINEAR))

    changed = _segmented_device("Strip", [
        ("Left",  [("L1", 15), ("L2", 20)]),     # L1: 10 -> 15
        ("Right", [("R1", 30), ("R2", 40)]),
    ])
    api.init_topology_api(_Manager((changed, TopologyType.LINEAR)))
    zones = json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())["topologies"]["Strip::linear"]["zones"]
    assert [z["led_count"] for z in zones] == [15, 20, 30, 40]


def test_resync_keeps_each_segment_layout(tmp_path, monkeypatch):
    dev = _segmented_device("Strip", TWO_SEGMENTED_ZONES)
    first = _run(tmp_path, monkeypatch, {}, (dev, TopologyType.LINEAR))
    saved = json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())
    for i, z in enumerate(saved["topologies"]["Strip::linear"]["zones"]):
        z["position"] = {"x": 100 * i, "y": 0}          # distinct layout per segment
    api.TOPOLOGY_CONFIG_FILE.write_text(json.dumps(saved))

    changed = _segmented_device("Strip", [
        ("Left",  [("L1", 10), ("L2", 20)]),
        ("Right", [("R1", 30), ("R2", 45)]),            # R2: 40 -> 45
    ])
    api.init_topology_api(_Manager((changed, TopologyType.LINEAR)))
    zones = json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())["topologies"]["Strip::linear"]["zones"]
    assert [z["position"]["x"] for z in zones] == [0, 100, 200, 300]
    assert [z["led_count"] for z in zones] == [10, 20, 30, 45]


# -- reconnect -----------------------------------------------------------------

class _Service:
    def __init__(self):
        self.refreshed = []

    def refresh_zones(self, device_key):
        self.refreshed.append(device_key)


class _ReconnectingManager(_Manager):
    """Manager already holding devices; reconnect() re-enumerates the hardware."""

    def __init__(self, after_reconnect, *devices):
        super().__init__(*devices)
        self._after = after_reconnect

    def reconnect(self, host, port):
        self.devices = _Manager(*self._after).devices
        return True


def test_sync_runs_after_reconnect_with_existing_manager(tmp_path, monkeypatch):
    from api import settings_api

    stale = {"Strip::linear": {"zones": [_zone(0, "Top", 60)]}}
    service = _Service()
    manager = _ReconnectingManager(
        [(_device("Strip", [("Top", 30)]), TopologyType.LINEAR)],      # hardware now has 30
        (_device("Strip", [("Top", 60)]), TopologyType.LINEAR),
    )
    _run(tmp_path, monkeypatch, stale, (_device("Strip", [("Top", 60)]), TopologyType.LINEAR))
    api.init_topology_api(manager, service)
    service.refreshed.clear()

    monkeypatch.setattr(settings_api, "_settings",
                        N(get_openrgb_host=lambda: "localhost", get_openrgb_port=lambda: 6742))
    monkeypatch.setattr(settings_api, "_openrgb_manager", manager)
    monkeypatch.setattr(settings_api, "_ambilight_service", service)

    assert settings_api.reconnect_openrgb()["ok"]

    zones = json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())["topologies"]["Strip::linear"]["zones"]
    assert zones[0]["led_count"] == 30
    assert service.refreshed == ["Strip::linear"]


# -- legacy data / compatibility -----------------------------------------------

def test_legacy_repeated_indexes_are_renumbered_keeping_layout(tmp_path, monkeypatch, capsys):
    # what older versions saved for two segmented zones: indexes 0,1,0,1
    legacy = {"Strip::linear": {"zones": [
        _zone(0, "L1", 10, position={"x": 0, "y": 0}),
        _zone(1, "L2", 20, position={"x": 100, "y": 0}),
        _zone(0, "R1", 30, position={"x": 200, "y": 0}),
        _zone(1, "R2", 40, position={"x": 300, "y": 0}),
    ]}}
    dev = _segmented_device("Strip", TWO_SEGMENTED_ZONES)
    topo = _run(tmp_path, monkeypatch, legacy, (dev, TopologyType.LINEAR))
    zones = topo["Strip::linear"]["zones"]
    assert [z["zone_index"] for z in zones] == [0, 1, 2, 3]
    assert [z["name"] for z in zones] == ["L1", "L2", "R1", "R2"]
    assert [z["position"]["x"] for z in zones] == [0, 100, 200, 300]

    capsys.readouterr()
    api.init_topology_api(_Manager((dev, TopologyType.LINEAR)))
    assert "differs from hardware" not in capsys.readouterr().out


def test_device_without_segments_keeps_its_indexes():
    dev = _device("Strip", [("A", 5), ("B", 6), ("C", 7)])
    assert [z["zone_index"] for z in api._read_openrgb_zones(dev)] == [0, 1, 2]


def test_sync_runs_when_manager_is_created_after_start(tmp_path, monkeypatch):
    import openrgb
    from api import settings_api

    hardware = [_device("Strip", [("Top", 30)])]
    monkeypatch.setattr(openrgb, "OpenRGBClient", lambda host, port: N(devices=hardware))

    stale = {"Strip::linear": {"zones": [_zone(0, "Top", 60)]}}
    _run(tmp_path, monkeypatch, stale)             # app started with no hardware
    service = _Service()
    monkeypatch.setattr(api, "_openrgb_manager", None)
    monkeypatch.setattr(settings_api, "_settings",
                        N(get_openrgb_host=lambda: "localhost", get_openrgb_port=lambda: 6742))
    monkeypatch.setattr(settings_api, "_openrgb_manager", None)
    monkeypatch.setattr(settings_api, "_ambilight_service", service)
    from api import ambilight_api
    monkeypatch.setattr(ambilight_api, "init_ambilight_api", lambda *a, **k: None)

    assert settings_api.reconnect_openrgb()["ok"]
    zones = json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())["topologies"]["Strip::linear"]["zones"]
    assert zones[0]["led_count"] == 30
    assert service.refreshed == ["Strip::linear"]
