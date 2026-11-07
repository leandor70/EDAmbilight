"""Which OpenRGB is running, and a one-time notice when it is older than 1.0.

The SDK protocol does not report the application version, so it is read from
the header of the newest OpenRGB log (%APPDATA%\\OpenRGB\\logs), which starts with
a line such as:

    OpenRGB v0.9+ (1.0rc2)
    OpenRGB v1.1

This is best effort: no log (remote OpenRGB, portable copy with its own config
folder) simply means no notice.
"""

import json
import os
import re
from pathlib import Path
from typing import Callable, Optional, Tuple

_HEADER_LINES = 15
_PRERELEASE = ("rc", "beta", "alpha", "pre", "dev")


def default_log_dir() -> Optional[Path]:
    appdata = os.environ.get("APPDATA")
    return Path(appdata) / "OpenRGB" / "logs" if appdata else None


def read_version_text(log_dir: Optional[Path] = None) -> Optional[str]:
    """The 'v0.9+ (1.0rc2)' part of the newest log's header, or None."""
    folder = log_dir if log_dir is not None else default_log_dir()
    if folder is None or not folder.is_dir():
        return None
    logs = sorted(folder.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return None
    try:
        with logs[0].open("r", encoding="utf-8", errors="replace") as f:
            for _ in range(_HEADER_LINES):
                line = f.readline().strip()
                if re.match(r"OpenRGB\s+v\d", line, re.I):
                    return line[len("OpenRGB"):].strip()
    except OSError:
        return None
    return None


def parse_version(text: str) -> Optional[Tuple[int, int, bool, str]]:
    """(major, minor, is_prerelease, label) from 'v1.1' or 'v0.9+ (1.0rc2)'.

    A version in parentheses wins: 'v0.9+ (1.0rc2)' is the 1.0 release candidate.
    """
    paren = re.search(r"\(([^)]*)\)", text)
    core = paren.group(1) if paren and re.search(r"\d+\.\d+", paren.group(1)) else text
    m = re.search(r"(\d+)\.(\d+)(?:\.\d+)?\s*([A-Za-z][\w.-]*)?", core)
    if not m:
        return None
    major, minor, suffix = int(m.group(1)), int(m.group(2)), (m.group(3) or "")
    prerelease = suffix.lower().startswith(_PRERELEASE)
    return major, minor, prerelease, f"{major}.{minor}{suffix}"


def is_older_than_1_0(major: int, minor: int, prerelease: bool) -> bool:
    return (major, minor) < (1, 0) or ((major, minor) == (1, 0) and prerelease)


def _seen(state_file: Path) -> Optional[str]:
    try:
        return json.loads(state_file.read_text(encoding="utf-8")).get("notified")
    except Exception:
        return None


def _remember(state_file: Path, label: str) -> None:
    try:
        state_file.write_text(json.dumps({"notified": label}), encoding="utf-8")
    except OSError:
        pass


def check_openrgb_version(add_notice: Callable[[str, str, str], None], state_file: Path,
                          log_dir: Optional[Path] = None) -> Optional[str]:
    """Notify once per detected version when OpenRGB is older than 1.0.

    Returns the detected version label, or None when it could not be read.
    """
    text = read_version_text(log_dir)
    parsed = parse_version(text) if text else None
    if parsed is None:
        return None
    major, minor, prerelease, label = parsed
    if is_older_than_1_0(major, minor, prerelease) and _seen(state_file) != label:
        add_notice(
            "version", "OpenRGB",
            f"OpenRGB {label} detected. Version 1.0 or later is recommended: it identifies "
            f"hardware more accurately and fixes bugs. Get it from openrgb.org. On Windows it "
            f"also needs the PawnIO driver (pawnio.eu) to reach memory and motherboards.",
        )
        _remember(state_file, label)
    return label
