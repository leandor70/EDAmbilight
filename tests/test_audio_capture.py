"""Cattura audio e ascolto dei battiti, con una libreria audio simulata (nessun hardware)."""
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace as N

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import audio_capture as ac                          # noqa: E402
from effects.ambilight_service import AmbilightService        # noqa: E402

SR = 48000
LOOPBACK = {"index": 3, "name": "Speakers (Fake) [Loopback]", "maxInputChannels": 2,
            "defaultSampleRate": float(SR), "isLoopbackDevice": True}


def kick_track(secs=4.5, bpm=120):
    rng = np.random.default_rng(1)
    n = int(SR * secs)
    t = np.arange(n) / SR
    x = 0.05 * (np.sin(2 * np.pi * 220 * t) + 0.7 * np.sin(2 * np.pi * 330 * t))
    x += 0.005 * rng.standard_normal(n)
    beats = np.arange(0.5, secs - 0.3, 60.0 / bpm)
    for b in beats:
        i = int(b * SR); m = min(int(0.25 * SR), n - i); tt = np.arange(m) / SR
        f = 50 + 90 * np.exp(-tt / 0.03)
        x[i:i + m] += 0.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.07)
    return x.astype(np.float32), beats


class FakeStream:
    """Come il loopback WASAPI: consegna i blocchi a tempo reale, poi tace."""

    def __init__(self, callback, data):
        self._cb, self._data, self._active = callback, data, True
        threading.Thread(target=self._feed, daemon=True).start()

    def _feed(self):
        n = 1024
        for i in range(0, len(self._data) - n + 1, n):
            if not self._active:
                return
            self._cb(self._data[i:i + n].tobytes(), n, None, 0)
            time.sleep(n / SR)
        while self._active:
            time.sleep(0.01)

    def is_active(self):
        return self._active

    def stop_stream(self):
        self._active = False

    def close(self):
        self._active = False


def fake_backend(track, devices=(LOOPBACK,)):
    pcm = (np.repeat(track[:, None], 2, axis=1) * 32767).astype(np.int16).reshape(-1)

    class FakePyAudio:
        def get_loopback_device_info_generator(self):
            return iter(devices)

        def get_host_api_info_by_type(self, _t):
            return {"defaultOutputDevice": 1}

        def get_device_info_by_index(self, _i):
            return {"name": "Speakers (Fake)", "isLoopbackDevice": False}

        def open(self, **kw):
            assert kw["input"] and kw["channels"] == 2 and kw["rate"] == SR
            return FakeStream(kw["stream_callback"], pcm)

        def terminate(self):
            pass

    return N(paWASAPI=13, paInt16=8, paContinue=0, PyAudio=FakePyAudio)


def wait_for(cond, secs):
    end = time.monotonic() + secs
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.05)
    return cond()


# -- elenco dispositivi ----------------------------------------------------------

def test_list_devices_with_backend():
    r = ac.list_devices(fake_backend(kick_track(1)[0]))
    assert r == {"available": True, "devices": [LOOPBACK["name"]], "error": ""}


def test_missing_library_is_a_readable_error(monkeypatch):
    monkeypatch.setattr(ac, "_load_backend", lambda: (None, ac.INSTALL_HINT))
    r = ac.list_devices()
    assert r["available"] is False and r["devices"] == [] and "PyAudioWPatch" in r["error"]

    beats = []
    lis = ac.AudioListener(beats.append)             # nessun backend: usa _load_backend
    lis.sync(True, "", 50)
    assert wait_for(lambda: lis.status()["error"], 2)
    st = lis.status()
    assert st["running"] is False and "PyAudioWPatch" in st["error"] and beats == []
    lis.stop()


# -- ascolto ---------------------------------------------------------------------

