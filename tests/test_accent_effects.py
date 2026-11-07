"""Accento sul battito: formule, stato (inviluppo / limite) e integrazione nel servizio."""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from effects import accent_effects as ae                     # noqa: E402
from effects.ambilight_service import AmbilightService       # noqa: E402


def P(**over):
    """Parametri normalizzati partendo da quelli di default."""
    cfg = {f"accent_{k}": v for k, v in over.items()}
    return ae.params_from_cfg(cfg)


def rgb(*c):
    return np.array([c], dtype=np.float32)


ALL = np.array([True])


# -- parametri -----------------------------------------------------------------

def test_defaults_and_clamping():
    p = ae.params_from_cfg({})
    assert p["mode"] == "mix" and p["hue_mode"] == "off" and not p["enabled"]
    assert p["max_per_sec"] == 3 and abs(p["intensity"] - 0.25) < 1e-9
    assert abs(p["min_strength"] - 0.4) < 1e-9
    assert list(p["color"]) == [255, 255, 255]

    p = ae.params_from_cfg({"accent_intensity": 9999, "accent_duration": -5,
                            "accent_mode": "bogus", "accent_color": "zzz",
                            "accent_hue_mode": 7, "accent_sensitivity": "x"})
    assert p["intensity"] == 2.0                  # tetto 200%
    assert p["duration_ms"] == 20                 # minimo
    assert p["mode"] == "mix" and p["hue_mode"] == "off"
    assert list(p["color"]) == [255, 255, 255]    # colore non valido -> bianco
    assert p["sensitivity"] == 50                 # non numerico -> default

    assert list(ae.params_from_cfg({"accent_color": "#f80"})["color"]) == [255, 136, 0]


# -- formule -------------------------------------------------------------------

def test_multiplicative_keeps_hue_and_never_lights_black():
    out = ae.render(rgb(200, 100, 50), ALL, 1.0, 0, P(mode="mul"))[0]
    assert out.max() <= 255
    assert abs(out[0] / out[1] - 2.0) < 0.02 and abs(out[1] / out[2] - 2.0) < 0.02   # stessa tinta
    black = ae.render(rgb(0, 0, 0), ALL, 2.0, 0, P(mode="mul"))[0]
    assert black.max() == 0


def test_additive_lights_black_with_the_flash_color():
    out = ae.render(rgb(0, 0, 0), ALL, 0.5, 0, P(mode="add", color="#ff0000"))[0]
    assert abs(out[0] - 127.5) < 0.6 and out[1] == 0 and out[2] == 0


def test_mixed_is_between_multiplicative_and_additive():
    base = rgb(100, 60, 20)
    mul = ae.render(base, ALL, 0.6, 0, P(mode="mul"))[0]
    add = ae.render(base, ALL, 0.6, 0, P(mode="add"))[0]
    assert np.allclose(ae.render(base, ALL, 0.6, 0, P(mode="mix", dark_lift=0))[0], mul, atol=0.6)
    assert np.allclose(ae.render(base, ALL, 0.6, 0, P(mode="mix", dark_lift=100))[0], add, atol=0.6)
    mid = ae.render(base, ALL, 0.6, 0, P(mode="mix", dark_lift=50))[0]
    assert (mid >= np.minimum(mul, add) - 0.6).all() and (mid <= np.maximum(mul, add) + 0.6).all()
    # su un LED nero il misto illumina solo per la quota additiva
    dark = ae.render(rgb(0, 0, 0), ALL, 1.0, 0, P(mode="mix", dark_lift=50))[0]
    assert abs(dark[0] - 127.5) < 0.6


def test_overflow_is_scaled_not_clipped_per_channel():
    # 200,100,50 con un flash bianco molto forte: ogni canale supererebbe 255
    out = ae.render(rgb(200, 100, 50), ALL, 2.0, 0, P(mode="add"))[0]
    assert out.max() <= 255.0 + 1e-3
    assert out[0] >= out[1] >= out[2]            # l'ordine dei canali si conserva
    # moltiplicativo: 4:2:1 resta 4:2:1 anche se il canale piu' alto sfora
    m = ae.render(rgb(200, 100, 50), ALL, 3.0, 0, P(mode="mul"))[0]
    assert abs(m[0] - 255) < 1e-3 and abs(m[0] / m[2] - 4.0) < 0.05


def test_mask_leaves_other_leds_untouched():
    base = np.array([[100, 100, 100], [100, 100, 100]], dtype=np.float32)
    mask = np.array([True, False])
    out = ae.render(base, mask, 1.0, 0, P(mode="mul"))
    assert out[0, 0] > 150 and (out[1] == base[1]).all()


