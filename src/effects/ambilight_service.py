"""AmbilightService — idle background loop per ambilight standalone.

Campiona lo schermo e invia i colori ai device configurati.
Adattato da EDLogReader: rimossa la dipendenza da is_effect_playing()
(non ci sono altri effetti in questo sottoprogetto).
"""

import json
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import numpy as np

from core.screen_capturer_service import ScreenCapturerService
from effects import standby_effects

CONFIG_PATH = Path("config/ambilight_config.json")

# Secondi senza frame prima di considerare lo schermo in standby (i buchi brevi,
# es. avvio o cambio capturer, non devono far partire gli effetti).
STANDBY_GRACE = 3.0
# Durata massima dell'anteprima manuale dello standby (s)
STANDBY_PREVIEW_MAX = 60.0

# Zone name -> screen edge mapping
_ZONE_SCREEN_MAP = {
    "MonitorRight":  {"edge": "right",  "reversed": False},
    "MonitorTop":    {"edge": "top",    "reversed": True},
    "MonitorLeft":   {"edge": "left",   "reversed": True},
    "MonitorBottom": {"edge": "bottom", "reversed": False},
    "Desktop":       {"edge": "bottom", "reversed": False},
}


# ── Sampling helpers ──────────────────────────────────────────────────────────


def _led_world_positions(zone: dict) -> List[Tuple[float, float]]:
    x0      = zone["position"]["x"]
    y0      = zone["position"]["y"]
    spacing = zone.get("led_spacing", 1.0)
    rot     = zone.get("rotation", 0)
    dx = {0: spacing, 90: 0, 180: -spacing, 270: 0      }.get(rot, spacing)
    dy = {0: 0,       90: spacing, 180: 0,  270: -spacing}.get(rot, 0)
    return [(x0 + i * dx, y0 + i * dy) for i in range(zone["led_count"])]


def _sample_segment(seg_2d: np.ndarray, strategy: str) -> Tuple[int, int, int]:
    pixels = seg_2d.reshape(-1, 3)
    if len(pixels) == 0:
        return (0, 0, 0)

    if strategy in ("percentile", "smooth", "adaptive", "adaptive_smooth"):
        lums = 0.2126 * pixels[:, 2] + 0.7152 * pixels[:, 1] + 0.0722 * pixels[:, 0]
        k    = int(len(lums) * 0.80)
        idx  = np.argpartition(lums, k)[k]
        bgr  = pixels[idx]
    elif strategy == "dominant":
        bgr = np.median(pixels, axis=0)
    else:  # mean
        bgr = pixels.mean(axis=0)

    return (int(bgr[2]), int(bgr[1]), int(bgr[0]))


def _adaptive_depth(
    frame: np.ndarray,
    edge: str,
    screen_start: float,
    screen_end: float,
    min_pct: float,
    max_pct: float,
) -> float:
    h, w  = frame.shape[:2]
    probe = max(1, int(min(h, w) * 0.03))
    if edge in ("top", "bottom"):
        x0, x1 = int(w * screen_start), max(int(w * screen_start) + 1, int(w * screen_end))
        outer   = frame[:probe, x0:x1, :] if edge == "top" else frame[-probe:, x0:x1, :]
    else:
        y0, y1 = int(h * screen_start), max(int(h * screen_start) + 1, int(h * screen_end))
        outer   = frame[y0:y1, :probe, :] if edge == "left" else frame[y0:y1, -probe:, :]
    norm = min(1.0, float(outer.std()) / 80.0)
    return max_pct - norm * (max_pct - min_pct)


def _apply_temporal_smooth(
    prev_map: Dict[str, List[Tuple[int, int, int]]],
    zone_key: str,
    new_colors: List[Tuple[int, int, int]],
    alpha: float,
    cut_threshold: float,
) -> List[Tuple[int, int, int]]:
    prev = prev_map.get(zone_key)
    if prev is None or len(prev) != len(new_colors):
        prev_map[zone_key] = new_colors
        return new_colors

    avg_delta = sum(
        (abs(n[0] - p[0]) + abs(n[1] - p[1]) + abs(n[2] - p[2])) / 3
        for n, p in zip(new_colors, prev)
    ) / len(new_colors)

    if avg_delta > cut_threshold:
        result = new_colors
    else:
        result = [
            (
                min(255, max(0, int(p[0] + alpha * (n[0] - p[0])))),
                min(255, max(0, int(p[1] + alpha * (n[1] - p[1])))),
                min(255, max(0, int(p[2] + alpha * (n[2] - p[2])))),
            )
            for n, p in zip(new_colors, prev)
        ]

    prev_map[zone_key] = result
    return result


