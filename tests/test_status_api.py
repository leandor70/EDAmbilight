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
    zones = {"A": [{"name": "MonitorTop"}, {"name": "MonitorLeft"}],
             "B": [{"name": "MonitorTop"}]}
    cfg = {"enabled": True, "devices": {
        "A": {"enabled": True, "zones_enabled": {"MonitorLeft": False}},
        "B": {"enabled": False}}}
    _setup(cfg, zones, ["A", "B", "C"])
    s = ambilight_api.get_ambilight_status()
    assert s["active_devices"] == 1
    assert s["active_zones"] == 1            # MonitorLeft switched off
    assert s["devices_total"] == 3
    assert s["mapped_devices"] == 2          # C has no zones


def test_status_no_enabled_device_means_zero_active_zones():
    _setup({"enabled": True, "devices": {}}, {"A": [{"name": "MonitorTop"}]}, ["A"])
    s = ambilight_api.get_ambilight_status()
    assert s["active_zones"] == 0 and s["mapped_devices"] == 1


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
