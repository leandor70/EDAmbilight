"""Interface language and network access are kept in settings.json."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from settings import Settings  # noqa: E402


def _settings(tmp_path):
    return Settings(str(tmp_path / "settings.json"))


def test_language_default_english_and_only_known_ones(tmp_path):
    s = _settings(tmp_path)
    assert s.get_language() == "en"
    s.set_language("it")
    assert _settings(tmp_path).get_language() == "it"
    s.set_language("klingon")
    assert _settings(tmp_path).get_language() == "en"


def test_remote_access_off_by_default(tmp_path):
    s = _settings(tmp_path)
    assert s.get_allow_remote_access() is False
    s.settings["allow_remote_access"] = "yes"          # only a real true counts
    assert s.get_allow_remote_access() is False
    s.set_allow_remote_access(True)
    assert _settings(tmp_path).get_allow_remote_access() is True


def test_api_round_trip(tmp_path, monkeypatch):
    from api import settings_api
    s = _settings(tmp_path)
    monkeypatch.setattr(settings_api, "_settings", s)
    assert settings_api.get_settings()["allow_remote_access"] is False
    assert settings_api.save_settings({"allow_remote_access": True, "language": "it"})["ok"]
    got = settings_api.get_settings()
    assert got["allow_remote_access"] is True and got["language"] == "it"
