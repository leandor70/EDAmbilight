"""Test degli effetti di standby (funzioni pure)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from effects import standby_effects as se

BASE = np.array([[200.0, 100.0, 50.0]] * 6)
MASK = np.array([True, True, True, True, False, False])


def _arr(mode, t, base=BASE, mask=MASK, level=0.6):
    return np.array(se.render(mode, t, base, mask, level))


def test_hold_and_unknown_write_nothing():
    assert se.render("hold", 5, BASE, MASK) is None
    assert se.render("bogus", 5, BASE, MASK) is None


def test_fade_goes_from_base_to_black_and_masked_leds_stay_off():
    start, end = _arr("fade", 0), _arr("fade", se.FADE_SECS)
    assert start[0].tolist() == [200, 100, 50]
    assert end.sum() == 0
    assert start[4:].sum() == 0


def test_dim_keeps_a_faint_glow():
    end = _arr("dim", 999)
    assert end[0].tolist() == [30, 15, 8]    # 15% of base, rounded
    assert se.is_static("dim", se.FADE_SECS) and not se.is_static("dim", 1)


def test_pulse_breathes_and_falls_back_on_dark_base():
    assert _arr("pulse", 0)[0].tolist() == [200, 100, 50]
    low = _arr("pulse", se.PULSE_SECS / 2)[0]
    assert 0 < low[0] < 40
    dark = _arr("pulse", 0, base=np.zeros((6, 3)))
    assert dark[0].sum() > 0 and dark[4:].sum() == 0


def test_generative_effects_move_and_respect_brightness():
    for mode in ("rainbow", "aurora", "ember"):
        a, b = _arr(mode, 0), _arr(mode, 7)
        assert (a != b).any(), mode
        bright, dim = _arr(mode, 3, level=1.0), _arr(mode, 3, level=0.2)
        assert bright[:4].sum() > dim[:4].sum(), mode
        assert bright[4:].sum() == 0, mode


def test_off_is_black_and_static():
    assert _arr("off", 0).sum() == 0 and se.is_static("off", 0)


def test_values_stay_in_byte_range():
    for mode in se.MODE_IDS:
        out = se.render(mode, 3.3, BASE, MASK, 1.0)
        if out is not None:
            assert all(0 <= c <= 255 for px in out for c in px), mode


def test_service_runs_effect_only_after_grace_and_resets_on_frame(monkeypatch):
    from effects import ambilight_service as amb

    class _Mgr:
        def __init__(self): self.calls = []
        def apply_direct_colors(self, key, colors, mask=None): self.calls.append((key, colors))

    mgr = _Mgr()
    svc = amb.AmbilightService(mgr)
    svc._stop_event.wait = lambda *_: None
    svc._standby_ctx["dev"] = (BASE.astype(np.float32), MASK)
    cfg = {"standby_mode": "pulse", "standby_brightness": 60,
           "devices": {"dev": {"enabled": True}}}

    clock = [100.0]
    monkeypatch.setattr(amb.time, "monotonic", lambda: clock[0])

    svc._on_no_frame(cfg)                       # inizio assenza frame
    assert not svc.standby_active and not mgr.calls
    clock[0] += amb.STANDBY_GRACE + 0.1
    svc._on_no_frame(cfg)
    assert svc.standby_active and mgr.calls and mgr.calls[-1][0] == "dev"
    assert len(mgr.calls[-1][1]) == len(BASE)

    cfg["standby_mode"] = "hold"
    n = len(mgr.calls)
    clock[0] += 1
    svc._on_no_frame(cfg)
    assert len(mgr.calls) == n                  # hold non scrive
