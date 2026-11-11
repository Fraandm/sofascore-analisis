"""Caché persistente de simulaciones Monte Carlo.

Guarda el resumen JSON de cada simulación en disco para reaprovecharlo al
volver a abrir la aplicación. La clave incluye la versión del modelo, la
ventana, la semilla, las iteraciones, las alineaciones, el árbitro y los
partidos usados en el análisis; así un cambio de contexto invalida la caché.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

from . import __version__, neural, normalize

CACHE_TTL_SECONDS = 7 * 24 * 3600


def cache_dir() -> Path:
    """Directorio de caché de simulaciones del usuario."""
    if os.name == "nt":
        base = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "sofascore-gui" / "simulations"


def _target_dir(directory: Optional[Union[str, Path]]) -> Path:
    return Path(directory) if directory is not None else cache_dir()


def _lineup_ids(lineups: Optional[Dict[str, Any]]) -> Dict[str, list]:
    return {
        side: [
            str(player.get("id"))
            for player in normalize.lineup_starters(lineups, side)
            if player.get("id") is not None
        ]
        for side in ("home", "away")
    }


def _lineup_quality(lineups: Optional[Dict[str, Any]]) -> Dict[str, list]:
    return {
        side: [
            [
                str(player.get("id")),
                player.get("market_value"),
                player.get("avg_rating"),
            ]
            for player in normalize.lineup_starters(lineups, side)
        ]
        for side in ("home", "away")
    }


def fingerprint(
    analysis: Dict[str, Any],
    iterations: int,
    seed: Optional[int],
) -> str:
    """Huella estable del contexto que produce una simulación."""
    analysis = analysis or {}
    match = analysis.get("match") or {}
    lineups = analysis.get("lineups")
    referee = analysis.get("referee") or {}
    teams = analysis.get("teams") or {}
    event_ids = {}
    for side in ("home", "away"):
        rows = (teams.get(side) or {}).get("matches") or []
        event_ids[side] = sorted(
            str(row.get("event_id") or row.get("id"))
            for row in rows
            if row.get("event_id") is not None or row.get("id") is not None
        )
    payload = {
        "version": __version__,
        "neural_model": neural.model_version(),
        "match_id": match.get("id"),
        "start_timestamp": match.get("start_timestamp"),
        "window": analysis.get("window"),
        "season": (analysis.get("season") or {}).get("id"),
        "iterations": int(iterations),
        "seed": seed,
        "lineups": {
            "status": normalize.lineup_status(lineups),
            "starters": _lineup_ids(lineups),
            "quality": _lineup_quality(lineups),
        },
        "referee": {
            "id": referee.get("id"),
            "cards_per_match": referee.get("cards_per_match"),
            "fouls_per_match": referee.get("fouls_per_match"),
        },
        "standings": analysis.get("standings"),
        "h2h": analysis.get("h2h"),
        "events": event_ids,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:24]


def _cache_path(
    analysis: Dict[str, Any],
    iterations: int,
    seed: Optional[int],
    directory: Optional[Union[str, Path]] = None,
) -> Path:
    match_id = ((analysis or {}).get("match") or {}).get("id") or "match"
    digest = fingerprint(analysis, iterations, seed)
    return _target_dir(directory) / f"{match_id}-{digest}.json"


def load_simulation(
    analysis: Dict[str, Any],
    iterations: int,
    seed: Optional[int],
    directory: Optional[Union[str, Path]] = None,
    max_age: Optional[float] = CACHE_TTL_SECONDS,
) -> Optional[Dict[str, Any]]:
    """Devuelve el resumen cacheado o ``None`` si no existe o caducó."""
    path = _cache_path(analysis, iterations, seed, directory)
    try:
        if max_age is not None and time.time() - path.stat().st_mtime > max_age:
            return None
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("fingerprint") != fingerprint(analysis, iterations, seed):
        return None
    summary = payload.get("summary")
    return summary if isinstance(summary, dict) else None


def save_simulation(
    summary: Dict[str, Any],
    analysis: Dict[str, Any],
    iterations: int,
    seed: Optional[int],
    directory: Optional[Union[str, Path]] = None,
) -> Optional[Path]:
    """Guarda una simulación de forma atómica. No lanza errores de disco."""
    path = _cache_path(analysis, iterations, seed, directory)
    payload = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": fingerprint(analysis, iterations, seed),
        "summary": summary,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        os.replace(temporary, path)
        return path
    except OSError:
        return None


def clear_simulation_cache(
    directory: Optional[Union[str, Path]] = None,
) -> int:
    """Elimina las simulaciones guardadas y devuelve cuántas borró."""
    path = _target_dir(directory)
    if not path.exists():
        return 0
    count = 0
    for file in path.glob("*.json"):
        try:
            file.unlink()
            count += 1
        except OSError:
            continue
    for file in path.glob("*.tmp"):
        try:
            file.unlink()
        except OSError:
            pass
    return count


def cache_count(
    directory: Optional[Union[str, Path]] = None,
) -> int:
    path = _target_dir(directory)
    if not path.exists():
        return 0
    return sum(1 for _ in path.glob("*.json"))
