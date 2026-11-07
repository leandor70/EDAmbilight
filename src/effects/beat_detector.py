"""Rilevatore di battito: bande per il misuratore + battiti con forza 0..1.

Funzione pura sui campioni audio (nessun I/O, nessun thread): si alimenta con
blocchi mono float32 di lunghezza qualsiasi e restituisce i battiti trovati.

Il battito e' un picco del flusso spettrale (aumento di energia tra due frame
consecutivi) calcolato sullo spettro in scala logaritmica, quindi poco
dipendente dal volume, con soglia adattiva sull'ultimo secondo circa.
"""

import math
import time
from collections import deque
from typing import List, Optional

import numpy as np

FRAME = 1024                      # campioni per analisi (~21 ms a 48 kHz)

BASS_HZ = (30.0, 250.0)
MID_HZ  = (250.0, 4000.0)
HIGH_HZ = (4000.0, 16000.0)

HISTORY_SECS   = 1.0              # finestra della soglia adattiva
REFRACTORY     = 0.12             # s minimi tra due battiti rilevati
MIN_FLUX       = 1.2              # sotto questo flusso non e' mai un battito (rumore)
SILENCE_DBFS   = -70.0            # sotto questo livello il frame e' silenzio
MID_FLUX_GAIN  = 0.15             # peso della banda media/alta nel flusso (rullante, charleston)


def min_ratio(sensitivity: float) -> float:
    """Quanto il flusso deve superare la propria media (2.4x .. 1.4x).

    Il rumore stazionario ha un flusso che oscilla attorno alla media e non
    arriva a questi rapporti; un colpo di cassa li supera di molto.
    """
    s = max(0.0, min(100.0, float(sensitivity))) / 100.0
    return 2.4 - 1.0 * s


class Beat:
    __slots__ = ("strength", "time")

    def __init__(self, strength: float, t: float) -> None:
        self.strength = strength
        self.time = t


def _dbfs_to_unit(db: float) -> float:
    """-60 dBFS -> 0, 0 dBFS -> 1."""
    return max(0.0, min(1.0, (db + 60.0) / 60.0))


def _to_db(x: float) -> float:
    return 20.0 * math.log10(x) if x > 1e-9 else -120.0


def threshold_k(sensitivity: float) -> float:
    """Sensibilita' 0-100 -> moltiplicatore della deviazione standard (3.0 .. 0.6)."""
    s = max(0.0, min(100.0, float(sensitivity))) / 100.0
    return 3.0 - 2.4 * s


class BeatDetector:
    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = int(sample_rate)
        self._buf = np.zeros(0, dtype=np.float32)
        self._win = np.hanning(FRAME).astype(np.float32)
        freqs = np.fft.rfftfreq(FRAME, 1.0 / self.sample_rate)
        self._bass = (freqs >= BASS_HZ[0]) & (freqs < BASS_HZ[1])
        self._mid  = (freqs >= MID_HZ[0])  & (freqs < MID_HZ[1])
        self._high = (freqs >= HIGH_HZ[0]) & (freqs < min(HIGH_HZ[1], self.sample_rate / 2))
        self._lowflux_bins = self._bass
        self._midflux_bins = self._mid
        self._prev_log: Optional[np.ndarray] = None
        frames_per_sec = self.sample_rate / FRAME
        self._hist = deque(maxlen=max(8, int(HISTORY_SECS * frames_per_sec)))
        self._prev_flux = 0.0
        self._last_beat = -1e9
        # Ultimi valori per il misuratore (0..1) e istante dell'ultimo battito
        self.level = 0.0
        self.bass = 0.0
        self.mid = 0.0
        self.high = 0.0
        self.last_beat_time: Optional[float] = None
        self.beats = 0

    # ── API ────────────────────────────────────────────────────────────────────

    def process(self, mono: np.ndarray, sensitivity: float = 50.0,
                now: Optional[float] = None) -> List[Beat]:
        """Aggiunge campioni mono float32 (-1..1). Ritorna i battiti trovati.

        `now` e' l'istante dell'ultimo campione (default: time.monotonic()); i
        frame precedenti nello stesso blocco vengono datati all'indietro.
        """
        if mono.size:
            self._buf = np.concatenate((self._buf, np.asarray(mono, dtype=np.float32)))
        now = time.monotonic() if now is None else now
        n_frames = len(self._buf) // FRAME
        beats: List[Beat] = []
        step = FRAME / self.sample_rate
        for i in range(n_frames):
            frame = self._buf[i * FRAME:(i + 1) * FRAME]
            t = now - (n_frames - 1 - i) * step
            beat = self._analyse(frame, sensitivity, t)
            if beat:
                beats.append(beat)
        self._buf = self._buf[n_frames * FRAME:]
        return beats

    # ── interno ────────────────────────────────────────────────────────────────

    def _analyse(self, frame: np.ndarray, sensitivity: float, t: float) -> Optional[Beat]:
        rms = float(np.sqrt(np.mean(frame * frame)))
        self.level = _dbfs_to_unit(_to_db(rms))
        mag = np.abs(np.fft.rfft(frame * self._win)) / (FRAME / 4.0)   # sinusoide a fondo scala = 1.0

        def band(mask):
            return _dbfs_to_unit(_to_db(float(mag[mask].max()))) if mask.any() else 0.0

        self.bass, self.mid, self.high = band(self._bass), band(self._mid), band(self._high)

        if _to_db(rms) < SILENCE_DBFS:
            self._prev_log = None
            self._prev_flux = 0.0
            return None

        logm = np.log1p(mag * 50.0)
        flux = 0.0
        if self._prev_log is not None:
            diff = np.maximum(0.0, logm - self._prev_log)
            flux = float(diff[self._lowflux_bins].sum() + MID_FLUX_GAIN * diff[self._midflux_bins].sum())
        self._prev_log = logm

        hist = self._hist
        beat = None
        if len(hist) >= max(8, hist.maxlen // 3):     # riscaldamento: ~0.3 s di storico
            arr = np.fromiter(hist, dtype=np.float64)
            mean = float(arr.mean())
            thr = float(mean + threshold_k(sensitivity) * arr.std())
            thr = max(thr, mean * min_ratio(sensitivity), MIN_FLUX)
            rising = flux >= self._prev_flux
            if flux > thr and rising and (t - self._last_beat) >= REFRACTORY:
                ratio = flux / thr
                strength = max(0.35, min(1.0, (ratio - 1.0) / 1.5 + 0.35))
                beat = Beat(strength, t)
                self._last_beat = t
                self.last_beat_time = t
                self.beats += 1
        hist.append(flux)
        self._prev_flux = flux
        return beat
