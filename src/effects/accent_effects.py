"""Accento sul battito audio: luminosita' e spostamento di colore sopra l'ambilight.

Funzioni pure + un piccolo stato (limite, inviluppo, spostamento di colore a
passi). render() riceve i colori base (gia' campionati dallo schermo), la
maschera dei LED appartenenti a zone attive e i livelli correnti, e ritorna i
nuovi colori. Niente I/O: tutto testabile senza audio ne' hardware.
"""

import math
import threading
import time
from typing import Optional, Tuple

import numpy as np

from effects.standby_effects import _hsv_to_rgb

# Valori usati quando la chiave manca da ambilight_config.json (nessuna migrazione)
DEFAULTS = {
    "accent_enabled":      False,
    "accent_device":       "",          # nome del dispositivo loopback, "" = predefinito
    "accent_sensitivity":  50,          # 0-100
    "accent_min_strength": 40,          # 0-100: 0 = ogni battito, 100 = solo i piu' forti
    "accent_mode":         "mix",       # mul | add | mix
    "accent_intensity":    25,          # % di aumento al battito (0-200)
    "accent_duration":     200,         # ms di decadimento (80-600)
    "accent_color":        "#ffffff",   # colore del flash (add / mix)
    "accent_dark_lift":    20,          # % di quota additiva nel misto (0-100)
    "accent_hue_mode":     "off",       # off | pulse | step
    "accent_hue_deg":      40,          # gradi di rotazione della tinta (0-180)
    "accent_hue_decay":    1500,        # ms: ritorno lento dello spostamento a passi
    "accent_max_per_sec":  3,           # limite lampi al secondo (0 = nessun limite)
    "accent_max_boost":    100,         # tetto dell'intensita' applicata, % (20-300)
    "accent_attack":       15,          # ms di salita (0 = istantaneo)
}

# Forza minima che il rilevatore assegna a un battito (vedi beat_detector): la scala
# di "solo battiti forti" va da qui (accetta tutto) a 1.0 (solo i piu' forti).
MIN_BEAT_STRENGTH = 0.35

MODES     = ("mul", "add", "mix")
HUE_MODES = ("off", "pulse", "step")

# Sotto questa soglia l'accento e' considerato finito (inviluppo ~ 1%)
_ACTIVE_EPS = 0.004
_HUE_EPS    = 0.5      # gradi


def _num(cfg: dict, key: str, lo: float, hi: float) -> float:
    try:
        v = float(cfg.get(key, DEFAULTS[key]))
    except (TypeError, ValueError):
        v = float(DEFAULTS[key])
    if v != v:                       # NaN
        v = float(DEFAULTS[key])
    return max(lo, min(hi, v))


def _color(value) -> np.ndarray:
    """'#rrggbb' -> array (3,) 0..255; bianco se il valore non e' valido."""
    try:
        s = str(value).strip().lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) != 6:
            raise ValueError
        return np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)
    except (ValueError, TypeError):
        return np.array([255.0, 255.0, 255.0], dtype=np.float32)


def params_from_cfg(cfg: dict) -> dict:
    """Parametri normalizzati e limitati, con i default per le chiavi mancanti."""
    mode = cfg.get("accent_mode", DEFAULTS["accent_mode"])
    hue_mode = cfg.get("accent_hue_mode", DEFAULTS["accent_hue_mode"])
    return {
        "enabled":     bool(cfg.get("accent_enabled", DEFAULTS["accent_enabled"])),
        "device":      str(cfg.get("accent_device", DEFAULTS["accent_device"]) or ""),
        "sensitivity": _num(cfg, "accent_sensitivity", 0, 100),
        "min_strength": _num(cfg, "accent_min_strength", 0, 100) / 100.0,
        "mode":        mode if mode in MODES else DEFAULTS["accent_mode"],
        "intensity":   _num(cfg, "accent_intensity", 0, 200) / 100.0,
        "duration_ms": _num(cfg, "accent_duration", 20, 2000),
        "color":       _color(cfg.get("accent_color", DEFAULTS["accent_color"])),
        "dark_lift":   _num(cfg, "accent_dark_lift", 0, 100) / 100.0,
        "hue_mode":    hue_mode if hue_mode in HUE_MODES else DEFAULTS["accent_hue_mode"],
        "hue_deg":     _num(cfg, "accent_hue_deg", 0, 180),
        "hue_decay_ms": _num(cfg, "accent_hue_decay", 100, 10000),
        "max_per_sec": _num(cfg, "accent_max_per_sec", 0, 20),
        "max_boost":   _num(cfg, "accent_max_boost", 0, 300) / 100.0,
        "attack_ms":   _num(cfg, "accent_attack", 0, 100),
    }


def strength_threshold(p: dict) -> float:
    """Forza minima di un battito per far partire l'accento (0.35 .. 1.0)."""
    return MIN_BEAT_STRENGTH + (1.0 - MIN_BEAT_STRENGTH) * p["min_strength"]