def _boost_saturation(
    colors: List[Tuple[int, int, int]],
    factor: float,
) -> List[Tuple[int, int, int]]:
    result = []
    for r, g, b in colors:
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        result.append((
            min(255, max(0, int(lum + (r - lum) * factor))),
            min(255, max(0, int(lum + (g - lum) * factor))),
            min(255, max(0, int(lum + (b - lum) * factor))),
        ))
    return result


_MIN_LUM_BLACK = 4   # sotto questo valore (max canale) il colore è nero vero: resta spento


def _hex_colors(colors: List[Tuple[int, int, int]]) -> str:
    """Colori compattati in una stringa 'rrggbbrrggbb…' (6 caratteri per LED)."""
    return "".join(f"{r:02x}{g:02x}{b:02x}" for r, g, b in colors)


def _apply_min_luminance(
    colors: List[Tuple[int, int, int]],
    floor: float,
) -> List[Tuple[int, int, int]]:
    """Alza i colori più scuri di `floor` (0-255) fino a quella luminosità.

    Scala i tre canali in proporzione, quindi la tinta non cambia. Il nero
    vero (max canale < _MIN_LUM_BLACK) non viene toccato: così le scene
    davvero nere continuano a spegnere i LED.
    """
    if floor <= 0:
        return colors
    result = []
    for r, g, b in colors:
        peak = max(r, g, b)
        if _MIN_LUM_BLACK <= peak < floor:
            k = floor / peak
            r, g, b = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)))
        result.append((r, g, b))
    return result


def _sample_area_point(
    frame: np.ndarray,
    x_pct: float,
    y_pct: float,
    strategy: str,
    radius_pct: float = 0.18,
) -> Tuple[int, int, int]:
    """Sample a screen area at (x_pct, y_pct) in [0,1]x[0,1] coordinates."""
    h, w = frame.shape[:2]
    cx = int(w * x_pct)
    cy = int(h * y_pct)
    r  = max(1, int(min(h, w) * radius_pct))
    x0, x1 = max(0, cx - r), min(w, cx + r)
    y0, y1 = max(0, cy - r), min(h, cy + r)
    patch = frame[y0:y1, x0:x1, :3].astype(np.float32)
    # No HSV conversion for area patches — use brightness-based percentile
    eff = "adaptive_smooth" if strategy in ("hsv", "adaptive", "adaptive_smooth") else strategy
    return _sample_segment(patch, eff)


# ── Black-border detection ────────────────────────────────────────────────────

_BB_STEP     = 8      # passo di sottocampionamento del probe
_BB_MIN_FRAC = 0.02   # quota di pixel luminosi perché una riga/colonna sia "contenuto"
_BB_MIN_SIZE = 0.30   # il rettangolo deve coprire almeno questa frazione per lato


def _detect_content_rect(frame: np.ndarray, threshold: int) -> Optional[Tuple[int, int, int, int]]:
    """Rettangolo (x0, y0, x1, y1) del contenuto escludendo le bande nere.

    Lavora su un probe sottocampionato (1 pixel ogni _BB_STEP): su un frame
    3440x1440 legge ~77k pixel, costo trascurabile. Ritorna None se il frame
    è troppo scuro per decidere (es. dissolvenza): in quel caso il chiamante
    mantiene lo stato corrente.
    """
    h, w   = frame.shape[:2]
    small  = frame[::_BB_STEP, ::_BB_STEP, :3]
    bright = small.max(axis=2) > threshold
    rows   = bright.mean(axis=1)
    cols   = bright.mean(axis=0)

    row_idx = np.flatnonzero(rows > _BB_MIN_FRAC)
    col_idx = np.flatnonzero(cols > _BB_MIN_FRAC)
    if len(row_idx) == 0 or len(col_idx) == 0:
        return None

    y0 = int(row_idx[0] * _BB_STEP)
    y1 = min(h, int((row_idx[-1] + 1) * _BB_STEP))
    x0 = int(col_idx[0] * _BB_STEP)
    x1 = min(w, int((col_idx[-1] + 1) * _BB_STEP))

    if (x1 - x0) < w * _BB_MIN_SIZE or (y1 - y0) < h * _BB_MIN_SIZE:
        return None   # troppo piccolo: scena scura, non bande
    return (x0, y0, x1, y1)


