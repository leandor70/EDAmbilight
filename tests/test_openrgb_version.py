"""OpenRGB version notice, and how OpenRGB is started."""
import sys
from pathlib import Path
from types import SimpleNamespace as N

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils import openrgb_bootstrap as boot      # noqa: E402
from utils import openrgb_version as ov          # noqa: E402


def _log(folder: Path, name: str, header: str, mtime: float = None):
    folder.mkdir(parents=True, exist_ok=True)
    f = folder / name
    f.write_text(f"    {header}\n    Commit: abc\n    Launched: x\n" + "=" * 20 + "\n", encoding="utf-8")
    if mtime is not None:
        import os
        os.utime(f, (mtime, mtime))
    return f


# -- parsing ---------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("v1.1", (1, 1, False, "1.1")),
    ("v1.0", (1, 0, False, "1.0")),
    ("v0.9", (0, 9, False, "0.9")),
    ("v0.9+ (1.0rc2)", (1, 0, True, "1.0rc2")),         # the release candidate of 1.0
    ("v0.9.1 (build 12)", (0, 9, False, "0.9")),
])
def test_parse_version(text, expected):
    assert ov.parse_version(text) == expected


def test_unreadable_version_is_none():
    assert ov.parse_version("OpenRGB dev build") is None


@pytest.mark.parametrize("args,old", [
    ((0, 9, False), True), ((1, 0, True), True), ((1, 0, False), False), ((1, 1, False), False),
])
def test_older_than_one_zero(args, old):
    assert ov.is_older_than_1_0(*args) is old


# -- reading the log -------------------------------------------------------------

def test_reads_the_newest_log(tmp_path):
    _log(tmp_path, "OpenRGB_old.log", "OpenRGB v0.9", mtime=1000)
    _log(tmp_path, "OpenRGB_new.log", "OpenRGB v1.1", mtime=2000)
    assert ov.read_version_text(tmp_path) == "v1.1"


def test_no_logs_means_no_version(tmp_path):
    assert ov.read_version_text(tmp_path) is None
    assert ov.read_version_text(tmp_path / "missing") is None


# -- the notice ------------------------------------------------------------------

def test_old_version_is_reported_once_per_version(tmp_path):
    logs, state = tmp_path / "logs", tmp_path / "v.json"
    _log(logs, "a.log", "OpenRGB v0.9+ (1.0rc2)")
    got = []
    add = lambda kind, key, text: got.append((kind, key, text))

    assert ov.check_openrgb_version(add, state, logs) == "1.0rc2"
    assert len(got) == 1 and got[0][0] == "version"
    assert "1.0rc2" in got[0][2] and "PawnIO" in got[0][2] and "openrgb.org" in got[0][2]

    ov.check_openrgb_version(add, state, logs)                # next start: same version, quiet
    assert len(got) == 1

    _log(logs, "b.log", "OpenRGB v0.9", mtime=9_999_999_999)   # a different old version: new notice
    ov.check_openrgb_version(add, state, logs)
    assert len(got) == 2


def test_current_version_is_silent(tmp_path):
    logs = tmp_path / "logs"
    _log(logs, "a.log", "OpenRGB v1.1")
    got = []
    assert ov.check_openrgb_version(lambda *a: got.append(a), tmp_path / "v.json", logs) == "1.1"
    assert got == []


def test_missing_log_is_silent(tmp_path):
    got = []
    assert ov.check_openrgb_version(lambda *a: got.append(a), tmp_path / "v.json", tmp_path / "none") is None
    assert got == []


# -- starting OpenRGB ------------------------------------------------------------

def test_openrgb_is_started_with_its_window(monkeypatch):
    calls = []
    shell32 = N(ShellExecuteW=lambda *a: calls.append(a) or 42)
    monkeypatch.setattr(boot.ctypes, "windll", N(shell32=shell32), raising=False)
    assert boot.launch_as_admin(Path("C:/x/OpenRGB.exe"), 6742) == "launched"
    params = calls[0][3].split()
    assert "--gui" in params and "--server" in params and "--startminimized" in params
    assert "--server-port" not in params


def test_custom_port_is_passed(monkeypatch):
    calls = []
    monkeypatch.setattr(boot.ctypes, "windll",
                        N(shell32=N(ShellExecuteW=lambda *a: calls.append(a) or 42)), raising=False)
    boot.launch_as_admin(Path("C:/x/OpenRGB.exe"), 7000)
    assert "--server-port 7000" in calls[0][3]


def test_not_installed_message_mentions_pawnio(monkeypatch):
    monkeypatch.setattr(boot, "is_port_open", lambda *a, **k: False)
    monkeypatch.setattr(boot, "is_openrgb_running", lambda: False)
    monkeypatch.setattr(boot, "find_openrgb", lambda s=None: None)
    settings = N(get_openrgb_host=lambda: "localhost", get_openrgb_port=lambda: 6742,
                 get_openrgb_autostart=lambda: True)
    res = boot.ensure_openrgb(settings)
    assert res["state"] == "not_found" and res["download_url"] == "https://openrgb.org"
    assert "PawnIO" in res["detail"]
