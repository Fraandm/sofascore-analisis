"""Preferencias compartidas por la interfaz web y la clásica."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


def config_dir() -> Path:
    if os.name == "nt":
        base = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "sofascore-gui"


def settings_path() -> Path:
    return config_dir() / "settings.json"


def load_preferences() -> Dict[str, Any]:
    """Devuelve las preferencias guardadas o un diccionario vacío."""
    try:
        with settings_path().open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_preferences(preferences: Dict[str, Any]) -> None:
    """Guarda las preferencias sin interrumpir la aplicación si falla el disco."""
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(preferences, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    except OSError:
        pass
