"""Test standalone del black-border detector (nessuna dipendenza di test).

Esecuzione:  python tests/test_blackbar.py   (dalla root del progetto)
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from effects.ambilight_service import (
    AmbilightService, _detect_content_rect, _BB_STEP,
)

W, H = 3440, 1440   # ultrawide 21:9
TOL  = 2 * _BB_STEP


def _frame_with_bars(left=0, right=0, top=0, bottom=0):
    """Frame BGR con contenuto casuale luminoso e bande nere ai lati."""
    rng = np.random.default_rng(42)
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    content = rng.integers(60, 256, size=(H - top - bottom, W - left - right, 3),
                           dtype=np.uint8)
    frame[top:H - bottom or None, left:W - right or None] = content
    return frame


def _assert_close(name, got, expected):
    assert abs(got - expected) <= TOL, f"{name}: atteso ~{expected}, ottenuto {got}"


def test_pillarbox_25pct():
    bar = int(W * 0.25)
    rect = _detect_content_rect(_frame_with_bars(left=bar, right=bar), 18)
    assert rect is not None, "pillarbox non rilevato"
    x0, y0, x1, y1 = rect
    _assert_close("x0", x0, bar)
    _assert_close("x1", x1, W - bar)
    _assert_close("y0", y0, 0)
    _assert_close("y1", y1, H)
    print(f"  pillarbox 25%        -> rect {rect}  OK")


def test_letterbox_12pct():
    bar = int(H * 0.12)
    rect = _detect_content_rect(_frame_with_bars(top=bar, bottom=bar), 18)
    assert rect is not None, "letterbox non rilevato"
    x0, y0, x1, y1 = rect
    _assert_close("y0", y0, bar)
    _assert_close("y1", y1, H - bar)
    print(f"  letterbox 12%        -> rect {rect}  OK")


def test_combined_bars():
    bx, by = int(W * 0.20), int(H * 0.10)
    rect = _detect_content_rect(_frame_with_bars(left=bx, right=bx, top=by, bottom=by), 18)
    assert rect is not None
    x0, y0, x1, y1 = rect
    _assert_close("x0", x0, bx); _assert_close("y0", y0, by)
    _assert_close("x1", x1, W - bx); _assert_close("y1", y1, H - by)
    print(f"  bande combinate      -> rect {rect}  OK")


def test_full_bright_frame():
    rect = _detect_content_rect(_frame_with_bars(), 18)
    assert rect is not None
    x0, y0, x1, y1 = rect
    assert x0 <= _BB_STEP and y0 <= _BB_STEP and x1 >= W - _BB_STEP and y1 >= H - _BB_STEP, \
        f"frame pieno dovrebbe dare rect ~full, ottenuto {rect}"
    print(f"  frame pieno          -> rect ~full  OK")


def test_black_frame_undecidable():
    rect = _detect_content_rect(np.zeros((H, W, 3), dtype=np.uint8), 18)
    assert rect is None, "frame nero deve essere indecidibile (None)"
    print("  frame nero           -> None (mantieni stato)  OK")


def test_tiny_region_rejected():
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[600:700, 1600:1800] = 200   # regione minuscola (<30% per lato)
    rect = _detect_content_rect(frame, 18)
    assert rect is None, "regione troppo piccola deve essere scartata"
    print("  regione minuscola    -> None (guardia min size)  OK")


def test_hysteresis():
    svc = AmbilightService(None)
    cfg = {"bb_interval": 0.0, "bb_threshold": 18, "bb_consistent": 3}
    bar = int(W * 0.25)
    pillar = _frame_with_bars(left=bar, right=bar)
    full   = _frame_with_bars()
    black  = np.zeros((H, W, 3), dtype=np.uint8)

    # servono 3 rilevamenti concordi prima di applicare
    svc._update_content_rect(pillar, cfg)
    assert svc.content_rect is None, "rect applicato troppo presto (1)"
    svc._update_content_rect(pillar, cfg)
    assert svc.content_rect is None, "rect applicato troppo presto (2)"
    svc._update_content_rect(pillar, cfg)
    assert svc.content_rect is not None, "rect non applicato dopo 3 rilevamenti"
    applied = svc.content_rect
    print(f"  isteresi (3x)        -> applicato {applied}  OK")

    # un frame nero NON deve resettare lo stato
    svc._update_content_rect(black, cfg)
    assert svc.content_rect == applied, "frame nero ha alterato lo stato"
    print("  frame nero in mezzo  -> stato conservato  OK")

    # ritorno a schermo intero: di nuovo 3 rilevamenti
    svc._update_content_rect(full, cfg)
    svc._update_content_rect(full, cfg)
    assert svc.content_rect == applied
    svc._update_content_rect(full, cfg)
    assert svc.content_rect is None, "non è tornato a schermo intero"
    print("  ritorno a full       -> rect None dopo 3 rilevamenti  OK")


def test_process_frame_crop():
    """_process_frame con bande deve campionare il contenuto, non le bande."""
    svc = AmbilightService(None)
    bar = int(W * 0.25)
    pillar = _frame_with_bars(left=bar, right=bar)
    cfg = {"black_bar_detect": True, "bb_interval": 0.0, "bb_threshold": 18,
           "bb_consistent": 1, "strategy": "percentile", "depth": 5,
           "saturation_boost": 1.0, "devices": {}}
    svc._process_frame(pillar, cfg)   # nessun device: testa solo il crop
    assert svc.content_rect is not None
    x0, y0, x1, y1 = svc.content_rect
    cropped = pillar[y0:y1, x0:x1]
    # il bordo sinistro del crop deve essere contenuto luminoso, non banda nera
    left_strip = cropped[:, : max(1, int(cropped.shape[1] * 0.05))]
    assert left_strip.mean() > 40, f"bordo sinistro ancora nero (mean={left_strip.mean():.1f})"
    print(f"  _process_frame       -> crop a {x1-x0}x{y1-y0}px, bordo luminoso  OK")


def test_performance():
    frame = _frame_with_bars(left=400, right=400)
    # best of 5 batches: a busy PC (other programs, the test run itself) must not
    # make it fail, only a really slow detection does
    n, best = 40, float("inf")
    for _ in range(5):
        t0 = time.perf_counter()
        for _ in range(n):
            _detect_content_rect(frame, 18)
        best = min(best, (time.perf_counter() - t0) / n * 1000)
    per_call = best
    assert per_call < 5.0, f"detection troppo lenta: {per_call:.2f} ms"
    print(f"  performance          -> {per_call:.2f} ms/rilevamento su {W}x{H}  OK")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    print(f"Black-border detector — {len(tests)} test su frame {W}x{H}\n")
    for t in tests:
        t()
    print("\nTutti i test superati.")