def test_hue_rotation():
    red = ae.render(rgb(255, 0, 0), ALL, 0, 120, P())[0]
    assert abs(red[1] - 255) < 1 and red[0] < 1 and red[2] < 1          # rosso +120 = verde
    assert (ae.render(rgb(90, 90, 90), ALL, 0, 77, P())[0] == 90).all()  # i grigi non cambiano
    assert ae.render(rgb(0, 0, 0), ALL, 0, 77, P())[0].max() == 0        # il nero resta nero


# -- stato: inviluppo e limite ---------------------------------------------------

def test_envelope_attack_and_decay():
    p = P(attack=20, duration=200, intensity=100, max_boost=300)
    s = ae.AccentState()
    assert s.trigger(1.0, p, now=10.0)
    k0, _ = s.levels(10.0, p);            assert k0 == 0.0
    k_half, _ = s.levels(10.010, p);      assert abs(k_half - 0.5) < 1e-6      # a meta' attacco
    k_peak, _ = s.levels(10.020, p);      assert abs(k_peak - 1.0) < 1e-6
    k_tau, _ = s.levels(10.020 + 0.200, p)
    assert abs(k_tau - math.exp(-1)) < 1e-6                                     # una costante di tempo
    k_late, hue = s.levels(12.0, p)
    assert not ae.AccentState.is_active(k_late, hue)


def test_strength_and_boost_cap():
    p = P(attack=0, intensity=200, max_boost=50)
    s = ae.AccentState(); s.trigger(1.0, p, now=0.0)
    assert abs(s.levels(0.0, p)[0] - 0.5) < 1e-9           # tetto 50%
    p = P(attack=0, intensity=100, max_boost=300, min_strength=0)
    s = ae.AccentState(); s.trigger(0.4, p, now=0.0)
    assert abs(s.levels(0.0, p)[0] - 0.4) < 1e-9            # forza del battito


def test_strong_beats_only_filter():
    # soglia = 0.35 + 0.65 * cursore: 0 accetta ogni battito, 100 solo i piu' forti
    assert abs(ae.strength_threshold(P(min_strength=0)) - 0.35) < 1e-9
    assert abs(ae.strength_threshold(P(min_strength=100)) - 1.0) < 1e-9
    assert abs(ae.strength_threshold(P(min_strength=40)) - 0.61) < 1e-9

    p = P(min_strength=40, max_per_sec=0)
    s = ae.AccentState()
    assert not s.trigger(0.50, p, now=0.0)                   # debole: scartato
    assert s.levels(0.0, p)[0] == 0                          # e non lascia traccia
    assert s.trigger(0.62, p, now=0.1)                       # sopra soglia: accettato
    assert s.trigger(1.0, p, now=0.2)

    everything = P(min_strength=0, max_per_sec=0)
    assert ae.AccentState().trigger(0.35, everything, now=0.0)     # il minimo del rilevatore passa

    strict = P(min_strength=100, max_per_sec=0)
    assert ae.AccentState().trigger(1.0, strict, now=0.0)          # il Test accent (forza 1.0) passa sempre
    assert not ae.AccentState().trigger(0.99, strict, now=0.0)


def test_weak_beats_do_not_consume_the_rate_limit():
    p = P(min_strength=40, max_per_sec=2)                     # un lampo ogni 0.5 s
    s = ae.AccentState()
    assert s.trigger(0.9, p, now=0.0)
    assert not s.trigger(0.4, p, now=0.6)                     # debole: scartato...
    assert s.trigger(0.9, p, now=0.7)                         # ...e il forte successivo passa


def test_rate_limiter():
    p = P(max_per_sec=3)
    s = ae.AccentState()
    assert s.trigger(1.0, p, now=0.0)
    assert not s.trigger(1.0, p, now=0.20)                  # < 1/3 s: scartato
    assert s.trigger(1.0, p, now=0.34)
    free = P(max_per_sec=0)                                  # 0 = nessun limite
    s2 = ae.AccentState()
    assert all(s2.trigger(1.0, free, now=i * 0.001) for i in range(5))


def test_retrigger_does_not_stack():
    p = P(attack=0, intensity=100, max_boost=300, max_per_sec=0, duration=500)
    s = ae.AccentState()
    s.trigger(1.0, p, now=0.0)
    s.trigger(1.0, p, now=0.1)
    assert abs(s.levels(0.1, p)[0] - 1.0) < 1e-9            # riparte da 1, non somma


