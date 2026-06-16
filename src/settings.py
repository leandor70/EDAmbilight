"""Settings management for EDAmbilight."""
import json
from pathlib import Path


class Settings:
    def __init__(self, config_file: str = "config/settings.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self._load()

    def _load(self) -> dict:
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save(self):
        self.config_file.write_text(
            json.dumps(self.settings, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get_openrgb_host(self) -> str:
        return self.settings.get("openrgb_host", "localhost")

    def get_openrgb_port(self) -> int:
        return int(self.settings.get("openrgb_port", 6742))

    def set_openrgb_connection(self, host: str, port: int):
        self.settings["openrgb_host"] = host
        self.settings["openrgb_port"] = int(port)
        self._save()

    def get_openrgb_path(self) -> str:
        """Manual override for portable installs ('' = autodetect)."""
        return self.settings.get("openrgb_path", "")

    def get_openrgb_autostart(self) -> bool:
        return bool(self.settings.get("openrgb_autostart", True))

    def get_web_port(self) -> int:
        return int(self.settings.get("web_port", 8001))

    def get_language(self) -> str:
        return self.settings.get("language", "en")

    def set_language(self, lang: str):
        self.settings["language"] = lang
        self._save()

    def get_theme(self) -> str:
        return self.settings.get("theme", "ambilight")

    def set_theme(self, theme: str):
        self.settings["theme"] = theme
        self._save()
