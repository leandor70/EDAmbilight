"""New version notice: GitHub's answer, once a day, skip / close, switched off, no network."""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from settings import Settings                                   # noqa: E402
from utils import update_check as uc                             # noqa: E402


def _settings(tmp_path):
    return Settings(str(tmp_path / "settings.json"))


class _Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def _fetch(version="1.7.0", calls=None):
    def f(current):
        if calls is not None:
            calls.append(current)
        return None if version is None else {"version": version, "url": f"{uc.RELEASES_URL}/tag/v{version}"}
    return f


def test_versions():
    assert uc.parse_version("v1.6.1") == (1, 6, 1)
    assert uc.parse_version("1.7") == (1, 7, 0)
    assert uc.parse_version("v1.7.0-rc1") is None
    assert uc.is_newer("v1.10.0", "1.9.3")
    assert not uc.is_newer("1.6.1", "1.6.1")
    assert not uc.is_newer("1.6.0", "1.6.1")
    assert not uc.is_newer("garbage", "1.6.1")


def _opener(payload):
    class _Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def open_(req, timeout):
        assert req.full_url == uc.API_URL and timeout == uc.TIMEOUT_S
        assert req.get_header("User-agent").startswith("EDAmbilight/")
        if isinstance(payload, Exception):
            raise payload
        return _Resp(json.dumps(payload).encode())
    return open_


def test_fetch_reads_the_latest_release():
    got = uc.fetch_latest("1.6.1", _opener({"tag_name": "v1.7.0",
                                            "html_url": "https://github.com/leandor70/EDAmbilight/releases/tag/v1.7.0"}))
    assert got == {"version": "1.7.0", "url": "https://github.com/leandor70/EDAmbilight/releases/tag/v1.7.0"}


def test_fetch_ignores_odd_answers_and_foreign_links():
    assert uc.fetch_latest("1.6.1", _opener(OSError("offline"))) is None
    assert uc.fetch_latest("1.6.1", _opener({"tag_name": "nightly"})) is None
    assert uc.fetch_latest("1.6.1", _opener({"tag_name": "v1.7.0", "prerelease": True})) is None
    got = uc.fetch_latest("1.6.1", _opener({"tag_name": "v1.7.0", "html_url": "https://evil.example/x"}))
    assert got["url"] == f"{uc.RELEASES_URL}/tag/v1.7.0"


def test_a_newer_version_shows_the_notice(tmp_path):
    c = uc.UpdateChecker(_settings(tmp_path), "1.6.1", _fetch("1.7.0"), _Clock())
    c.check()
    info = c.info()
    assert info["show"] and info["newer"] and info["latest"] == "1.7.0"
    assert info["url"].endswith("/tag/v1.7.0")


def test_same_or_older_version_shows_nothing(tmp_path):
    for v in ("1.6.1", "1.5.0"):
        c = uc.UpdateChecker(_settings(tmp_path / v), "1.6.1", _fetch(v), _Clock())
        c.check()
        assert not c.info()["show"]


def test_at_most_once_a_day_and_the_answer_is_kept(tmp_path):
    s, clock, calls = _settings(tmp_path), _Clock(), []
    c = uc.UpdateChecker(s, "1.6.1", _fetch("1.7.0", calls), clock)
    c.check()
    clock.t += 3600
    c2 = uc.UpdateChecker(Settings(str(tmp_path / "settings.json")), "1.6.1", _fetch("1.7.0", calls), clock)
    c2.check()                                   # next start, an hour later: no request
    assert len(calls) == 1 and c2.info()["show"]
    clock.t += uc.CHECK_EVERY_S
    c2.check()
    assert len(calls) == 2


def test_no_network_tries_again_next_time(tmp_path):
    s, calls = _settings(tmp_path), []
    c = uc.UpdateChecker(s, "1.6.1", _fetch(None, calls), _Clock())
    c.check()
    c.check()
    assert len(calls) == 2 and not c.info()["show"] and c.info()["error"]


def test_close_until_next_start_skip_for_good(tmp_path):
    s = _settings(tmp_path)
    c = uc.UpdateChecker(s, "1.6.1", _fetch("1.7.0"), _Clock())
    c.check()
    c.close()
    assert not c.info()["show"]
    again = uc.UpdateChecker(Settings(str(tmp_path / "settings.json")), "1.6.1", _fetch("1.7.0"), _Clock())
    assert again.info()["show"]                  # closed: back at the next start
    again.close(skip=True)
    later = uc.UpdateChecker(Settings(str(tmp_path / "settings.json")), "1.6.1", _fetch("1.8.0"), _Clock())
    assert not later.info()["show"]              # 1.7.0 skipped for good
    later.check(force=True)
    assert later.info()["show"] and later.info()["latest"] == "1.8.0"   # a newer one is shown


def test_switched_off_asks_nothing_and_shows_nothing(tmp_path):
    s, calls = _settings(tmp_path), []
    c = uc.UpdateChecker(s, "1.6.1", _fetch("1.7.0", calls), _Clock())
    c.set_enabled(False)
    c.check()
    assert calls == [] and not c.info()["show"]
    c.check(force=True)                          # "Check now" still works
    assert calls and c.info()["newer"] and not c.info()["show"]
