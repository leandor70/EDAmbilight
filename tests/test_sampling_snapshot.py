"""Test standalone dello snapshot di campionatura usato dall'anteprima UI.

Esecuzione:  python tests/test_sampling_snapshot.py   (dalla root del progetto)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from effects.ambilight_service import AmbilightService

W, H = 3440, 1440


def _service(depth=3, strategy="mean", black_bar=False):
    svc = AmbilightService(None)
    svc._preview_until = float("inf")       # a page shows the map: build the preview
    svc._config = {
        "enabled": True, "strategy": strategy, "depth": depth,
        "saturation_boost": 1.0, "min_luminance": 0,
        "black_bar_detect": black_bar,
        "devices": {"dev": {"enabled": True}},
    }
    zones = [
        {"name": "MonitorTop", "zone_index": 0, "led_count": 4, "led_offset": 0,
         "led_start": 0, "led_end": 4, "screen_start": 0.0, "screen_end": 1.0,
         "edge": "top", "reversed": True},
        {"name": "MonitorLeft", "zone_index": 1, "led_count": 2, "led_offset": 4,
         "led_start": 0, "led_end": 2, "screen_start": 0.0, "screen_end": 1.0,
         "edge": "left", "reversed": True},
    ]
    svc.get_device_zones = lambda _key: (zones, 6)
    return svc


def test_geometry_and_depth():
    svc = _service(depth=3)
    svc._process_frame(np.full((H, W, 3), 128, dtype=np.uint8), svc._config)
    snap = svc.get_sampling_snapshot()
    assert snap is not None
    assert snap["frame"] == [W, H]
    assert snap["rect"] == [0, 0, W, H]
    # profondita' = 3% del lato corto, uguale per i bordi usati
    expected = int(min(H, W) * 0.03)
    assert snap["depth"] == {"top": expected, "left": expected}, snap["depth"]
    assert [z["edge"] for z in snap["zones"]] == ["top", "left"]
    assert len(snap["zones"][0]["colors"]) == 4 * 6
    assert snap["age"] >= 0
    print(f"  geometria/profondita'  -> depth {expected}px  OK")


def test_colors_in_screen_order():
    """Zona 'reversed': i colori nello snapshot sono in ordine di schermo,
    quindi il segmento a sinistra dello schermo e' il primo."""
    svc = _service(depth=3)
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:, : W // 4, 2] = 255            # quarto sinistro: rosso (BGR -> canale 2)
    svc._process_frame(frame, svc._config)
    top = svc.get_sampling_snapshot()["zones"][0]["colors"]
    assert top[:6] == "ff0000", top        # primo segmento a sinistra = rosso
    assert top[6:] == "000000" * 3, top
    print("  ordine colori (schermo) -> primo segmento rosso  OK")


def test_legacy_hsv_strategy_falls_back_to_mean():
    """'hsv' was removed (it needed OpenCV, which is not installed): an old
    config that still names it must keep working, not stop the service."""
    svc = _service(depth=3, strategy="hsv")
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:, :, 2] = 200                       # solid red (BGR channel 2)
    svc._process_frame(frame, svc._config)
    top = svc.get_sampling_snapshot()["zones"][0]["colors"]
    assert top[:6] == "c80000", top            # sat_boost 1.0: color untouched
    print("  strategy 'hsv' legacy  -> mean fallback  OK")


def test_content_rect_in_snapshot():
    svc = _service(depth=3, black_bar=True)
    bar = int(W * 0.25)
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:, bar:W - bar] = 200
    cfg = dict(svc._config, bb_consistent=1, bb_interval=0.0)
    svc._process_frame(frame, cfg)
    snap = svc.get_sampling_snapshot()
    x0, y0, x1, y1 = snap["rect"]
    assert abs(x0 - bar) < 40 and abs(x1 - (W - bar)) < 40, snap["rect"]
    # la profondita' e' relativa all'area utile (1720x1440 -> lato corto 1440)
    assert snap["depth"]["top"] == int(min(y1 - y0, x1 - x0) * 0.03)
    print(f"  content rect          -> {snap['rect']}  OK")


if __name__ == "__main__":
    print("test_sampling_snapshot:")
    test_geometry_and_depth()
    test_colors_in_screen_order()
    test_legacy_hsv_strategy_falls_back_to_mean()
    test_content_rect_in_snapshot()
    print("ALL OK")


def test_preview_is_built_only_while_a_page_asks_for_it():
    import time
    svc = AmbilightService(None)
    svc._config = {"enabled": True, "strategy": "mean", "depth": 10, "saturation_boost": 1.0,
                   "min_luminance": 0, "black_bar_detect": False, "devices": {}}
    frame = np.full((H, W, 3), 128, dtype=np.uint8)
    svc._process_frame(frame, svc._config)
    assert svc._sampling is None                 # nobody asked: nothing built
    assert svc.get_sampling_snapshot() is None   # a page asks...
    svc._process_frame(frame, svc._config)
    assert svc.get_sampling_snapshot() is not None   # ...and gets it from the next frame
    svc._preview_until = time.monotonic() - 1    # the page went away
    old = svc._sampling_ts
    svc._process_frame(frame, svc._config)
    assert svc._sampling_ts == old               # not built any more


def test_timings_are_reported():
    svc = AmbilightService(None)
    t = svc.timings
    assert set(t) >= {"grab_ms", "process_ms", "write_ms", "accent_ms_per_s", "accent_writes_per_s"}
