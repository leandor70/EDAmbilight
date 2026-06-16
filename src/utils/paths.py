"""Path resolution for EDAmbilight (dev vs PyInstaller frozen)."""
import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # src/utils/paths.py -> src/utils/ -> src/ -> project root
    return Path(__file__).parent.parent.parent
