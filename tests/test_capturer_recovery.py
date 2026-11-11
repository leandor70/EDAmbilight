"""_DxcamCapturer must restart a dxcam camera whose capture loop has crashed."""
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace as N

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import screen_capturer_service as scs   # noqa: E402


class _FakeCam:
    """Mimics DXCamera state after its capture loop raised: the thread is
    cleared (name-mangled attribute), is_capturing is False and the frame
    buffer is gone, so get_latest_frame() returns None."""

    def __init__(self):
        self.is_capturing = False
        self._DXCamera__thread = None
        self.crashed = False

    def start(self, target_fps=60):
        self.is_capturing = True

    def stop(self):
        self.is_capturing = False

    def release(self):
        pass

    def crash(self):
        self.crashed = True
        self.is_capturing = False
        self._DXCamera__thread = None

    def get_latest_frame(self, copy=True):
        if self.crashed:
            return None
        return np.zeros((8, 8, 4), dtype=np.uint8)


def _capturer(monkeypatch):
    created = []

    def create(output_color="BGRA"):
        cam = _FakeCam()
        created.append(cam)
        return cam

    fake = ModuleType("dxcam")
    fake.create = create
    monkeypatch.setitem(sys.modules, "dxcam", fake)
    monkeypatch.setattr(scs.time, "sleep", lambda s: None)
    return scs._DxcamCapturer(15), created


def test_healthy_camera_is_left_alone(monkeypatch):
    cap, created = _capturer(monkeypatch)
    assert cap.grab() is not None
    assert len(created) == 1


def test_camera_that_crashed_is_recreated(monkeypatch):
    cap, created = _capturer(monkeypatch)
    created[0].crash()

    frame = cap.grab()          # may be None on the call that detects the crash
    frame = frame if frame is not None else cap.grab()

    assert len(created) == 2 and created[1].is_capturing
    assert frame is not None
