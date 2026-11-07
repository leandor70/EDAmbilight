"""Notices about hardware that changed since the last start."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest                                              # noqa: E402
from api import topology_api as api                        # noqa: E402
from effects.openrgb_manager import TopologyType           # noqa: E402
from test_topology_sync import _Manager, _device, _zone   # noqa: E402

LINEAR = TopologyType.LINEAR


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, "TOPOLOGY_CONFIG_FILE", Path("config/device_topologies.json"))
    api.TOPOLOGY_CONFIG_FILE.parent.mkdir()
    api.dismiss_hardware_notices()
    yield
    api.dismiss_hardware_notices()


def _start(*devices, topologies=None):
    if not api.TOPOLOGY_CONFIG_FILE.exists():             # later starts keep what was saved
        api.TOPOLOGY_CONFIG_FILE.write_text(
            json.dumps({"version": 1, "topologies": topologies or {}}))
    api.init_topology_api(_Manager(*devices))


def _strip(name="Strip", zones=(("Top", 60),)):
    return (_device(name, list(zones)), LINEAR)


def _kinds():
    return sorted((n["kind"], n["device"]) for n in api.get_hardware_notices())


def test_first_run_is_silent_and_records_the_devices():
    _start(_strip())
    assert api.get_hardware_notices() == []
    assert json.loads(Path("config/hardware_seen.json").read_text()) == {"devices": ["Strip::linear"]}


def test_same_hardware_gives_no_notice():
    _start(_strip())
    _start(_strip())
    assert api.get_hardware_notices() == []


def test_added_device_is_reported():
    _start(_strip())
    _start(_strip(), _strip("Mouse", (("Logo", 2),)))
    assert _kinds() == [("added", "Mouse::linear")]
    text = api.get_hardware_notices()[0]["text"]
    assert "Mouse" in text and "enable it in Control" in text


def test_removed_device_is_reported_once_and_keeps_its_topology():
    _start(_strip(), _strip("Mouse", (("Logo", 2),)))
    _start(_strip())
    assert _kinds() == [("removed", "Mouse::linear")]
    topologies = json.loads(api.TOPOLOGY_CONFIG_FILE.read_text())["topologies"]
    assert "Mouse::linear" in topologies                  # settings kept
    api.dismiss_hardware_notices()
    _start(_strip())                                      # next start: already known
    assert api.get_hardware_notices() == []


def test_changed_led_count_is_reported():
    _start(_strip())
    _start(_strip(zones=(("Top", 30),)))
    assert _kinds() == [("changed", "Strip::linear")]
    assert "60->30" in api.get_hardware_notices()[0]["text"]


def test_no_devices_detected_is_not_reported_as_everything_removed():
    _start(_strip())
    _start()                                              # OpenRGB up, hardware not ready
    assert api.get_hardware_notices() == []
    _start(_strip())                                      # and nothing is lost afterwards
    assert api.get_hardware_notices() == []


def test_duplicate_names_are_shown_with_their_number():
    assert api._display_name("Strip::linear#2") == "Strip #2"
    assert api._display_name("Strip::linear") == "Strip"


def test_same_notice_is_not_listed_twice():
    _start(_strip())
    _start(_strip(), _strip("Mouse", (("Logo", 2),)))
    api.sync_topologies_with_hardware()                   # e.g. after a reconnect
    assert len(api.get_hardware_notices()) == 1


def test_dismiss_clears_the_list():
    _start(_strip())
    _start(_strip(), _strip("Mouse", (("Logo", 2),)))
    assert api.dismiss_hardware_notices() == {"ok": True}
    assert api.get_hardware_notices() == []
