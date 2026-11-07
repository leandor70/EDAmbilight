"""Cattura dell'audio di sistema (loopback WASAPI) e ascolto dei battiti.

La libreria (PyAudioWPatch) e' opzionale e viene caricata solo quando serve: se
manca o non parte, l'errore e' un testo leggibile nello stato, mai un'eccezione
che ferma l'ambilight.

AudioCapture  : thread che legge il loopback e passa blocchi mono a un callback.
AudioListener : capture + BeatDetector + stato per il misuratore della UI.
"""

import threading
import time
from typing import Callable, Optional

import numpy as np

from effects.beat_detector import BeatDetector

INSTALL_HINT = "Audio capture needs the PyAudioWPatch package (pip install PyAudioWPatch)"
FRAMES_PER_BUFFER = 1024
RETRY_SECS = 5.0          # attesa prima di riprovare dopo un errore di cattura
SILENT_AFTER = 0.6        # s senza blocchi = nessun suono in riproduzione (il loopback tace)


def _load_backend():
    """(modulo, errore): il modulo e' None se la libreria non e' utilizzabile."""
    try:
        import pyaudiowpatch as pa
        return pa, ""
    except ImportError:
        return None, INSTALL_HINT
    except Exception as exc:                       # DLL mancante, ecc.
        return None, f"Audio library could not be loaded: {exc}"


def list_devices(backend=None) -> dict:
    """Dispositivi di uscita ascoltabili: {available, devices: [nomi], error}."""
    pa_mod, err = (backend, "") if backend is not None else _load_backend()
    if pa_mod is None:
        return {"available": False, "devices": [], "error": err}
    p = None
    try:
        p = pa_mod.PyAudio()
        names = [lb["name"] for lb in p.get_loopback_device_info_generator()]
        return {"available": True, "devices": names, "error": ""}
    except Exception as exc:
        return {"available": False, "devices": [], "error": f"Could not list audio devices: {exc}"}
    finally:
        if p is not None:
            try:
                p.terminate()
            except Exception:
                pass


class AudioCapture:
    """Legge il loopback di un dispositivo e chiama on_block(mono_float32, sample_rate)."""

    def __init__(self, on_block: Callable[[np.ndarray, int], None], backend=None) -> None:
        self._on_block = on_block
        self._backend = backend
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._opened = threading.Event()
        self.error = ""
        self.device_name = ""
        self.sample_rate = 0

    # ── stato ──────────────────────────────────────────────────────────────────

    @property
    def alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def running(self) -> bool:
        return self.alive and self._opened.is_set()

    # ── ciclo di vita ──────────────────────────────────────────────────────────

    def start(self, device: str = "") -> None:
        """Avvia la cattura in un thread (non blocca: l'apertura del dispositivo e' lenta)."""
        if self.alive:
            return
        self._stop.clear()
        self._opened.clear()
        self.error = ""
        self._thread = threading.Thread(
            target=self._run, args=(device,), daemon=True, name="audio-capture")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        t = self._thread
        if t is not None and t is not threading.current_thread():
            t.join(timeout=2.0)
        self._thread = None

    # ── thread ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _pick_device(p, pa_mod, wanted: str) -> dict:
        if wanted:
            for lb in p.get_loopback_device_info_generator():
                if lb["name"] == wanted:
                    return lb
            raise RuntimeError(f"Audio device not found: {wanted}")
        wasapi = p.get_host_api_info_by_type(pa_mod.paWASAPI)
        default = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
        if default.get("isLoopbackDevice"):
            return default
        for lb in p.get_loopback_device_info_generator():
            if default["name"] in lb["name"]:
                return lb
        raise RuntimeError("No loopback device found for the default audio output")

    def _run(self, device: str) -> None:
        pa_mod, err = (self._backend, "") if self._backend is not None else _load_backend()
        if pa_mod is None:
            self.error = err
            return
        p = None
        stream = None
        try:
            p = pa_mod.PyAudio()
            info = self._pick_device(p, pa_mod, device)
            channels = max(1, int(info["maxInputChannels"]))
            rate = int(info["defaultSampleRate"])
            self.device_name = info["name"]
            self.sample_rate = rate

            def callback(in_data, frame_count, time_info, status):
                try:
                    x = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
                    self._on_block(x.reshape(-1, channels).mean(axis=1), rate)
                except Exception as exc:               # un blocco storto non deve fermare il flusso
                    self.error = f"Audio processing error: {exc}"
                return (None, pa_mod.paContinue)

            stream = p.open(format=pa_mod.paInt16, channels=channels, rate=rate,
                            frames_per_buffer=FRAMES_PER_BUFFER, input=True,
                            input_device_index=info["index"], stream_callback=callback)
            self._opened.set()
            while not self._stop.wait(0.2):
                if not stream.is_active():
                    self.error = "The audio stream stopped (device removed or changed?)"
                    break
        except Exception as exc:
            self.error = f"Could not capture audio: {exc}"
        finally:
            self._opened.clear()
            for closer in (getattr(stream, "stop_stream", None), getattr(stream, "close", None),
                           getattr(p, "terminate", None)):
                if closer is not None:
                    try:
                        closer()
                    except Exception:
                        pass