def test_hue_modes():
    pulse = P(hue_mode="pulse", hue_deg=60, attack=0, duration=200)
    s = ae.AccentState(); s.trigger(1.0, pulse, now=0.0)
    assert abs(s.levels(0.0, pulse)[1] - 60) < 1e-9
    step = P(hue_mode="step", hue_deg=30, hue_decay=1000, max_per_sec=0)
    s = ae.AccentState()
    s.trigger(1.0, step, now=0.0); s.trigger(1.0, step, now=0.0001)
    assert abs(s.levels(0.0001, step)[1] - 60) < 0.1        # due battiti = due passi
    later = s.levels(1.0001, step)[1]
    assert abs(later - 60 * math.exp(-1)) < 0.1             # ritorno lento
    off = P(hue_mode="off")
    s = ae.AccentState(); s.trigger(1.0, off, now=0.0)
    assert s.levels(0.0, off)[1] == 0


# -- integrazione nel servizio ---------------------------------------------------

KEY = "Strip::linear"
W, H = 400, 200


class _Manager:
    def __init__(self):
        self.writes = []

    def get_device_led_count(self, key):
        return 4

    def apply_direct_colors(self, key, colors):
        self.writes.append(list(colors))


def _service(tmp_path, monkeypatch, **accent_cfg):
    monkeypatch.chdir(tmp_path)
    Path("config").mkdir(exist_ok=True)
    zones = [{"zone_index": 0, "name": "MonitorTop", "led_count": 4, "led_spacing": 5,
              "position": {"x": 20, "y": 10}, "rotation": 0}]
    Path("config/device_topologies.json").write_text(
        json.dumps({"topologies": {KEY: {"zones": zones}}}))
    mgr = _Manager()
    svc = AmbilightService(mgr)
    svc._config = {
        "enabled": True, "strategy": "mean", "depth": 10, "saturation_boost": 1.0,
        "min_luminance": 0, "black_bar_detect": False,
        "devices": {KEY: {"enabled": True}},
        "accent_mode": "mul", "accent_intensity": 100, "accent_attack": 0,
        "accent_duration": 5000, "accent_max_per_sec": 0, "accent_max_boost": 300,
        **{f"accent_{k}": v for k, v in accent_cfg.items()},
    }
    return svc, mgr


def _gray(v):
    return np.full((H, W, 3), v, dtype=np.uint8)


def test_service_applies_accent_to_written_colors(tmp_path, monkeypatch):
    svc, mgr = _service(tmp_path, monkeypatch)
    svc._process_frame(_gray(100), svc._config)
    plain = mgr.writes[-1][0]
    assert all(abs(c - 100) <= 1 for c in plain)

    assert svc.trigger_accent(1.0)
    svc._process_frame(_gray(100), svc._config)
    boosted = mgr.writes[-1][0]
    assert all(190 <= c <= 201 for c in boosted)             # ~ x2

    # lo stato "base" (usato da standby e dai passi) resta senza accento
    base, _lit = svc._standby_ctx[KEY]
    assert np.allclose(base, 100, atol=1)
    # l'anteprima Live mostra l'accento
    snap_first = svc.get_sampling_snapshot()["zones"][0]["colors"][:6]
    assert int(snap_first[:2], 16) >= 190


def test_service_tick_reapplies_accent_between_frames(tmp_path, monkeypatch):
    svc, mgr = _service(tmp_path, monkeypatch)
    svc._process_frame(_gray(100), svc._config)
    n = len(mgr.writes)
    assert svc._accent_tick(svc._config) is False            # nessun accento: non scrive
    assert len(mgr.writes) == n

    svc.trigger_accent(1.0)
    assert svc._accent_tick(svc._config) is True
    assert all(c >= 190 for c in mgr.writes[-1][0])
    assert len(mgr.writes) == n + 1


def test_service_get_config_includes_accent_defaults(tmp_path, monkeypatch):
    svc, _ = _service(tmp_path, monkeypatch)
    svc._config = {"enabled": True}
    cfg = svc.get_config()
    assert cfg["accent_mode"] == "mix" and cfg["accent_max_per_sec"] == 3
    assert "accent_mode" not in svc._config                  # il file non viene "sporcato"


def test_service_limiter_blocks_rapid_beats(tmp_path, monkeypatch):
    svc, _ = _service(tmp_path, monkeypatch, max_per_sec=2)
    assert svc.trigger_accent(1.0) is True
    assert svc.trigger_accent(1.0) is False


def test_dark_scene_depends_on_mode(tmp_path, monkeypatch):
    # LED nero: il moltiplicativo non lo accende, l'additivo si'
    svc, mgr = _service(tmp_path, monkeypatch, mode="mul")
    svc.trigger_accent(1.0)
    svc._process_frame(_gray(0), svc._config)
    assert max(mgr.writes[-1][0]) == 0

    svc, mgr = _service(tmp_path, monkeypatch, mode="add", color="#ff0000")
    svc.trigger_accent(1.0)
    svc._process_frame(_gray(0), svc._config)
    r, g, b = mgr.writes[-1][0]
    assert r > 200 and g == 0 and b == 0
