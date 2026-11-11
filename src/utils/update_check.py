"""Is there a newer EDAmbilight on GitHub? A notice with a link, never an automatic update.

At startup (in the background) the app asks GitHub for the latest release of
leandor70/EDAmbilight, at most once a day; between two checks the answer saved
in config/settings.json is used. The pages show a toast with a link to the
release page when that version is newer than the running one, until the user
closes it (until the next start) or skips that version (for good).

It is the only connection to the internet the app makes: GitHub sees the IP
address and nothing else (no account, no token, no data about the PC). It can
be switched off in Settings. No network, a timeout or any odd answer just means
no notice.
"""

import json
import re
import threading
import time
import urllib.request
from typing import Callable, Optional, Tuple

REPO = "leandor70/EDAmbilight"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases"
CHECK_EVERY_S = 24 * 3600
TIMEOUT_S = 6


def parse_version(text) -> Optional[Tuple[int, ...]]:
    """(1, 6, 1) from "v1.6.1" or "1.6.1"; None for anything else (pre-releases included)."""
    m = re.fullmatch(r"\s*v?(\d+)\.(\d+)(?:\.(\d+))?\s*", str(text or ""))
    if not m:
        return None
    return tuple(int(g or 0) for g in m.groups())


def is_newer(remote, local) -> bool:
    r, l = parse_version(remote), parse_version(local)
    return bool(r and l and r > l)


def _release_url(url, version: str) -> str:
    """The page GitHub gave, if it really is a page of this repo; else the tag's page."""
    if isinstance(url, str) and url.startswith(f"https://github.com/{REPO}/releases/"):
        return url
    return f"{RELEASES_URL}/tag/v{version}"


def fetch_latest(current: str, opener: Callable = urllib.request.urlopen) -> Optional[dict]:
    """{"version", "url"} of the latest published release, or None."""
    req = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"EDAmbilight/{current}",
    })
    try:
        with opener(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read(256 * 1024).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    tag = str(data.get("tag_name", ""))
    if not parse_version(tag):
        return None
    version = tag.strip().lstrip("v")
    return {"version": version, "url": _release_url(data.get("html_url"), version)}


class UpdateChecker:
    """Holds the answer for the pages. `settings` is the app's Settings object."""

    def __init__(self, settings, current: str, fetch: Callable = fetch_latest,
                 clock: Callable[[], float] = time.time):
        self._settings = settings
        self._current = current
        self._fetch = fetch
        self._clock = clock
        self._lock = threading.Lock()
        self._closed = False             # closed with "Later": until the next start
        self._last_error = False

    # ── settings ─────────────────────────────────────────────────────────────
    @property
    def _s(self) -> dict:
        return self._settings.settings

    def enabled(self) -> bool:
        return bool(self._s.get("update_check", True))

    def set_enabled(self, on: bool) -> None:
        self._s["update_check"] = bool(on)
        self._settings._save()

    # ── checking ─────────────────────────────────────────────────────────────
    def check(self, force: bool = False) -> None:
        """Ask GitHub, unless it was asked less than a day ago (force: ask now)."""
        if not self.enabled() and not force:
            return
        with self._lock:
            last = float(self._s.get("update_checked_at", 0) or 0)
            if not force and 0 <= self._clock() - last < CHECK_EVERY_S:
                return
            latest = self._fetch(self._current)
            self._last_error = latest is None
            if latest is None:
                return                   # try again at the next start
            self._s["update_latest"] = latest
            self._s["update_checked_at"] = int(self._clock())
            self._settings._save()

    def check_in_background(self) -> None:
        threading.Thread(target=self.check, name="update-check", daemon=True).start()

    # ── what the pages show ──────────────────────────────────────────────────
    def info(self) -> dict:
        latest = self._s.get("update_latest") if isinstance(self._s.get("update_latest"), dict) else {}
        version = str(latest.get("version", ""))
        newer = is_newer(version, self._current)
        skipped = version and version == self._s.get("update_skip_version")
        return {
            "current": self._current,
            "latest": version or None,
            "url": _release_url(latest.get("url"), version) if version else RELEASES_URL,
            "newer": newer,
            "show": bool(self.enabled() and newer and not skipped and not self._closed),
            "checked_at": self._s.get("update_checked_at"),
            "error": self._last_error,
        }

    def close(self, skip: bool = False) -> None:
        """Hide the toast: until the next start, or for good for this version (skip)."""
        self._closed = True
        if skip:
            version = (self._s.get("update_latest") or {}).get("version")
            if version:
                self._s["update_skip_version"] = version
                self._settings._save()
