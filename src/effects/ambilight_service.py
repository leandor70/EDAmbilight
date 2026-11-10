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

from core.audio_capture import AudioListener
from core.screen_capturer_service import ScreenCapturerService
from effects import accent_effects, standby_effects

CONFIG_PATH = Path("config/ambilight_config.json")

# Secondi senza frame prima di considerare lo schermo in standby (i buchi brevi,
# es. avvio o cambio capturer, non devono far partire gli effetti).
STANDBY_GRACE = 3.0
# Durata massima dell'anteprima manuale dello standby (s)
STANDBY_PREVIEW_MAX = 60.0
# Passo di aggiornamento dei LED mentre un accento e' attivo (s): tra due frame
# catturati si riapplicano gli ultimi colori con l'accento corrente
ACCENT_TICK = 1.0 / 60.0

# ── Sampling helpers ──────────────────────────────────────────────────────────


def _led_world_positions(zone: dict) -> List[Tuple[float, float]]:
    """LED positions in screen coordinates: x to the right, y DOWNWARD.

    The Topology Editor draws with y pointing UP (rotation 90 = LEDs going up),
    so y is flipped here. Everything built on these points (monitor frame,
    screen fractions, LED order, area points) then reads top-to-bottom like
    the captured frame.

    Item i is the position of LED i. With direction "reverse" (Flip in the
    editor) the zone is wired the other way round: LED 0 sits at the far end.
    """
    x0      = zone["position"]["x"]
    y0      = zone["position"]["y"]
    spacing = zone.get("led_spacing", 1.0)
    rot     = zone.get("rotation", 0)
    dx = {0: spacing, 90: 0, 180: -spacing, 270: 0      }.get(rot, spacing)
    dy = {0: 0,       90: spacing, 180: 0,  270: -spacing}.get(rot, 0)
    pts = [(x0 + i * dx, -(y0 + i * dy)) for i in range(zone["led_count"])]
    if zone.get("direction") == "reverse":
        pts.reverse()
    return pts


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
    # Adaptive strategies use the brightness-based percentile on area patches
    eff = "adaptive_smooth" if strategy in ("adaptive", "adaptive_smooth") else strategy
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
    """Striscia di bordo a tutta larghezza/altezza, già convertita (float32).

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


def is_phantom_zone(zone: dict) -> bool:
    """A zone OpenRGB reports with a name made only of '?' ("???").

    These are LEDs that do not exist on the hardware (OpenRGB detects them
    anyway): they are excluded from everything - never shown, never driven, left
    out of the scene. It is the ONE rule that looks at a zone name; nothing else
    about a setup is inferred from names.
    """
    return not str(zone.get("name", "")).strip().strip("?")


def is_zone_enabled(zones_enabled: dict, zone: dict) -> bool:
    """Zone switches are keyed by zone_index only: a zone name never decides
    anything (keys written by name by old versions are ignored). On by default."""
    return bool(zones_enabled.get(str(zone.get("zone_index")), True))


def _sample_grid(frame: np.ndarray, rows: int, cols: int) -> np.ndarray:
    """Mean colour of each cell of a rows x cols grid laid over the frame -> (rows, cols, 3).

    The captured frame is BGR (like everywhere else in this file); the result is RGB."""
    h, w = frame.shape[:2]
    small = frame[::4, ::4, :3].astype(np.float32)
    sh, sw = small.shape[:2]
    r_idx = np.minimum(np.linspace(0, sh, rows + 1).astype(int)[:-1], sh - 1)
    c_idx = np.minimum(np.linspace(0, sw, cols + 1).astype(int)[:-1], sw - 1)
    r_cnt = np.diff(np.append(r_idx, sh)).clip(1)
    c_cnt = np.diff(np.append(c_idx, sw)).clip(1)
    sums = np.add.reduceat(np.add.reduceat(small, r_idx, axis=0), c_idx, axis=1)
    return (sums / (r_cnt[:, None, None] * c_cnt[None, :, None]))[..., ::-1]


# ── Screen rectangle (where the screen sits in the topology scene) ────────────
#
# With a screen rectangle the side of the screen a LED follows is decided by WHERE
# the LED is drawn, never by the zone name:
#   * LED on (or near) a side of the rectangle  -> reads that side of the screen
#   * LED inside the rectangle                  -> reads the point of the screen
#                                                   under it (centre -> centre)
#   * LED outside the rectangle                 -> left alone (never written)
# "Near" is SCREEN_EDGE_BAND of the smaller side of the rectangle, across the
# side, so a strip drawn a little off the frame still counts as that side.
#
# The topology is the ONLY description of a setup: zone names never decide
# anything (the one exception: '???' zones, LEDs that do not exist, are dropped). The rectangle is stored in device_topologies.json as "screen_rect" in
# editor coordinates (y pointing UP, like zone positions); without it the screen
# is the bounding box of the whole scene, grown to the real screen proportions.

SCREEN_EDGE_BAND = 0.15


def _valid_rect(r) -> bool:
    try:
        return (r["x_max"] - r["x_min"]) > 0 and (r["y_max"] - r["y_min"]) > 0
    except (KeyError, TypeError):
        return False


def _scene_points(data: dict, skip=frozenset()) -> List[Tuple[float, float]]:
    """LED points of the scene; `skip` = (device_key, zone_index) left out (key grids)."""
    return [pt for key, topo in data.get("topologies", {}).items()
            for z in topo.get("zones", [])
            if (key, z.get("zone_index")) not in skip and not is_phantom_zone(z)
            for pt in _led_world_positions(z)]


def fit_aspect(rect, aspect: Optional[float]):
    """Grow (x_min, x_max, y_min, y_max) around its centre to width/height = aspect.

    It only grows, never shrinks, so whatever the rectangle framed stays inside
    (or in the edge band). aspect None / <= 0 leaves it as it is."""
    if not aspect or aspect <= 0:
        return rect
    x0, x1, y0, y1 = rect
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return rect
    if w / h < aspect:
        grow = (h * aspect - w) / 2
        return (x0 - grow, x1 + grow, y0, y1)
    grow = (w / aspect - h) / 2
    return (x0, x1, y0 - grow, y1 + grow)


def _bbox(pts) -> Tuple[float, float, float, float]:
    return (min(p[0] for p in pts), max(p[0] for p in pts),
            min(p[1] for p in pts), max(p[1] for p in pts))


def screen_frame(data: dict, skip=frozenset(), aspect: Optional[float] = None
                 ) -> Tuple[str, Tuple[float, float, float, float]]:
    """Where the screen sits in the scene: (mode, rect).

    rect = (x_min, x_max, y_min, y_max) in sampling coordinates (y DOWN, as
    _led_world_positions):
      "manual" -> the stored screen_rect
      "auto"   -> no rectangle yet: bounding box of the whole scene, grown to the
                  proportions of the real screen (aspect = width/height)
    """
    r = data.get("screen_rect")
    if _valid_rect(r):
        return "manual", (float(r["x_min"]), float(r["x_max"]), -float(r["y_max"]), -float(r["y_min"]))
    pts = _scene_points(data, skip)
    return "auto", fit_aspect(_bbox(pts) if pts else (0.0, 100.0, 0.0, 100.0), aspect)


def suggest_screen_rect(data: dict, skip=frozenset(), aspect: Optional[float] = None) -> Optional[dict]:
    """A starting rectangle (editor coordinates, y UP): the bounding box of the
    whole scene with the real screen proportions. The user then places it."""
    pts = _scene_points(data, skip)
    if not pts:
        return None
    x0, x1, y0, y1 = _bbox(pts)
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        return None
    x0, x1, y0, y1 = fit_aspect((x0, x1, y0, y1), aspect)
    return {"x_min": x0, "x_max": x1, "y_min": -y1, "y_max": -y0}


def _classify_led(x: float, y: float, rect, band: float, along_axis: Optional[str] = None,
                  reach: float = 0.5):
    """("off",) | ("edge", side, along 0..1) | ("area", x_pct, y_pct).

    A LED belongs to a side when it is within `band` of it ACROSS the side (a
    strip drawn a little above / below the frame still counts) and within the
    length of the side ALONG it, give or take `reach` (half a LED): past the
    corner it is outside. along_axis ("x" or "y") is the direction the strip
    runs: a strip only follows the sides parallel to it (a horizontal strip
    never reads the left or right side, even near a corner)."""
    x0, x1, y0, y1 = rect
    w, h = max(0.001, x1 - x0), max(0.001, y1 - y0)
    d = {"left": x - x0, "right": x1 - x, "top": y - y0, "bottom": y1 - y}
    in_x = x0 - reach <= x <= x1 + reach
    in_y = y0 - reach <= y <= y1 + reach
    near = [k for k in d if abs(d[k]) <= band and (in_x if k in ("top", "bottom") else in_y)]
    if along_axis:
        near = [k for k in near if (k in ("top", "bottom")) == (along_axis == "x")]
    if near:
        side = min(near, key=lambda k: abs(d[k]))
        along = (x - x0) / w if side in ("top", "bottom") else (y - y0) / h
        return ("edge", side, max(0.0, min(1.0, along)))
    if x0 <= x <= x1 and y0 <= y <= y1:
        return ("area", (x - x0) / w, (y - y0) / h)
    return ("off",)


def _geometric_entries(zone: dict, led_offset: int, rect) -> List[dict]:
    """Sampling entries for one zone, LED by LED, from where its LEDs sit.

    Consecutive LEDs on the same side become one edge entry (a zone that runs
    past a corner gives its corner LEDs to the side it is parallel to); LEDs
    inside become one point entry each; LEDs outside become "off" entries
    (listed, never sampled)."""
    pts = _led_world_positions(zone)
    if not pts:
        return []
    x0, x1, y0, y1 = rect
    w, h = max(0.001, x1 - x0), max(0.001, y1 - y0)
    band = max(1.0, SCREEN_EDGE_BAND * min(w, h))
    spacing = zone.get("led_spacing", 1.0)
    base = {"name": zone.get("name", ""), "zone_index": zone["zone_index"],
            "led_count": zone["led_count"], "led_offset": led_offset,
            "screen_start": 0.0, "screen_end": 1.0, "reversed": False}

    axis = None
    if len(pts) > 1:
        axis = "x" if abs(pts[-1][0] - pts[0][0]) >= abs(pts[-1][1] - pts[0][1]) else "y"
    reach = max(0.5, spacing / 2)
    kinds = [_classify_led(x, y, rect, band, axis, reach) for x, y in pts]
    out: List[dict] = []
    i = 0
    while i < len(kinds):
        k = kinds[i]
        j = i + 1
        if k[0] in ("edge", "off"):
            while j < len(kinds) and kinds[j][0] == k[0] and kinds[j][1:2] == k[1:2]:
                j += 1
        if k[0] == "off":
            out.append({**base, "edge": "off", "led_start": i, "led_end": j})
        elif k[0] == "area":
            out.append({**base, "edge": "area", "led_start": i, "led_end": i + 1,
                        "x_pct": k[1], "y_pct": k[2]})
        else:
            side = k[1]
            along = [kinds[n][2] for n in range(i, j)]
            span = w if side in ("top", "bottom") else h
            half = spacing / 2 / span
            out.append({**base, "edge": side, "led_start": i, "led_end": j,
                        "screen_start": max(0.0, min(along) - half),
                        "screen_end":   min(1.0, max(along) + half),
                        "reversed":     len(along) > 1 and along[0] > along[-1]})
        i = j
    return out


def summarize_zones(entries: List[dict]) -> List[dict]:
    """One item per zone (entries of a zone share zone_index), for lists and counts.

    edge: "top", "area", "matrix", several joined with "+" ("top+right"), or "off"
    when every LED of the zone is outside the screen (it is never driven)."""
    by_idx: Dict[int, dict] = {}
    for e in entries:
        s = by_idx.setdefault(e["zone_index"], {
            "zone_index": e["zone_index"], "name": e["name"],
            "rows": e.get("rows"), "cols": e.get("cols"), "_kinds": []})
        if e["edge"] != "off" and e["edge"] not in s["_kinds"]:
            s["_kinds"].append(e["edge"])
    out = []
    for s in by_idx.values():
        kinds = s.pop("_kinds")
        s["edge"] = "+".join(kinds) if kinds else "off"
        s["outside"] = not kinds
        out.append(s)
    return out


def _matrix_entry(zone: dict, led_offset: int, layout: dict) -> dict:
    return {
        "name":         zone.get("name", ""),
        "zone_index":   zone["zone_index"],
        "led_count":    zone["led_count"],
        "led_offset":   led_offset,
        "led_start":    0,
        "led_end":      zone["led_count"],
        "screen_start": 0.0,
        "screen_end":   1.0,
        "edge":         "matrix",
        "rows":         layout["rows"],
        "cols":         layout["cols"],
        "cells":        [tuple(c) for c in layout["cells"]],
        "reversed":     False,
    }


def build_device_zones(device_key: str, layouts: Optional[dict] = None,
                       scene_skip=frozenset(), aspect: Optional[float] = None) -> Tuple[List[dict], int]:
    """Load zone sampling parameters for a device from device_topologies.json.

    `layouts` (OpenRGBManager.matrix_layouts) turns a zone that has a key grid
    into an "matrix" zone: every LED reads its own cell of the screen.
    Entries of one zone can be several (one per side / point / off run): they
    share zone_index and differ by led_start..led_end."""
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

    _, rect = screen_frame(data, scene_skip, aspect)
    result: List[dict] = []
    for z_idx, zone in enumerate(all_zones):
        if is_phantom_zone(zone):
            continue                          # '???': LEDs that do not exist, never driven
        layout = (layouts or {}).get(zone["zone_index"])
        if layout:
            result.append(_matrix_entry(zone, zone_offsets[z_idx], layout))
        else:
            result.extend(_geometric_entries(zone, zone_offsets[z_idx], rect))
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
        self._frame_size: Optional[Tuple[int, int]] = None   # (w, h) of the captured screen
        self._topology_warned: set = set()
        # Standby (schermo non disponibile): ultimi colori + maschera LED attivi
        # per device, e istanti di inizio dell'assenza di frame / dello standby.
        self._standby_ctx: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        # LEDs written by the last frame, per device: a LED that stops being used
        # gets black once, then it is left free (never written again)
        self._prev_lit: Dict[str, np.ndarray] = {}
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
        # Accento sul battito audio (luminosita' / tinta): stato dell'ultimo battito
        self._accent = accent_effects.AccentState()
        # Ascolto dell'audio di sistema: ogni battito rilevato fa partire un accento
        self._audio = AudioListener(self.trigger_accent)

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
        # I default dell'accento completano la copia restituita alla UI; il file
        # di configurazione resta com'e' finche' l'utente non cambia un valore.
        return {**accent_effects.DEFAULTS, **self._config}

    def audio_status(self) -> dict:
        """Stato dell'ascolto audio (misuratore della UI)."""
        return self._audio.status()

    def _sync_audio(self, cfg: dict) -> None:
        """Avvia/ferma la cattura audio secondo la configurazione (economico)."""
        p = accent_effects.params_from_cfg(cfg)
        want = p["enabled"] and bool(cfg.get("enabled", False))
        self._audio.sync(want, p["device"], p["sensitivity"])

    def trigger_accent(self, strength: float = 1.0) -> bool:
        """Fa partire un accento (battito audio o prova). False se il limite lo scarta."""
        return self._accent.trigger(strength, accent_effects.params_from_cfg(self._config))

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
        self._audio.stop()
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

    @property
    def frame_size(self) -> Optional[Tuple[int, int]]:
        """(width, height) of the last captured screen, None before the first frame."""
        return self._frame_size

    def refresh_zones(self, device_key: str) -> None:
        self._zone_cache.pop(device_key, None)
        self._topology_warned.discard(device_key)

    def get_device_zones(self, device_key: str) -> Tuple[List[dict], int]:
        if device_key not in self._zone_cache:
            get_layouts = getattr(self._manager, "matrix_layouts", None)
            layouts = get_layouts(device_key) if get_layouts else None
            skip = set()
            if get_layouts:
                for ctrl in getattr(self._manager, "devices", []):
                    key = self._manager._make_device_key(ctrl)
                    skip |= {(key, i) for i in get_layouts(key)}
            aspect = (self._frame_size[0] / self._frame_size[1]) if self._frame_size else None
            zones, total_leds = build_device_zones(device_key, layouts, skip, aspect)
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
                self._sync_audio(cfg)

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
                    self._wait_with_accent(wait, cfg)
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
                self._manager.apply_direct_colors(device_key, colors, mask)

    # ── Accento sul battito ───────────────────────────────────────────────────

    def _accent_now(self, cfg: dict):
        """(parametri, k, tinta) se c'e' un accento in corso, altrimenti None."""
        p = accent_effects.params_from_cfg(cfg)
        k, hue = self._accent.levels(time.monotonic(), p)
        return (p, k, hue) if self._accent.is_active(k, hue) else None

    @staticmethod
    def _accented(colors: List[Tuple[int, int, int]], accent) -> List[Tuple[int, int, int]]:
        """Colori di una zona con l'accento applicato (per l'anteprima Live)."""
        if not accent or not colors:
            return colors
        p, k, hue = accent
        arr = np.asarray(colors, dtype=np.float32)
        return accent_effects.to_colors(
            accent_effects.render(arr, np.ones(len(arr), dtype=bool), k, hue, p))

    def _accent_tick(self, cfg: dict) -> bool:
        """Riapplica gli ultimi colori base con l'accento corrente.

        Serve tra due frame catturati: un flash di 100 ms non puo' dipendere dai
        15-30 fps della cattura. False se non c'e' nessun accento in corso.
        """
        accent = self._accent_now(cfg)
        if not accent or self._paused or not self._manager:
            return bool(accent)
        p, k, hue = accent
        for device_key, (base, lit) in list(self._standby_ctx.items()):
            if not cfg.get("devices", {}).get(device_key, {}).get("enabled", False):
                continue
            colors = accent_effects.to_colors(accent_effects.render(base, lit, k, hue, p))
            self._manager.apply_direct_colors(device_key, colors, lit)
        return True

    def _wait_with_accent(self, wait: float, cfg: dict) -> None:
        """Attende `wait` secondi; con l'accento attivo aggiorna i LED a 60 passi/s.

        Con l'accento abilitato (ascolto audio) dorme a fette anche a riposo, cosi'
        un battito arrivato dal thread audio parte subito e non al frame successivo.
        """
        listening = bool(cfg.get("accent_enabled", False))
        end = time.perf_counter() + wait
        while not self._stop_event.is_set():
            remaining = end - time.perf_counter()
            if remaining <= 0:
                return
            if self._accent_tick(cfg) or listening:
                self._stop_event.wait(min(remaining, ACCENT_TICK))
            else:
                self._stop_event.wait(remaining)
                return

    def _process_frame(self, frame: np.ndarray, cfg: dict) -> None:
        full_h, full_w = frame.shape[:2]
        if self._frame_size != (full_w, full_h):
            # the automatic screen rectangle follows the real proportions
            self._frame_size = (full_w, full_h)
            self._zone_cache.clear()
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
        accent = self._accent_now(cfg)     # (params, k, tinta) se attivo, altrimenti None

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
                if zone["edge"] == "off" or not is_zone_enabled(zones_enabled, zone):
                    continue                  # outside the screen: stays dark

                led_start = zone["led_start"]
                led_end   = zone["led_end"]
                active    = led_end - led_start
                off       = zone["led_offset"] + led_start
                # one zone can give several entries (sides / points): keep their history apart
                zone_key  = f"{device_key}:{zone['zone_index']}:{led_start}"

                if zone["edge"] == "matrix":
                    grid = _sample_grid(frame, zone["rows"], zone["cols"])
                    per_led = [(0, 0, 0)] * active
                    for r, c, led in zone["cells"]:
                        if led < active:
                            px = grid[r, c]
                            per_led[led] = (int(px[0]), int(px[1]), int(px[2]))
                    zone_colors = _boost_saturation(per_led, sat_boost)
                    if strategy in ("smooth", "adaptive_smooth"):
                        zone_colors = _apply_temporal_smooth(
                            self._prev_colors, zone_key, zone_colors,
                            alpha=cfg.get("ema_alpha", 0.35),
                            cut_threshold=cfg.get("scene_cut", 60.0),
                        )
                    zone_colors = _apply_min_luminance(zone_colors, min_lum)
                    colors[off: off + active] = zone_colors
                    lit[off: off + active] = True
                    shown = self._accented(zone_colors, accent)
                    snap_zones.append({
                        "dev": device_key, "zone": zone["name"], "edge": "matrix",
                        "rows": zone["rows"], "cols": zone["cols"],
                        "cells": [[r, c] for r, c, led in zone["cells"] if led < active],
                        "colors": _hex_colors([shown[led] for r, c, led in zone["cells"] if led < active]),
                    })
                    continue

                if zone["edge"] == "area":
                    color = _sample_area_point(
                        frame, zone["x_pct"], zone["y_pct"], strategy
                    )
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
                        "colors": _hex_colors(self._accented(zone_colors[:1], accent)),
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
                    "colors": _hex_colors(self._accented(on_screen, accent)),
                })

            # Colori base (senza accento): servono anche allo standby e ai passi
            # di accento tra un frame catturato e il successivo
            base = np.asarray(colors, dtype=np.float32)
            self._standby_ctx[device_key] = (base, lit)

            out = colors
            if accent:
                p, k, hue = accent
                out = accent_effects.to_colors(accent_effects.render(base, lit, k, hue, p))

            # Skip the write if a pause arrived mid-frame (e.g. calibration
            # just started) — avoids a stray ambilight frame fighting it.
            if self._manager and not self._paused:
                # write only the LEDs in use (+ the ones that just stopped being
                # used, once, in black): the others stay free for OpenRGB
                prev = self._prev_lit.get(device_key)
                write = lit | prev if prev is not None and len(prev) == len(lit) else lit
                self._manager.apply_direct_colors(device_key, out, write)
                self._prev_lit[device_key] = lit.copy()

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
