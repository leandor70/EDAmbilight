"""Effetti LED mentre lo schermo non e' disponibile (standby, lock screen).

Funzioni pure: render() riceve gli ultimi colori inviati (base), la maschera dei
LED appartenenti a zone attive e il tempo trascorso, e ritorna i nuovi colori.
"""

import math
from typing import List, Optional, Tuple

import numpy as np

# (id, etichetta UI) — l'ordine e' quello del selettore in index.html
MODES = (
    ("hold",    "Hold last colors"),
    ("fade",    "Slow fade to black"),
    ("dim",     "Fade to dim glow"),
    ("pulse",   "Pulse (breathing)"),
    ("rainbow", "Rotating colors"),
    ("aurora",  "Aurora"),
    ("ember",   "Ember glow"),
    ("off",     "Lights off"),
)
MODE_IDS = tuple(m[0] for m in MODES)

FADE_SECS  = 20.0    # durata di fade / dim
DIM_LEVEL  = 0.15    # luminosita' finale di "dim"
PULSE_SECS = 5.0     # periodo del respiro
PULSE_MIN  = 0.12    # luminosita' minima del respiro
PULSE_FALLBACK = (20.0, 245.0, 255.0)   # ciano: se l'ultima scena era quasi nera

Color = Tuple[int, int, int]


def is_static(mode: str, t: float) -> bool:
    """True quando l'effetto ha smesso di cambiare: basta riscrivere di rado."""
    if mode == "off":
        return True
    return mode in ("fade", "dim") and t >= FADE_SECS


def _hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    """h, s, v in [0,1], stessa shape (N,) -> (N,3) in 0..255."""
    h6 = (h % 1.0) * 6.0
    i  = np.floor(h6).astype(int) % 6
    f  = h6 - np.floor(h6)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=1) * 255.0


def _pulse(base: np.ndarray, mask: np.ndarray, t: float) -> np.ndarray:
    if not mask.any() or base[mask].max() < 8:
        base = np.where(mask[:, None], np.array(PULSE_FALLBACK), 0.0)
    wave = 0.5 + 0.5 * math.cos(2 * math.pi * t / PULSE_SECS)   # 1 -> 0 -> 1, parte da pieno
    return base * (PULSE_MIN + (1.0 - PULSE_MIN) * wave)


def _rainbow(n: int, t: float, level: float) -> np.ndarray:
    pos = np.arange(n) / max(1, n)
    return _hsv_to_rgb(pos + t / 30.0, np.full(n, 1.0), np.full(n, level))


def _aurora(n: int, t: float, level: float) -> np.ndarray:
    pos = np.arange(n) / max(1, n)
    hue = 0.62 + 0.18 * np.sin(2 * math.pi * (pos * 1.5 - t / 12.0))    # verde-ciano <-> viola
    val = level * (0.65 + 0.35 * np.sin(2 * math.pi * (pos * 2.0 + t / 9.0)))
    return _hsv_to_rgb(hue, np.full(n, 0.85), val)


def _ember(n: int, t: float, level: float) -> np.ndarray:
    idx   = np.arange(n)
    flick = (0.6 + 0.25 * np.sin(t * 1.3 + idx * 0.9)
                 + 0.15 * np.sin(t * 2.9 + idx * 2.3))
    hue   = 0.03 + 0.02 * np.sin(t * 0.7 + idx * 0.5)                   # arancio-rosso
    return _hsv_to_rgb(hue, np.full(n, 1.0), level * flick)


def render(mode: str, t: float, base: np.ndarray, mask: np.ndarray,
           brightness: float = 0.6) -> Optional[List[Color]]:
    """Colori per un device, o None se la modalita' non scrive nulla (hold).

    t          secondi dall'inizio dello standby
    base       (N,3) ultimi colori inviati
    mask       (N,)  bool, LED di zone attive: gli altri restano spenti
    brightness 0..1, solo per gli effetti generativi (rainbow/aurora/ember)
    """
    n     = len(base)
    level = max(0.0, min(1.0, brightness))

    if mode == "fade":
        x   = min(1.0, max(0.0, t / FADE_SECS))
        out = base * (1.0 - x) ** 2
    elif mode == "dim":
        x   = min(1.0, max(0.0, t / FADE_SECS))
        out = base * (DIM_LEVEL + (1.0 - DIM_LEVEL) * (1.0 - x) ** 2)
    elif mode == "pulse":
        out = _pulse(base, mask, t)
    elif mode == "rainbow":
        out = _rainbow(n, t, level)
    elif mode == "aurora":
        out = _aurora(n, t, level)
    elif mode == "ember":
        out = _ember(n, t, level)
    elif mode == "off":
        out = np.zeros((n, 3))
    else:
        return None

    out = np.where(mask[:, None], out, 0.0)
    out = np.clip(np.rint(out), 0, 255).astype(int)
    return [(int(r), int(g), int(b)) for r, g, b in out]
