"""The interface theme is kept in settings.json (ui_theme), not only in the browser."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from settings import Settings  # noqa: E402


def _settings(tmp_path):
    return Settings(str(tmp_path / "settings.json"))


def test_default_is_dark_and_unset(tmp_path):
    s = _settings(tmp_path)
    assert s.get_ui_theme() == "dark"
    assert s.has_ui_theme() is False


def test_theme_survives_a_restart(tmp_path):
    s = _settings(tmp_path)
    s.set_ui_theme("light")
    again = _settings(tmp_path)
    assert again.get_ui_theme() == "light"
    assert again.has_ui_theme() is True
    assert json.loads((tmp_path / "settings.json").read_text())["ui_theme"] == "light"


def test_garbage_value_falls_back_to_dark(tmp_path):
    s = _settings(tmp_path)
    s.set_ui_theme("neon")
    assert s.get_ui_theme() == "dark"


def test_api_reports_none_until_chosen_then_the_value(tmp_path, monkeypatch):
    from api import settings_api
    s = _settings(tmp_path)
    monkeypatch.setattr(settings_api, "_settings", s)
    assert settings_api.get_settings()["ui_theme"] is None
    assert settings_api.save_settings({"ui_theme": "light"}) == {"ok": True}
    assert settings_api.get_settings()["ui_theme"] == "light"