class AudioListener:
    """Capture + rilevatore di battito. sync() e' economico: si chiama a ogni ciclo."""

    def __init__(self, on_beat: Callable[[float], None], backend=None) -> None:
        self._on_beat = on_beat
        self._backend = backend
        self._capture: Optional[AudioCapture] = None
        self._detector: Optional[BeatDetector] = None
        self._device = ""
        self._sens = 50.0
        self._last_block = 0.0
        self._last_try = -1e9
        self._last_error = ""

    # ── controllo ──────────────────────────────────────────────────────────────

    def sync(self, want: bool, device: str, sensitivity: float) -> None:
        """Allinea la cattura alla configurazione: avvia, ferma o riavvia se serve."""
        self._sens = float(sensitivity)
        cap = self._capture
        if not want:
            if cap is not None:
                self.stop()
            return
        if cap is not None and cap.alive and device == self._device:
            return
        now = time.monotonic()
        if cap is not None and not cap.alive and device == self._device:
            # Cattura finita con un errore: ritenta ogni RETRY_SECS, senza martellare
            if now - self._last_try < RETRY_SECS:
                return
        self.stop()
        self._device = device
        self._last_try = now
        self._detector = None
        self._last_error = ""
        self._capture = AudioCapture(self._on_block, self._backend)
        self._capture.start(device)

    def stop(self) -> None:
        cap = self._capture
        if cap is not None:
            self._last_error = cap.error or self._last_error
            cap.stop()
        self._capture = None
        self._detector = None

    # ── audio ──────────────────────────────────────────────────────────────────

    def _on_block(self, mono: np.ndarray, sample_rate: int) -> None:
        det = self._detector
        if det is None or det.sample_rate != sample_rate:
            det = self._detector = BeatDetector(sample_rate)
        now = time.monotonic()
        self._last_block = now
        for beat in det.process(mono, self._sens, now=now):
            self._on_beat(beat.strength)

    # ── stato per la UI ────────────────────────────────────────────────────────

    def status(self) -> dict:
        cap, det = self._capture, self._detector
        now = time.monotonic()
        running = bool(cap and cap.running)
        stale = now - self._last_block > SILENT_AFTER
        live = running and det is not None and not stale
        beat_age = None
        if det is not None and det.last_beat_time is not None:
            beat_age = round(now - det.last_beat_time, 3)
        return {
            "running": running,
            "error":   (cap.error if cap and cap.error else self._last_error),
            "device":  cap.device_name if cap else "",
            "level":   round(det.level, 3) if live else 0.0,
            "bass":    round(det.bass, 3) if live else 0.0,
            "mid":     round(det.mid, 3) if live else 0.0,
            "high":    round(det.high, 3) if live else 0.0,
            "beat_age": beat_age,
            "beats":   det.beats if det else 0,
            "silent":  running and (stale or (det is not None and det.level < 0.02)),
        }
