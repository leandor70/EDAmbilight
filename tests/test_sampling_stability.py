"""Sampling stability of the percentile strategies (_sample_segment).

Bug fixed: the percentile strategies took the ONE pixel at the 80th luminance
percentile. On dark content with coloured text (a chat, an IDE) a blinking
cursor moved that choice onto a pixel of another colour: the LED jumped by up to
225/255 between frames. Now the mean of the brightest 20% is used.

Synthetic BGR frames, no capture and no hardware. Ported from ED:Event2Led
(tools/test_ambilight_sampling.py).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from effects.ambilight_service import _boost_saturation, _sample_segment  # noqa: E402

PALETTE = np.array([[53, 107, 255], [80, 200, 120], [230, 230, 230],
                    [255, 170, 60], [90, 90, 220], [200, 120, 200]], np.uint8)   # BGR


def _text_segment(rng, h=108, w=160):
    """Dark background with words of coloured text (one top-edge LED segment at 1080p)."""
    seg = np.full((h, w, 3), 30, np.uint8)
    cover = rng.uniform(0.08, 0.35)
    for row in range(0, h, 14):
        x = 0
        while x < w:
            n = int(rng.integers(3, 30))
            if rng.random() < cover * 2.2:
                seg[row:row + 9, x:x + n] = PALETTE[rng.integers(len(PALETTE))]
            x += n + int(rng.integers(3, 9))
    return seg


def _led(seg, strategy):
    return np.array(_boost_saturation([_sample_segment(seg, strategy)], 1.4)[0], float)


@pytest.mark.parametrize("strategy", ["adaptive_smooth", "smooth", "percentile", "adaptive"])
def test_a_blinking_cursor_does_not_make_the_led_jump(strategy):
    rng = np.random.default_rng(11)
    worst = 0.0
    for _ in range(300):
        seg = _text_segment(rng)
        on = seg.copy()
        cy, cx = rng.integers(0, seg.shape[0] - 16), rng.integers(0, seg.shape[1] - 8)
        on[cy:cy + 16, cx:cx + 8] = 240                      # cursor block
        worst = max(worst, np.abs(_led(on, strategy) - _led(seg, strategy)).max())
    assert worst <= 20, f"{strategy}: the LED moves by {worst:.1f}/255 (was up to 225)"


def test_bright_colours_still_win_over_a_dark_background():
    seg = np.full((100, 100, 3), 10, np.uint8)
    seg[:25] = (53, 107, 255)                                # 25% orange (BGR)
    assert _sample_segment(seg, "percentile") == (255, 107, 53)


def test_a_little_colour_is_dimmer_but_keeps_its_hue():
    seg = np.full((100, 100, 3), 10, np.uint8)
    seg[:10] = (53, 107, 255)                                # 10% orange
    r, g, b = _sample_segment(seg, "percentile")
    assert r > g > b and r >= 120


def test_empty_and_one_pixel_segments():
    assert _sample_segment(np.zeros((0, 3), np.uint8), "percentile") == (0, 0, 0)
    assert _sample_segment(np.full((1, 1, 3), 7, np.uint8), "percentile") == (7, 7, 7)
