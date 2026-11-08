"""wait_devices_settled: a freshly started OpenRGB lists devices progressively."""

from types import SimpleNamespace as N

from utils import openrgb_bootstrap as ob


class _Client:
    """Device count seen on each refresh(), then it stays on the last value."""

    def __init__(self, counts):
        self._counts = list(counts)
        self.devices = []
        self.refreshes = 0

    def refresh(self):
        self.refreshes += 1
        n = self._counts.pop(0) if len(self._counts) > 1 else self._counts[0]
        self.devices = [N()] * n


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
