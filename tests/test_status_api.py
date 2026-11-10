"""Test di get_ambilight_status / get_ambilight_devices con servizio e manager finti."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api import ambilight_api


class _FakeService:
    def __init__(self, cfg, zones):
        self._cfg, self._zones = cfg, zones
        self.is_running, self.actual_fps = True, 14.0
        self.capturer_name, self.content_rect = "wgc", None

    def get_config(self):
        return dict(self._cfg)

    def get_device_zones(self, key):
        return self._zones.get(key, []), 0


def _manager(keys):
    ctrls = [SimpleNamespace(key=k) for k in keys]
    return SimpleNamespace(devices=ctrls, _make_device_key=lambda c: c.key)


def _setup(cfg, zones, keys):
    ambilight_api._ambilight_service = _FakeService(cfg, zones)
    ambilight_api._openrgb_manager = _manager(keys)


def test_status_counts_only_enabled_and_zone_enabled():
    zones = {"A": [{"name": "MonitorTop", "zone_index": 0, "edge": "top"},
                   {"name": "MonitorLeft", "zone_index": 1, "edge": "left"}],
             "B": [{"name": "MonitorTop", "zone_index": 0, "edge": "top"}]}
    cfg = {"enabled": True, "devices": {
        "A": {"enabled": True, "zones_enabled": {"1": False}},
        "B": {"enabled": False}}}
    _setup(cfg, zones, ["A", "B", "C"])
    s = ambilight_api.get_ambilight_status()
    assert s["active_devices"] == 1
    assert s["active_zones"] == 1            # MonitorLeft switched off
    assert s["devices_total"] == 3
    assert s["mapped_devices"] == 2          # C has no zones


def test_status_no_enabled_device_means_zero_active_zones():
    _setup({"enabled": True, "devices": {}}, {"A": [{"name": "MonitorTop", "zone_index": 0, "edge": "top"}]}, ["A"])
    s = ambilight_api.get_ambilight_status()
    assert s["active_zones"] == 0 and s["mapped_devices"] == 1


def test_zone_switches_go_by_index_never_by_name():
    from effects.ambilight_service import is_zone_enabled
    zones = [{"name": "???", "zone_index": i} for i in (1, 5, 6)]
    by_name = {"???": False}                                     # old files: keys by name
    assert all(is_zone_enabled(by_name, z) for z in zones)       # ignored: on by default
    by_index = {"???": False, "5": False}
    assert [is_zone_enabled(by_index, z) for z in zones] == [True, False, True]


def test_phantom_zones_are_never_driven(tmp_path, monkeypatch):
    import json
    from effects import ambilight_service as svc
    def z(i, name):
        return {"zone_index": i, "name": name, "led_count": 1, "position": {"x": 5, "y": i},
                "rotation": 0, "direction": "forward"}
    topo = {"topologies": {"D": {"zones": [z(0, "CPU"), z(1, "???"), z(2, "Case")]}}}
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "device_topologies.json").write_text(json.dumps(topo))
    monkeypatch.chdir(tmp_path)
    zones, total = svc.build_device_zones("D")
    assert [x["name"] for x in zones] == ["CPU", "Case"]   # '???' = LEDs that do not exist
    assert total == 3                      # LED offsets still count them
    assert [x["led_offset"] for x in zones] == [0, 2]


def test_set_zone_enabled_stores_index_key():
    saved = {}
    svc = _FakeService({"devices": {}}, {})
    svc.set_config = lambda u: saved.update(u)
    ambilight_api._ambilight_service = svc
    ambilight_api.set_ambilight_zone_enabled("A", 5, True)
    assert saved["devices"]["A"]["zones_enabled"] == {"5": True}


def test_status_without_service_has_new_keys():
    ambilight_api._ambilight_service = None
    s = ambilight_api.get_ambilight_status()
    for k in ("active_devices", "active_zones", "devices_total", "mapped_devices"):
        assert s[k] == 0


if __name__ == "__main__":
    test_status_counts_only_enabled_and_zone_enabled()
    test_status_no_enabled_device_means_zero_active_zones()
    test_status_without_service_has_new_keys()
    print("OK")
