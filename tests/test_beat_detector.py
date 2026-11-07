"""Rilevatore di battito su audio sintetico (cassa a tempo su un fondo continuo)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from effects.beat_detector import BeatDetector, threshold_k, min_ratio   # noqa: E402

SR = 48000


def track(bpm=120, secs=12, amp=0.8, pad=0.05, noise=0.005, seed=1):
    """Cassa (sinusoide con glide e decadimento) a tempo + accordo continuo + rumore."""
    rng = np.random.default_rng(seed)
    n = int(SR * secs)
    t = np.arange(n) / SR
    x = pad * (np.sin(2 * np.pi * 220 * t) + 0.7 * np.sin(2 * np.pi * 330 * t))
    x += noise * rng.standard_normal(n)
    beats = np.arange(0.5, secs - 0.3, 60.0 / bpm)
    for b in beats:
        i = int(b * SR)
        m = min(int(0.25 * SR), n - i)
        tt = np.arange(m) / SR
        f = 50 + 90 * np.exp(-tt / 0.03)
        x[i:i + m] += amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.07)
    return x.astype(np.float32), beats


def detect(x, sens=50, chunk=None):
    d = BeatDetector(SR)
    found = []
    if chunk is None:
        found += d.process(x, sens, now=len(x) / SR)
    else:
        for i in range(0, len(x), chunk):
            blk = x[i:i + chunk]
            found += d.process(blk, sens, now=(i + len(blk)) / SR)
    return found, d


def hits(found, beats, tol=0.08):
    ts = np.array([b.time for b in found])
    return sum(1 for b in beats if len(ts) and np.min(np.abs(ts - b)) < tol)


def test_kick_at_120bpm_is_found_on_time():
    x, beats = track()
    found, _ = detect(x)
    assert hits(found, beats) >= len(beats) - 1            # al massimo uno perso
    assert len(found) - hits(found, beats) <= 1             # nessun falso battito
    iv = np.diff([b.time for b in found])
    assert abs(np.median(iv) - 0.5) < 0.03
    assert all(0.35 <= b.strength <= 1.0 for b in found)


def test_other_tempos():
    for bpm in (90, 150):
        x, beats = track(bpm=bpm)
        found, _ = detect(x)
        assert hits(found, beats) >= len(beats) - 2, bpm
        assert len(found) - hits(found, beats) <= 2, bpm


def test_block_size_does_not_matter():
    x, beats = track()
    whole, _ = detect(x)
    small, _ = detect(x, chunk=480)
    assert abs(len(whole) - len(small)) <= 1
    assert hits(small, beats) >= len(beats) - 1


def test_volume_independent():
    x, beats = track(amp=0.1, pad=0.006, noise=0.0006)
    found, _ = detect(x)
    assert hits(found, beats) >= len(beats) - 2


def test_sensitivity_orders_detection():
    x, beats = track(amp=0.05, pad=0.003, noise=0.0003)
    low, _ = detect(x, sens=0)
    high, _ = detect(x, sens=100)
    assert len(high) >= len(low)
    assert threshold_k(0) > threshold_k(100) and min_ratio(0) > min_ratio(100)


def test_silence_and_steady_sound_give_no_beats():
    n = SR * 10
    for sig in (np.zeros(n, dtype=np.float32),
                (0.0002 * np.random.default_rng(3).standard_normal(n)).astype(np.float32),
                (0.05 * np.sin(2 * np.pi * 220 * np.arange(n) / SR)).astype(np.float32)):
        found, _ = detect(sig)
        assert found == []


def test_stationary_noise_is_rare_and_weak():
    n = SR * 10
    for amp in (0.05, 0.3):
        sig = (amp * np.random.default_rng(3).standard_normal(n)).astype(np.float32)
        found, _ = detect(sig)
        assert len(found) <= 6                              # sporadici
        assert all(b.strength < 0.6 for b in found)         # e comunque deboli


def test_meter_bands():
    x, _ = track()
    _, d = detect(x)
    assert d.bass > 0.4 and d.level > 0.3
    assert d.high < 0.05                                     # la cassa non ha alti
    assert d.beats > 15 and d.last_beat_time is not None


def test_meter_is_zero_on_silence():
    _, d = detect(np.zeros(SR, dtype=np.float32))
    assert d.level == 0 and d.bass == 0 and d.mid == 0 and d.high == 0