def _extract_edge_strip(
    frame: np.ndarray,
    edge: str,
    depth_pct: float,
    strategy: str,
    cfg: dict,
    edge_cache: Dict[str, np.ndarray],
) -> np.ndarray:
    """Striscia di bordo a tutta larghezza/altezza, già convertita (float32/HSV).

    Cache per-frame condivisa tra device/zone: ritaglio, profondità adattiva
    e astype vengono fatti una sola volta per bordo.
    """
    cached = edge_cache.get(edge)
    if cached is not None:
        return cached

    h, w = frame.shape[:2]

    if strategy in ("adaptive", "adaptive_smooth"):
        depth_pct = _adaptive_depth(
            frame, edge, 0.0, 1.0,
            min_pct=cfg.get("adaptive_min", 3.0) / 100.0,
            max_pct=cfg.get("adaptive_max", 20.0) / 100.0,
        )

    depth = max(1, int(min(h, w) * depth_pct))

    if edge == "top":
        strip = frame[:depth, :, :]
    elif edge == "bottom":
        strip = frame[-depth:, :, :]
    elif edge == "left":
        strip = frame[:, :depth, :]
    else:
        strip = frame[:, -depth:, :]

    if strategy == "hsv":
        import cv2
        strip_proc = cv2.cvtColor(
            np.ascontiguousarray(strip), cv2.COLOR_BGR2HSV
        ).astype(np.float32)
    else:
        strip_proc = strip.astype(np.float32)

    edge_cache[edge] = strip_proc
    return strip_proc


def _sample_edge(
    frame: np.ndarray,
    edge: str,
    led_count: int,
    reversed_dir: bool,
    depth_pct: float,
    screen_start: float,
    screen_end: float,
    strategy: str,
    zone_key: str,
    prev_map: Dict,
    cfg: dict,
    edge_cache: Dict[str, np.ndarray],
) -> List[Tuple[int, int, int]]:
    h, w = frame.shape[:2]
    strip_proc = _extract_edge_strip(frame, edge, depth_pct, strategy, cfg, edge_cache)

    if edge in ("top", "bottom"):
        x0   = int(w * screen_start)
        x1   = max(x0 + 1, int(w * screen_end))
        span = strip_proc[:, x0:x1, :]
        axis = 1
    else:
        y0   = int(h * screen_start)
        y1   = max(y0 + 1, int(h * screen_end))
        span = strip_proc[y0:y1, :, :]
        axis = 0

    segs   = np.array_split(span, led_count, axis=axis)
    colors = [_sample_segment(seg, strategy) for seg in segs]

    if strategy in ("smooth", "adaptive_smooth") and zone_key:
        colors = _apply_temporal_smooth(
            prev_map, zone_key, colors,
            alpha=cfg.get("ema_alpha", 0.35),
            cut_threshold=cfg.get("scene_cut", 60.0),
        )

    return colors[::-1] if reversed_dir else colors


# ── Zone discovery ────────────────────────────────────────────────────────────


def _is_unreadable_name(name: str) -> bool:
    """OpenRGB hands over some zone names as '???' (non-Latin chars lost upstream).

    Such zones can't be told apart or identified by the user, so they are left out.
    """
    return not name.strip().strip("?")


def is_zone_enabled(zones_enabled: dict, zone: dict) -> bool:
    """Zones are keyed by zone_index (names can repeat or be unreadable).

    Falls back to the legacy name key written by older versions.
    """
    idx_key = str(zone.get("zone_index"))
    if idx_key in zones_enabled:
        return bool(zones_enabled[idx_key])
    return bool(zones_enabled.get(zone.get("name", ""), True))