class AccentState:
    """Ultimo battito accettato: inviluppo, limite di frequenza, tinta a passi.

    Thread-safe: trigger() arriva dal thread audio o dall'API, levels() dal
    ciclo dell'ambilight.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._t0: Optional[float] = None
        self._strength = 0.0
        self._last_accept: Optional[float] = None
        self._hue_off = 0.0
        self._hue_t = 0.0

    def trigger(self, strength: float, p: dict, now: Optional[float] = None) -> bool:
        """Registra un battito. False se troppo debole o scartato dal limite di frequenza.

        I battiti deboli si scartano prima del limite: non lo consumano, cosi' un
        battito forte subito dopo non viene perso.
        """
        now = time.monotonic() if now is None else now
        if float(strength) < strength_threshold(p) - 1e-9:
            return False
        with self._lock:
            n = p["max_per_sec"]
            if n > 0 and self._last_accept is not None and now - self._last_accept < 1.0 / n:
                return False
            self._last_accept = now
            self._t0 = now
            self._strength = max(0.0, min(1.0, float(strength)))
            if p["hue_mode"] == "step":
                cur = self._hue_at(now, p)
                self._hue_off = min(360.0, cur + p["hue_deg"])
                self._hue_t = now
            return True

    def _hue_at(self, now: float, p: dict) -> float:
        if self._hue_off <= 0:
            return 0.0
        return self._hue_off * math.exp(-(now - self._hue_t) * 1000.0 / p["hue_decay_ms"])

    def _envelope(self, now: float, p: dict) -> float:
        if self._t0 is None:
            return 0.0
        dt = (now - self._t0) * 1000.0
        a = p["attack_ms"]
        if a > 0 and dt < a:
            return dt / a
        return math.exp(-(dt - a) / max(1.0, p["duration_ms"]))

    def levels(self, now: float, p: dict) -> Tuple[float, float]:
        """(k, tinta): k = aumento corrente (0 = nessuno), tinta in gradi."""
        with self._lock:
            e = self._envelope(now, p)
            k = min(p["intensity"], p["max_boost"]) * self._strength * e
            if p["hue_mode"] == "pulse":
                hue = p["hue_deg"] * self._strength * e
            elif p["hue_mode"] == "step":
                hue = self._hue_at(now, p)
            else:
                hue = 0.0
        return k, hue

    @staticmethod
    def is_active(k: float, hue: float) -> bool:
        return k > _ACTIVE_EPS or abs(hue) > _HUE_EPS


def _rotate_hue(rgb: np.ndarray, deg: float) -> np.ndarray:
    """Ruota la tinta di `deg` gradi. rgb (N,3) 0..255. Grigi e neri restano uguali."""
    x = rgb / 255.0
    r, g, b = x[:, 0], x[:, 1], x[:, 2]
    mx = x.max(axis=1)
    d = mx - x.min(axis=1)
    safe = np.where(d > 1e-9, d, 1.0)
    h = np.where(mx == r, ((g - b) / safe) % 6.0,
        np.where(mx == g, (b - r) / safe + 2.0, (r - g) / safe + 4.0)) / 6.0
    h = np.where(d > 1e-9, h, 0.0)
    s = np.where(mx > 0, d / np.where(mx > 0, mx, 1.0), 0.0)
    return _hsv_to_rgb(h + deg / 360.0, s, mx)


def render(base: np.ndarray, mask: np.ndarray, k: float, hue_deg: float, p: dict) -> np.ndarray:
    """Applica tinta e luminosita' ai LED della maschera. base (N,3) 0..255.

    Ordine: prima la tinta (un nero resta nero), poi la luminosita'. Se un canale
    supera 255 i tre canali vengono ridotti in proporzione: la tinta si conserva
    (un taglio canale per canale spingerebbe il colore verso il bianco).
    """
    out = np.asarray(base, dtype=np.float32)
    if not mask.any() or (k <= 0 and abs(hue_deg) < 0.01):
        return out
    out = out.copy()
    sel = out[mask]

    if abs(hue_deg) >= 0.01:
        sel = _rotate_hue(sel, hue_deg)

    if k > 0:
        flash = p["color"]
        mode = p["mode"]
        if mode == "mul":
            sel = sel * (1.0 + k)
        elif mode == "add":
            sel = sel + flash * k
        else:
            m = p["dark_lift"]
            sel = sel * (1.0 + k * (1.0 - m)) + flash * (k * m)

    peak = sel.max(axis=1, keepdims=True)
    sel = np.where(peak > 255.0, sel * (255.0 / np.maximum(peak, 1e-6)), sel)
    out[mask] = np.clip(sel, 0.0, 255.0)
    return out


def to_colors(arr: np.ndarray):
    """(N,3) float -> lista di tuple (r, g, b) intere, come si aspettano i device."""
    return [tuple(c) for c in np.rint(arr).astype(int).tolist()]
