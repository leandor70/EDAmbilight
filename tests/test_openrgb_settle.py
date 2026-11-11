"""wait_devices_settled: a freshly started OpenRGB lists devices progressively."""

from types import SimpleNamespace as N

from utils import openrgb_bootstrap as ob


NAMES = ["Corsair Vengeance RGB RS DDR4", "Corsair Vengeance RGB RS DDR4", "B450 AORUS PRO-CF",
         "ASUS TUF Gaming K7", "Logitech G933 Lightsync Headset", "Tunable RGB Gaming Mouse G502",
         "LedStripScrivania"]


class _Client:
    """Device count seen on each refresh(), then it stays on the last value.
    The devices are the first n of NAMES, in OpenRGB's detection order."""

    def __init__(self, counts):
        self._counts = list(counts)
        self.devices = []
        self.refreshes = 0

    def refresh(self):
        self.refreshes += 1
        n = self._counts.pop(0) if len(self._counts) > 1 else self._counts[0]
        self.devices = [N(name=NAMES[i % len(NAMES)]) for i in range(n)]


def _fast(monkeypatch):
    """Run the polling loop on a fake clock so the test does not sleep."""
    now = [0.0]
    monkeypatch.setattr(ob.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(ob.time, "sleep", lambda s: now.__setitem__(0, now[0] + s))


def test_waits_until_the_count_stops_changing(monkeypatch):
    _fast(monkeypatch)
    client = _Client([1, 1, 3, 6, 6, 6, 6, 6, 6, 6])
    ob.wait_devices_settled(client, stable_secs=3.0, timeout=45.0)
    assert len(client.devices) == 6          # not stopped at the early 1 or 3


def test_gives_up_after_the_timeout(monkeypatch):
    _fast(monkeypatch)
    client = _Client([0])                    # nothing is ever detected
    ob.wait_devices_settled(client, stable_secs=3.0, timeout=10.0)
    assert 9 <= client.refreshes <= 11


def test_a_failing_poll_does_not_raise(monkeypatch):
    _fast(monkeypatch)

    class Broken:
        devices = []

        def refresh(self):
            raise OSError("connection lost")

    ob.wait_devices_settled(Broken())        # must return, the caller carries on


KEYS = ["ASUS TUF Gaming K7::linear", "B450 AORUS PRO-CF::linear",
        "Corsair Vengeance RGB RS DDR4::linear", "Corsair Vengeance RGB RS DDR4::linear#2",
        "LedStripScrivania::linear", "Logitech G933 Lightsync Headset::linear",
        "Tunable RGB Gaming Mouse G502::linear"]


def test_names_of_keys_keep_repeats():
    c = ob.device_names_of_keys(KEYS)
    assert c["Corsair Vengeance RGB RS DDR4"] == 2 and sum(c.values()) == 7


def test_a_long_pause_in_detection_does_not_lose_devices(monkeypatch):
    """Seen in OpenRGB's log: one memory module at 0.9 s, then nothing for 10 s
    (slow I2C), then the other six. The old rule stopped at 1 device."""
    _fast(monkeypatch)
    client = _Client([1] * 11 + [7])
    assert ob.wait_devices_settled(client, expected=ob.device_names_of_keys(KEYS)) is True
    assert len(client.devices) == 7


def test_old_rule_alone_would_have_stopped_early(monkeypatch):
    _fast(monkeypatch)
    client = _Client([1] * 11 + [7])
    ob.wait_devices_settled(client, stable_secs=5.0)          # nothing expected (first start)
    assert len(client.devices) == 1


def test_all_there_at_once_means_no_wait(monkeypatch):
    _fast(monkeypatch)
    client = _Client([7])
    assert ob.wait_devices_settled(client, expected=ob.device_names_of_keys(KEYS)) is True
    assert client.refreshes == 1


def test_a_device_really_gone_costs_a_bounded_wait(monkeypatch):
    _fast(monkeypatch)
    client = _Client([6])                                      # one device unplugged
    t0 = ob.time.monotonic()
    done = ob.wait_devices_settled(client, expected=ob.device_names_of_keys(KEYS),
                                   missing_stable_secs=15.0, timeout=45.0)
    assert done is False and len(client.devices) == 6
    assert 14 <= ob.time.monotonic() - t0 <= 17                 # not the whole 45 s


def test_progress_is_reported(monkeypatch):
    _fast(monkeypatch)
    seen = []
    ob.wait_devices_settled(_Client([2, 5, 7]), expected=ob.device_names_of_keys(KEYS),
                            status_cb=seen.append)
    assert seen[0].endswith("(2 of 7)") and seen[-1].endswith("(5 of 7)")