def build_device_zones(device_key: str) -> Tuple[List[dict], int]:
    """Load zone sampling parameters for a device from device_topologies.json."""
    try:
        data = json.loads(Path("config/device_topologies.json").read_text(encoding="utf-8"))
    except Exception:
        return [], 0

    topology = data.get("topologies", {}).get(device_key)
    if not topology:
        return [], 0

    all_zones = sorted(topology.get("zones", []), key=lambda z: z["zone_index"])
    if not all_zones:
        return [], 0

    zone_offsets: List[int] = []
    off = 0
    for zone in all_zones:
        zone_offsets.append(off)
        off += zone["led_count"]
    total_leds = off

    frame_zones = [z for z in all_zones if z.get("name", "").startswith("Monitor")]
    if frame_zones:
        all_pts   = [pt for z in frame_zones for pt in _led_world_positions(z)]
        mon_x_min = min(p[0] for p in all_pts)
        mon_x_max = max(p[0] for p in all_pts)
        mon_y_min = min(p[1] for p in all_pts)
        mon_y_max = max(p[1] for p in all_pts)
    else:
        mon_x_min, mon_x_max, mon_y_min, mon_y_max = 0.0, 100.0, 0.0, 100.0

    result: List[dict] = []
    for z_idx, zone in enumerate(all_zones):
        name = zone.get("name", "")
        if name not in _ZONE_SCREEN_MAP:
            continue

        mapping  = _ZONE_SCREEN_MAP[name]
        edge     = mapping["edge"]
        spacing  = zone.get("led_spacing", 1.0)
        led_pts  = _led_world_positions(zone)

        if edge in ("top", "bottom"):
            in_range = [(i, x, y) for i, (x, y) in enumerate(led_pts)
                        if mon_x_min <= x <= mon_x_max]
            if not in_range:
                in_range = [(i, x, y) for i, (x, y) in enumerate(led_pts)]
            xs           = [x for _, x, _ in in_range]
            x_lo, x_hi   = min(xs), max(xs)
            mon_span     = max(0.001, mon_x_max - mon_x_min)
            screen_start = max(0.0, (x_lo - spacing / 2 - mon_x_min) / mon_span)
            screen_end   = min(1.0, (x_hi + spacing / 2 - mon_x_min) / mon_span)
        else:
            in_range = [(i, x, y) for i, (x, y) in enumerate(led_pts)
                        if mon_y_min <= y <= mon_y_max]
            if not in_range:
                in_range = [(i, x, y) for i, (x, y) in enumerate(led_pts)]
            ys           = [y for _, _, y in in_range]
            y_lo, y_hi   = min(ys), max(ys)
            mon_span     = max(0.001, mon_y_max - mon_y_min)
            screen_start = max(0.0, (y_lo - spacing / 2 - mon_y_min) / mon_span)
            screen_end   = min(1.0, (y_hi + spacing / 2 - mon_y_min) / mon_span)

        led_start = in_range[0][0]
        led_end   = in_range[-1][0] + 1

        result.append({
            "name":         name,
            "zone_index":   zone["zone_index"],
            "led_count":    zone["led_count"],
            "led_offset":   zone_offsets[z_idx],
            "led_start":    led_start,
            "led_end":      led_end,
            "screen_start": screen_start,
            "screen_end":   screen_end,
            "edge":         edge,
            "reversed":     mapping["reversed"],
        })

    # Non-Monitor zones: sample screen area proportional to canvas position.
    # Use global scene bounds (all devices) so positions are consistent.
    all_scene_pts = [
        pt
        for _, topo in data.get("topologies", {}).items()
        for z in topo.get("zones", [])
        for pt in _led_world_positions(z)
    ]
    if all_scene_pts:
        scene_x_min = min(p[0] for p in all_scene_pts)
        scene_x_max = max(p[0] for p in all_scene_pts)
        scene_y_min = min(p[1] for p in all_scene_pts)
        scene_y_max = max(p[1] for p in all_scene_pts)
    else:
        scene_x_min, scene_x_max, scene_y_min, scene_y_max = 0.0, 100.0, 0.0, 100.0

    span_x = max(0.001, scene_x_max - scene_x_min)
    span_y = max(0.001, scene_y_max - scene_y_min)

    for z_idx, zone in enumerate(all_zones):
        name = zone.get("name", "")
        if name in _ZONE_SCREEN_MAP or _is_unreadable_name(name):
            continue

        led_pts = _led_world_positions(zone)
        if not led_pts:
            continue

        x_avg = sum(p[0] for p in led_pts) / len(led_pts)
        y_avg = sum(p[1] for p in led_pts) / len(led_pts)

        result.append({
            "name":         name,
            "zone_index":   zone["zone_index"],
            "led_count":    zone["led_count"],
            "led_offset":   zone_offsets[z_idx],
            "led_start":    0,
            "led_end":      zone["led_count"],
            "screen_start": 0.0,
            "screen_end":   1.0,
            "edge":         "area",
            "x_pct":        max(0.0, min(1.0, (x_avg - scene_x_min) / span_x)),
            "y_pct":        max(0.0, min(1.0, (y_avg - scene_y_min) / span_y)),
            "reversed":     False,
        })

    return result, total_leds