def test_listener_detects_beats_from_loopback():
    track, expected = kick_track(4.5)
    beats = []
    lis = ac.AudioListener(beats.append, backend=fake_backend(track))
    try:
        lis.sync(True, "", 50)
        assert wait_for(lambda: lis.status()["running"], 3)
        assert wait_for(lambda: len(beats) >= len(expected) - 2, 8)
        st = lis.status()
        assert st["device"] == LOOPBACK["name"] and st["error"] == ""
        assert st["level"] > 0.3 and st["bass"] > 0.4 and st["high"] < 0.1
        assert st["beats"] >= len(expected) - 2 and st["beat_age"] is not None
        assert all(0.35 <= s <= 1.0 for s in beats)
        assert len(beats) <= len(expected) + 1               # nessun falso battito evidente
    finally:
        lis.stop()
    assert lis.status()["running"] is False


def test_listener_goes_silent_when_no_blocks_arrive():
    track, _ = kick_track(1.2)
    lis = ac.AudioListener(lambda s: None, backend=fake_backend(track))
    try:
        lis.sync(True, "", 50)
        assert wait_for(lambda: lis.status()["running"], 3)
        assert wait_for(lambda: lis.status()["silent"], 4)   # la traccia finisce, il loopback tace
        st = lis.status()
        assert st["level"] == 0 and st["bass"] == 0          # il misuratore torna a zero
    finally:
        lis.stop()


def test_sync_stops_when_not_wanted_and_restarts_on_device_change():
    track, _ = kick_track(4.0)
    lis = ac.AudioListener(lambda s: None, backend=fake_backend(track))
    try:
        lis.sync(True, "", 50)
        assert wait_for(lambda: lis.status()["running"], 3)
        lis.sync(False, "", 50)
        assert lis.status()["running"] is False
        lis.sync(True, "", 50)
        assert wait_for(lambda: lis.status()["running"], 3)
        before = lis._capture
        lis.sync(True, "Does not exist", 50)                 # cambio dispositivo: riavvio
        assert wait_for(lambda: "not available" in lis.status()["notice"], 3)
        assert lis._capture is not before and lis.status()["error"] == ""
        first = lis._capture
        lis.sync(True, "Does not exist", 50)                 # stessa scelta: nessun riavvio
        assert lis._capture is first
    finally:
        lis.stop()


# -- servizio --------------------------------------------------------------------

class _Recorder:
    def __init__(self):
        self.calls = []

    def sync(self, want, device, sens):
        self.calls.append((want, device, sens))

    def stop(self):
        pass


def test_service_syncs_audio_with_config():
    svc = AmbilightService(None)
    svc._audio = rec = _Recorder()
    svc._sync_audio({"enabled": True, "accent_enabled": True, "accent_device": "X", "accent_sensitivity": 70})
    svc._sync_audio({"enabled": False, "accent_enabled": True})        # ambilight spento: niente ascolto
    svc._sync_audio({"enabled": True, "accent_enabled": False})        # accento spento: niente ascolto
    assert rec.calls[0] == (True, "X", 70.0)
    assert rec.calls[1][0] is False and rec.calls[2][0] is False


def test_beat_from_audio_triggers_the_accent():
    svc = AmbilightService(None)
    svc._config = {"enabled": True, "accent_attack": 0, "accent_intensity": 100,
                   "accent_duration": 5000, "accent_max_per_sec": 0}
    assert svc._accent_now(svc._config) is None
    svc._audio._on_beat(0.8)                                  # come farebbe il rilevatore
    accent = svc._accent_now(svc._config)
    assert accent is not None and abs(accent[1] - 0.8) < 0.01


def test_missing_device_falls_back_to_the_default_output():
    track, _ = kick_track(1)
    lis = ac.AudioListener(lambda s: None, backend=fake_backend(track))
    try:
        lis.sync(True, "Cuffie scollegate [Loopback]", 50)
        assert wait_for(lambda: lis.status()["running"], 3)
        st = lis.status()
        assert st["error"] == ""                              # not an error: it is listening
        assert st["device"] == LOOPBACK["name"]
        assert "Cuffie scollegate" in st["notice"] and "default output" in st["notice"]
    finally:
        lis.stop()


def test_chosen_device_that_exists_has_no_notice():
    track, _ = kick_track(1)
    lis = ac.AudioListener(lambda s: None, backend=fake_backend(track))
    try:
        lis.sync(True, LOOPBACK["name"], 50)
        assert wait_for(lambda: lis.status()["running"], 3)
        assert lis.status()["notice"] == ""
    finally:
        lis.stop()