# ── Service ───────────────────────────────────────────────────────────────────


class AmbilightService:
    """
    Servizio ambilight standalone: campiona lo schermo e invia i colori
    ai device configurati via OpenRGBManager.
    """

    def __init__(self, openrgb_manager) -> None:
        self._manager = openrgb_manager
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._config: dict = self._load_config()
        self._prev_colors: Dict[str, List[Tuple[int, int, int]]] = {}
        self._actual_fps: float = 0.0
        self._paused: bool = False
        self._zone_cache: Dict[str, Tuple[List[dict], int]] = {}
        self._topology_warned: set = set()
        # Standby (schermo non disponibile): ultimi colori + maschera LED attivi
        # per device, e istanti di inizio dell'assenza di frame / dello standby.
        self._standby_ctx: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        self._no_frame_since: Optional[float] = None
        self._standby_since:  Optional[float] = None
        self._standby_last_write: float = 0.0
        # Anteprima manuale dello standby: monotonic() di scadenza (0 = spenta)
        self._standby_preview_until: float = 0.0
        # Black-border detection: None = schermo intero
        self._bb_rect:        Optional[Tuple[int, int, int, int]] = None
        self._bb_candidate:   Optional[Tuple[int, int, int, int]] = None
        self._bb_count:       int = 0
        self._bb_last_check:  float = 0.0
        self._bb_frame_shape: Optional[Tuple[int, int]] = None
        # Ultimo snapshot della campionatura (geometria + colori), per l'anteprima UI
        self._sampling: Optional[dict] = None
        self._sampling_ts: float = 0.0

    # ── Config ────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_config() -> dict:
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {
                "version": 1, "enabled": False, "capturer": "auto",
                "fps": 15, "strategy": "adaptive_smooth",
                "depth": 10, "saturation_boost": 1.4, "min_luminance": 0,
                "ema_alpha": 0.35, "scene_cut": 60,
                "adaptive_min": 3, "adaptive_max": 20,
                "black_bar_detect": True, "bb_interval": 1.0,
                "bb_threshold": 18, "bb_consistent": 3,
                "standby_mode": "hold", "standby_brightness": 60,
                "devices": {},
            }

    @staticmethod
    def _save_config(cfg: dict) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get_config(self) -> dict:
        return dict(self._config)

    def set_config(self, updates: dict) -> None:
        if "strategy" in updates and updates["strategy"] != self._config.get("strategy"):
            self._prev_colors.clear()
        self._config.update(updates)
        self._save_config(self._config)
        svc = ScreenCapturerService.get_instance()
        if "fps" in updates and svc.is_running:
            svc.set_fps(int(updates["fps"]))

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def actual_fps(self) -> float:
        return self._actual_fps

    @property
    def capturer_name(self) -> str:
        return ScreenCapturerService.get_instance().capturer_name

    @property
    def standby_active(self) -> bool:
        """True quando lo schermo non fornisce frame da oltre STANDBY_GRACE."""
        return self._standby_since is not None

    def set_standby_preview(self, active: bool) -> bool:
        """Simula lo standby con l'effetto scelto, anche se lo schermo e' attivo.

        Si spegne da solo dopo STANDBY_PREVIEW_MAX secondi. Ritorna lo stato.
        """
        if active:
            self._standby_preview_until = time.monotonic() + STANDBY_PREVIEW_MAX
        else:
            self._standby_preview_until = 0.0
            self._standby_since = None
        return active

    @property
    def standby_preview_active(self) -> bool:
        return time.monotonic() < self._standby_preview_until

    @property
    def content_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """Rettangolo del contenuto rilevato (px), None = schermo intero."""
        return self._bb_rect

    def get_sampling_snapshot(self) -> Optional[dict]:
        """Ultima campionatura (frame, area, profondità per bordo, zone con colori).

        Aggiunge `age` (secondi dall'ultimo frame elaborato) così la UI può
        capire se il dato è fresco. None se non è mai stato elaborato un frame.
        """
        snap = self._sampling
        if snap is None:
            return None
        return {**snap, "age": round(time.monotonic() - self._sampling_ts, 2)}

    # ── Black-border detection ────────────────────────────────────────────────

    @staticmethod
    def _rects_equal(a, b, w: int, h: int) -> bool:
        if a is None or b is None:
            return a is b
        tol = max(2 * _BB_STEP, int(0.01 * max(w, h)))
        return all(abs(ca - cb) <= tol for ca, cb in zip(a, b))

    def _reset_bb(self) -> None:
        self._bb_rect = None
        self._bb_candidate = None
        self._bb_count = 0

    def _update_content_rect(self, frame: np.ndarray, cfg: dict) -> None:
        """Rilevamento periodico delle bande nere, con isteresi.

        Il rettangolo applicato cambia solo dopo bb_consistent rilevamenti
        consecutivi concordi: niente sfarfallii su scene scure o dissolvenze.
        """
        now = time.monotonic()
        if now - self._bb_last_check < float(cfg.get("bb_interval", 1.0)):
            return
        self._bb_last_check = now

        shape = frame.shape[:2]
        if shape != self._bb_frame_shape:
            self._bb_frame_shape = shape
            self._reset_bb()

        h, w = shape
        rect = _detect_content_rect(frame, int(cfg.get("bb_threshold", 18)))
        if rect is None:
            return   # frame indecidibile: mantieni lo stato corrente

        # Rettangolo ~ a schermo intero -> normalizza a None (nessun crop)
        full = (rect[0] <= _BB_STEP and rect[1] <= _BB_STEP and
                rect[2] >= w - _BB_STEP and rect[3] >= h - _BB_STEP)
        target = None if full else rect

        if self._rects_equal(target, self._bb_rect, w, h):
            self._bb_candidate = None
            self._bb_count = 0
            return

        if self._rects_equal(target, self._bb_candidate, w, h):
            self._bb_count += 1
        else:
            self._bb_candidate = target
            self._bb_count = 1

        if self._bb_count >= int(cfg.get("bb_consistent", 3)):
            self._bb_rect = target
            self._bb_candidate = None
            self._bb_count = 0
            self._prev_colors.clear()   # il mapping LED<->schermo è cambiato
            label = f"{target[2]-target[0]}x{target[3]-target[1]}px" if target else "full screen"
            print(f"[Ambilight] Content area: {label}")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._idle_loop, daemon=True, name="ambilight-idle"
        )
        self._thread.start()
        print("[Ambilight] Service started")

    def stop(self) -> None:
        self._stop_event.set()
        ScreenCapturerService.get_instance().stop()

    def pause(self) -> None:
        """Suspend the sampling loop AND turn the managed LEDs off.

        Used during topology calibration: the calibration must own the LEDs
        for a correct visualization, so we both stop sampling and black out
        every device the ambilight drives. Devices not covered by the
        calibration (non-linear, or LEDs outside the mapped topology) would
        otherwise stay frozen on the last ambilight frame."""
        self._paused = True
        self._blackout()

    def resume(self) -> None:
        self._paused = False

    def _blackout(self) -> None:
        """Send black to every enabled managed device, so nothing stays lit
        while the ambilight is paused."""
        if not self._manager:
            return
        for device_key, dev_cfg in self._config.get("devices", {}).items():
            if not dev_cfg.get("enabled", False):
                continue
            _, total_leds = self.get_device_zones(device_key)
            if total_leds <= 0:
                continue
            self._manager.apply_direct_colors(device_key, [(0, 0, 0)] * total_leds)

    # ── Zone cache ────────────────────────────────────────────────────────────

    def refresh_zones(self, device_key: str) -> None:
        self._zone_cache.pop(device_key, None)
        self._topology_warned.discard(device_key)

    def get_device_zones(self, device_key: str) -> Tuple[List[dict], int]:
        if device_key not in self._zone_cache:
            zones, total_leds = build_device_zones(device_key)
            self._validate_topology(device_key, total_leds)
            self._zone_cache[device_key] = (zones, total_leds)
        return self._zone_cache[device_key]

    def _validate_topology(self, device_key: str, total_leds: int) -> None:
        """Warn (once per device) when the LED count from the topology config
        does not match the count reported by the hardware. The mismatch is
        handled gracefully downstream (apply_direct_colors pads/truncates),
        but it usually signals a stale config/device_topologies.json entry."""
        if not self._manager or total_leds <= 0:
            return
        hw_led_count = self._manager.get_device_led_count(device_key)
        if hw_led_count is None or hw_led_count == total_leds:
            return
        if device_key in self._topology_warned:
            return
        self._topology_warned.add(device_key)
        print(
            f"[AmbilightService] Topology mismatch for '{device_key}': config "
            f"declares {total_leds} LEDs but hardware reports {hw_led_count}. "
            f"Colors will be padded/truncated; check config/device_topologies.json."
        )

    # ── Idle loop ─────────────────────────────────────────────────────────────

    def _idle_loop(self) -> None:
        svc = ScreenCapturerService.get_instance()

        try:
            import ctypes as _ct
            _ct.windll.winmm.timeBeginPeriod(1)
            _timer_ok = True
        except Exception:
            _timer_ok = False

        try:
            while not self._stop_event.is_set():
                t0  = time.perf_counter()
                cfg = dict(self._config)

                if not cfg.get("enabled", False):
                    if svc.is_running:
                        svc.stop()
                    self._stop_event.wait(0.5)
                    continue

                if not svc.is_running:
                    svc.start(
                        fps=int(cfg.get("fps", 15)),
                        preferred=cfg.get("capturer", "auto"),
                    )
                    self._stop_event.wait(0.1)
                    continue

                if self._paused:
                    self._stop_event.wait(0.1)
                    continue

                if self._standby_preview_until:
                    now = time.monotonic()
                    if now < self._standby_preview_until:
                        if self._standby_since is None:
                            self._standby_since = now
                            self._standby_last_write = 0.0
                        self._run_standby(cfg, now)
                        self._stop_event.wait(0.05)
                        continue
                    # Scaduta: riprende l'ambilight normale
                    self._standby_preview_until = 0.0
                    self._no_frame_since = self._standby_since = None

                frame = svc.get_latest_frame()
                if frame is None:
                    self._on_no_frame(cfg)
                    continue
                self._no_frame_since = self._standby_since = None

                self._process_frame(frame, cfg)

                elapsed = time.perf_counter() - t0
                if elapsed > 0:
                    self._actual_fps = round(0.85 * self._actual_fps + 0.15 / elapsed, 1)

                wait = 1.0 / max(1, int(cfg.get("fps", 15))) - elapsed
                if wait > 0:
                    self._stop_event.wait(wait)
        finally:
            if _timer_ok:
                import ctypes as _ct
                _ct.windll.winmm.timeEndPeriod(1)

    def _on_no_frame(self, cfg: dict) -> None:
        now = time.monotonic()
        if self._no_frame_since is None:
            self._no_frame_since = now
        if now - self._no_frame_since < STANDBY_GRACE:
            self._stop_event.wait(0.02)
            return
        if self._standby_since is None:
            self._standby_since = now
            self._standby_last_write = 0.0
            print(f"[AmbilightService] Schermo non disponibile: standby ({cfg.get('standby_mode', 'hold')})")
        self._run_standby(cfg, now)
        self._stop_event.wait(0.05)

    def _run_standby(self, cfg: dict, now: float) -> None:
        mode = cfg.get("standby_mode", "hold")
        if not self._manager or mode not in standby_effects.MODE_IDS or mode == "hold":
            return
        t = now - self._standby_since
        # Fade completato / luci spente: basta riscrivere una volta al secondo
        if standby_effects.is_static(mode, t) and now - self._standby_last_write < 1.0:
            return
        self._standby_last_write = now
        level = float(cfg.get("standby_brightness", 60)) / 100.0
        for device_key, (base, mask) in list(self._standby_ctx.items()):
            if not cfg.get("devices", {}).get(device_key, {}).get("enabled", False):
                continue
            colors = standby_effects.render(mode, t, base, mask, level)
            if colors is not None and not self._paused:
                self._manager.apply_direct_colors(device_key, colors)

    def _process_frame(self, frame: np.ndarray, cfg: dict) -> None:
        full_h, full_w = frame.shape[:2]
        snap_zones: List[dict] = []
        if cfg.get("black_bar_detect", True):
            self._update_content_rect(frame, cfg)
            if self._bb_rect is not None:
                x0, y0, x1, y1 = self._bb_rect
                frame = frame[y0:y1, x0:x1]   # view numpy, nessuna copia
        elif self._bb_rect is not None:
            self._reset_bb()

        strategy    = cfg.get("strategy", "adaptive_smooth")
        depth_pct   = cfg.get("depth", 10.0) / 100.0
        sat_boost   = cfg.get("saturation_boost", 1.4)
        min_lum     = cfg.get("min_luminance", 0)
        devices_cfg = cfg.get("devices", {})
        edge_cache: Dict[str, np.ndarray] = {}

        for device_key, dev_cfg in devices_cfg.items():
            if not dev_cfg.get("enabled", False):
                continue

            zones, total_leds = self.get_device_zones(device_key)
            if not zones or total_leds == 0:
                continue

            colors: List[Tuple[int, int, int]] = [(0, 0, 0)] * total_leds
            lit = np.zeros(total_leds, dtype=bool)
            zones_enabled = dev_cfg.get("zones_enabled", {})

            for zone in zones:
                if not is_zone_enabled(zones_enabled, zone):
                    continue

                led_start = zone["led_start"]
                led_end   = zone["led_end"]
                active    = led_end - led_start
                off       = zone["led_offset"] + led_start
                zone_key  = f"{device_key}:{zone['zone_index']}"

                if zone["edge"] == "area":
                    color = _sample_area_point(
                        frame, zone["x_pct"], zone["y_pct"], strategy
                    )
                    if strategy != "hsv":
                        color = _boost_saturation([color], sat_boost)[0]
                    zone_colors = [color] * active
                    if strategy in ("smooth", "adaptive_smooth"):
                        zone_colors = _apply_temporal_smooth(
                            self._prev_colors, zone_key, zone_colors,
                            alpha=cfg.get("ema_alpha", 0.35),
                            cut_threshold=cfg.get("scene_cut", 60.0),
                        )
                    zone_colors = _apply_min_luminance(zone_colors, min_lum)
                    colors[off: off + active] = zone_colors
                    lit[off: off + active] = True
                    snap_zones.append({
                        "dev": device_key, "zone": zone["name"],
                        "edge": "area", "x": round(zone["x_pct"], 4),
                        "y": round(zone["y_pct"], 4),
                        "colors": _hex_colors(zone_colors[:1]),
                    })
                    continue

                zone_colors = _sample_edge(
                    frame,
                    edge         = zone["edge"],
                    led_count    = active,
                    reversed_dir = zone["reversed"],
                    depth_pct    = depth_pct,
                    screen_start = zone["screen_start"],
                    screen_end   = zone["screen_end"],
                    strategy     = strategy,
                    zone_key     = zone_key,
                    prev_map     = self._prev_colors,
                    cfg          = cfg,
                    edge_cache   = edge_cache,
                )

                if strategy != "hsv":
                    zone_colors = _boost_saturation(zone_colors, sat_boost)

                zone_colors = _apply_min_luminance(zone_colors, min_lum)
                colors[off: off + active] = zone_colors
                lit[off: off + active] = True
                # Ordine "di schermo" (sinistra->destra / alto->basso), non d'ordine LED
                on_screen = zone_colors[::-1] if zone["reversed"] else zone_colors
                snap_zones.append({
                    "dev": device_key, "zone": zone["name"],
                    "edge": zone["edge"],
                    "start": round(zone["screen_start"], 4),
                    "end": round(zone["screen_end"], 4),
                    "colors": _hex_colors(on_screen),
                })

            self._standby_ctx[device_key] = (np.asarray(colors, dtype=np.float32), lit)

            # Skip the write if a pause arrived mid-frame (e.g. calibration
            # just started) — avoids a stray ambilight frame fighting it.
            if self._manager and not self._paused:
                self._manager.apply_direct_colors(device_key, colors)

        # Snapshot per l'anteprima UI: profondità realmente usata per bordo
        # (la cache contiene le strisce già ritagliate, anche con profondità adattiva).
        depth_px = {
            edge: int(strip.shape[0] if edge in ("top", "bottom") else strip.shape[1])
            for edge, strip in edge_cache.items()
        }
        rect = self._bb_rect or (0, 0, full_w, full_h)
        self._sampling = {
            "frame": [full_w, full_h],
            "rect":  list(rect),
            "depth": depth_px,
            "zones": snap_zones,
        }
        self._sampling_ts = time.monotonic()
