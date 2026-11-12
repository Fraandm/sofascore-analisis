"""Aplicación web local de SofaScore.

El motor de datos, análisis, simulación e historial es el mismo que usa la
interfaz clásica de Tkinter. Esta capa sirve una interfaz HTML5/CSS/JS en
``127.0.0.1`` y la abre en una ventana de Microsoft Edge en modo aplicación.

No requiere dependencias nuevas: usa ``http.server`` y el cliente HTTP que ya
forma parte del proyecto.
"""

from __future__ import annotations

import argparse
import io
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import webbrowser
import zipfile
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import urlopen

from . import (
    __version__,
    export,
    form,
    neural,
    normalize,
    preview,
    regions,
    simulation,
    simulation_cache,
    storage,
)
from .client import ClientConfig, SofaScoreClient
from .exceptions import SofaScoreError
from .extractor import SofaScoreExtractor, parse_day, resolve_timezone
from .settings import config_dir, load_preferences, save_preferences

WEB_DIR = Path(__file__).resolve().parent / "web_ui"
PREVIEW_DIR = Path(tempfile.gettempdir()) / "sofascore-previews"

TOP_LEAGUES = (
    (17, "Premier League", ("premier league",)),
    (8, "LaLiga", ("laliga", "la liga")),
    (23, "Serie A", ("serie a",)),
    (35, "Bundesliga", ("bundesliga",)),
    (34, "Ligue 1", ("ligue 1",)),
)
TOP_LEAGUE_IDS = {
    tournament_id: index
    for index, (tournament_id, _, _) in enumerate(TOP_LEAGUES)
}

TIMEZONES = (
    "local",
    "UTC",
    "Europe/Madrid",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Lisbon",
    "Europe/Istanbul",
    "America/Mexico_City",
    "America/Bogota",
    "America/Lima",
    "America/Santiago",
    "America/Argentina/Buenos_Aires",
    "America/Sao_Paulo",
    "America/Montevideo",
    "America/Asuncion",
    "America/La_Paz",
    "America/Caracas",
    "America/Guayaquil",
)

THEME_KEYS = {
    "light",
    "dark",
    "midnight",
    "forest",
    "ocean",
    "sunset",
    "contrast",
}
DARK_THEME_KEYS = {"dark", "midnight", "forest", "contrast"}

MODEL_TARGETS = (
    ("home_goals", "Goles local"),
    ("away_goals", "Goles visitante"),
    ("home_shots", "Remates local"),
    ("away_shots", "Remates visitante"),
    ("home_shots_on_target", "Al arco local"),
    ("away_shots_on_target", "Al arco visitante"),
    ("home_corners", "Córners local"),
    ("away_corners", "Córners visitante"),
    ("home_cards", "Tarjetas local"),
    ("away_cards", "Tarjetas visitante"),
    ("home_fouls", "Faltas local"),
    ("away_fouls", "Faltas visitante"),
)


def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def top_league_index(match: Dict[str, Any]) -> Optional[int]:
    tournament = (match or {}).get("tournament") or {}
    try:
        tournament_id = int(tournament.get("id"))
    except (TypeError, ValueError):
        tournament_id = None
    if tournament_id in TOP_LEAGUE_IDS:
        return TOP_LEAGUE_IDS[tournament_id]
    name = normalize.normalize_text(tournament.get("name") or "")
    for index, (_, _, aliases) in enumerate(TOP_LEAGUES):
        if name in aliases:
            return index
    return None


def match_section(match: Dict[str, Any]) -> str:
    if top_league_index(match) is not None:
        return "top"
    region = (match or {}).get("region") or regions.region_for_match(match or {})
    if region == regions.REGION_SOUTH_AMERICA:
        return "south"
    if region == regions.REGION_NATIONAL:
        return "national"
    return "other"


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    try:
        import numpy as np  # type: ignore

        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
    except Exception:  # noqa: BLE001 - numpy es opcional aquí
        pass
    return str(value)


def _merge_matches(
    base: Sequence[Dict[str, Any]], extra: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    merged: Dict[Any, Dict[str, Any]] = {
        match.get("id"): dict(match) for match in base if match.get("id") is not None
    }
    order = [match.get("id") for match in base if match.get("id") is not None]
    for match in extra:
        match_id = match.get("id")
        if match_id is None:
            continue
        if match_id in merged:
            merged[match_id].update(match)
        else:
            merged[match_id] = dict(match)
            order.append(match_id)
    return [merged[match_id] for match_id in order if match_id in merged]


class JobManager:
    """Cola mínima de trabajos con progreso consultable."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        kind: str,
        function: Callable[[Callable[[int, int, str], None]], Any],
    ) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        job: Dict[str, Any] = {
            "id": job_id,
            "kind": kind,
            "status": "running",
            "progress": {"done": 0, "total": 1, "message": "Preparando…"},
            "created_at": time.time(),
        }
        with self._lock:
            self._cleanup_locked()
            self._jobs[job_id] = job

        def report(done: int, total: int, message: str) -> None:
            with self._lock:
                current = self._jobs.get(job_id)
                if current is None:
                    return
                current["progress"] = {
                    "done": int(done or 0),
                    "total": max(1, int(total or 1)),
                    "message": str(message or ""),
                }

        def run() -> None:
            try:
                result = function(report)
            except BaseException as exc:  # noqa: BLE001 - se devuelve al cliente
                with self._lock:
                    current = self._jobs.get(job_id)
                    if current is not None:
                        current["status"] = "error"
                        current["error"] = str(exc) or exc.__class__.__name__
                        current["finished_at"] = time.time()
                return
            with self._lock:
                current = self._jobs.get(job_id)
                if current is not None:
                    current["status"] = "done"
                    current["result"] = result
                    current["finished_at"] = time.time()

        threading.Thread(target=run, daemon=True, name=f"job-{kind}").start()
        return dict(job)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return json.loads(json.dumps(job, default=_json_default)) if job else None

    def _cleanup_locked(self) -> None:
        if len(self._jobs) < 80:
            return
        cutoff = time.time() - 1800
        for key in [
            key
            for key, job in self._jobs.items()
            if (job.get("finished_at") or job.get("created_at") or 0) < cutoff
        ]:
            self._jobs.pop(key, None)


class WebService:
    """Lógica de la aplicación web, independiente del servidor HTTP."""

    def __init__(
        self,
        client: Optional[SofaScoreClient] = None,
        extractor: Optional[SofaScoreExtractor] = None,
        store: Optional[storage.HistoryStore] = None,
        workers: int = 6,
    ) -> None:
        self.client = client or SofaScoreClient(ClientConfig(rate_limit=0.08))
        self.extractor = extractor or SofaScoreExtractor(self.client, workers=workers)
        self.storage: Optional[storage.HistoryStore] = None
        self.storage_error = ""
        try:
            self.storage = store or storage.HistoryStore()
        except Exception as exc:  # noqa: BLE001 - la web sigue funcionando
            self.storage_error = str(exc)
        self.jobs = JobManager()
        self.preferences = load_preferences()
        self._lock = threading.Lock()
        self._day_cache: Dict[Tuple[Any, ...], Tuple[float, List[Dict[str, Any]]]] = {}
        self._analysis_cache: Dict[Tuple[int, str], Tuple[float, Dict[str, Any]]] = {}
        self._last_simulations: Dict[int, Dict[str, Any]] = {}
        self._image_locks: Dict[Tuple[str, int], threading.Lock] = {}

    # ------------------------------------------------------------------
    # Preferencias y estado general
    # ------------------------------------------------------------------
    def _default_preferences(self) -> Dict[str, Any]:
        return {
            "dark": False,
            "theme": "light",
            "auto_live": True,
            "alerts": True,
            "auto_analyze": True,
            "timezone": "local",
            "region": "ambas",
            "competitions": "principales",
        }

    def preferences_snapshot(self) -> Dict[str, Any]:
        data = self._default_preferences()
        data.update(
            {
                key: value
                for key, value in (self.preferences or {}).items()
                if key in {
                    "dark",
                    "theme",
                    "auto_live",
                    "alerts",
                    "auto_analyze",
                    "timezone",
                    "region",
                    "competitions",
                }
            }
        )
        theme = (self.preferences or {}).get("theme")
        if theme not in THEME_KEYS:
            theme = "dark" if (self.preferences or {}).get("dark") else "light"
        data["theme"] = theme
        data["dark"] = theme in DARK_THEME_KEYS
        favorites = (self.preferences or {}).get("favorites") or {}
        if not isinstance(favorites, dict):
            favorites = {}
        data["favorites"] = {
            str(key): str(value) for key, value in favorites.items()
        }
        return data

    def update_preferences(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {
            "dark",
            "theme",
            "auto_live",
            "alerts",
            "auto_analyze",
            "timezone",
            "region",
            "competitions",
        }
        if payload.get("theme") in THEME_KEYS:
            self.preferences["theme"] = payload["theme"]
            self.preferences["dark"] = payload["theme"] in DARK_THEME_KEYS
        for key in allowed:
            if key not in payload:
                continue
            value = payload[key]
            if key == "theme":
                continue
            if key == "dark":
                if "theme" not in payload:
                    self.preferences["dark"] = bool(value)
                    self.preferences["theme"] = (
                        "dark" if bool(value) else "light"
                    )
            elif key in ("auto_live", "alerts", "auto_analyze"):
                self.preferences[key] = bool(value)
            elif key == "timezone":
                self.preferences[key] = (
                    value if value in TIMEZONES else "local"
                )
            elif key == "region":
                self.preferences[key] = regions.normalize_region(value)
            elif key == "competitions":
                self.preferences[key] = (
                    value if value in ("principales", "todas") else "principales"
                )
        save_preferences(self.preferences)
        return self.preferences_snapshot()

    def toggle_favorite(
        self, team_id: Any, name: Any, favorite: Optional[bool] = None
    ) -> Dict[str, Any]:
        raw_id = _safe_int(team_id)
        if raw_id is None:
            raise ValueError("El equipo indicado no es válido.")
        favorites = dict((self.preferences or {}).get("favorites") or {})
        key = str(raw_id)
        if favorite is None:
            favorite = key not in favorites
        if favorite:
            favorites[key] = str(name or raw_id)
        else:
            favorites.pop(key, None)
        self.preferences["favorites"] = favorites
        save_preferences(self.preferences)
        return {
            "favorites": {
                str(key): str(value) for key, value in favorites.items()
            },
            "team_id": raw_id,
            "favorite": bool(favorite),
        }

    def model_info(self) -> Dict[str, Any]:
        root = Path(__file__).resolve().parents[1]
        metrics_path = root / "training" / "metrics.json"
        model_path = root / "sofascore" / "models" / "neural_model.npz"
        metrics: Dict[str, Any] = {}
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            metrics = {}
        neural_mae = metrics.get("test_mae_neural") or []
        baseline_mae = metrics.get("test_mae_baseline") or []
        targets = []
        for index, (key, label) in enumerate(MODEL_TARGETS):
            targets.append(
                {
                    "key": key,
                    "label": label,
                    "neural": neural_mae[index] if index < len(neural_mae) else None,
                    "baseline": baseline_mae[index]
                    if index < len(baseline_mae)
                    else None,
                }
            )
        try:
            stat = model_path.stat()
            model_file = {
                "path": str(model_path),
                "size": stat.st_size,
                "updated_at": datetime.fromtimestamp(
                    stat.st_mtime
                ).isoformat(),
            }
        except OSError:
            model_file = {}
        return {
            "version": neural.model_version(),
            "app_version": __version__,
            "metrics": metrics,
            "targets": targets,
            "model": model_file,
            "blend_weights": metrics.get("blend_weights") or {},
        }

    def bootstrap(self) -> Dict[str, Any]:
        prefs = self.preferences_snapshot()
        predictions = 0
        accuracy: Dict[str, Any] = {}
        if self.storage is not None:
            try:
                predictions = self.storage.count_predictions()
                accuracy = self.storage.accuracy()
            except Exception:
                predictions = 0
        return {
            "version": __version__,
            "today": date.today().isoformat(),
            "preferences": prefs,
            "timezones": list(TIMEZONES),
            "regions": [
                {"key": "ambas", "label": "Todas"},
                {"key": "europa", "label": "Europa"},
                {"key": "sudamerica", "label": "Sudamérica"},
                {"key": "selecciones", "label": "Selecciones"},
            ],
            "competitions": [
                {"key": "principales", "label": "Competiciones principales"},
                {"key": "todas", "label": "Todas las competiciones"},
            ],
            "storage": {
                "available": self.storage is not None,
                "path": str(self.storage.path) if self.storage else "",
                "error": self.storage_error,
                "predictions": predictions,
            },
            "accuracy": accuracy,
            "model": self.model_info(),
            "data_dir": str(config_dir()),
            "images_dir": str(config_dir() / "images"),
            "shortcuts": [
                {"keys": "Ctrl + K", "action": "Buscar partido"},
                {"keys": "Ctrl + G", "action": "Buscar equipo"},
                {"keys": "Ctrl + R", "action": "Recargar fecha"},
                {"keys": "Ctrl + D", "action": "Cambiar tema"},
                {"keys": "Ctrl + Shift + L", "action": "Sala de directo"},
                {"keys": "Ctrl + Shift + P", "action": "Cuaderno"},
                {"keys": "Ctrl + Shift + R", "action": "Estudio de previas"},
                {"keys": "Ctrl + Shift + D", "action": "Explorador"},
                {"keys": "Ctrl + Shift + E", "action": "Exportar análisis JSON"},
                {"keys": "F1", "action": "Ayuda"},
            ],
        }

    # ------------------------------------------------------------------
    # Partidos
    # ------------------------------------------------------------------
    def _decorate_match(
        self, match: Dict[str, Any], timezone_name: str = "local"
    ) -> Dict[str, Any]:
        result = dict(match)
        result["section"] = match_section(result)
        try:
            result["minute"] = round(float(form.match_minute(result)), 1)
        except Exception:
            result["minute"] = 0.0
        if not result.get("start_time_local"):
            timestamp = result.get("start_timestamp")
            if timestamp is not None:
                try:
                    tz = resolve_timezone(timezone_name)
                    result["start_time_local"] = datetime.fromtimestamp(
                        int(timestamp), tz=tz
                    ).isoformat()
                except Exception:
                    pass
        tournament = result.get("tournament") or {}
        result["league_id"] = tournament.get("id")
        result["league_name"] = tournament.get("name")
        result["category_id"] = tournament.get("category_id")
        result["top_index"] = top_league_index(result)
        return result

    def _initial_tournament(self, entry: Dict[str, Any]) -> bool:
        tournament_id = _safe_int(entry.get("unique_tournament_id"))
        return (
            tournament_id in TOP_LEAGUE_IDS
            or regions.normalize_region(entry.get("region")) == "sudamerica"
            or regions.normalize_region(entry.get("region")) == "selecciones"
        )

    def _remaining_tournament(self, entry: Dict[str, Any]) -> bool:
        return not self._initial_tournament(entry)

    def list_day(
        self,
        day: Optional[str] = None,
        region: str = "",
        competitions: str = "",
        timezone_name: str = "",
        stage: str = "all",
        refresh: bool = False,
    ) -> Dict[str, Any]:
        from . import upcoming  # import local para mantener el módulo ligero

        parsed_day = parse_day(day or "hoy")
        prefs = self.preferences_snapshot()
        region = regions.normalize_region(region or prefs.get("region") or "ambas")
        competitions = competitions or prefs.get("competitions") or "principales"
        if competitions not in ("principales", "todas"):
            competitions = "principales"
        timezone_name = timezone_name or prefs.get("timezone") or "local"
        stage = stage if stage in ("initial", "rest", "all") else "all"
        key = (parsed_day, region, competitions, timezone_name, stage)
        now = time.time()
        with self._lock:
            cached = self._day_cache.get(key)
            if (
                cached is not None
                and not refresh
                and now - cached[0] < 180
            ):
                matches = [dict(item) for item in cached[1]]
                return {
                    "day": parsed_day,
                    "matches": matches,
                    "count": len(matches),
                    "stage": stage,
                    "partial": stage in ("initial", "rest"),
                    "cached": True,
                }

        tournament_filter = None
        if stage == "initial":
            tournament_filter = self._initial_tournament
        elif stage == "rest":
            tournament_filter = self._remaining_tournament

        matches = upcoming.list_upcoming(
            self.extractor,
            parsed_day,
            region=region,
            competitions=competitions,
            limit=500,
            timezone_name=timezone_name,
            include_finished=True,
            include_live=True,
            tournament_filter=tournament_filter,
        )
        decorated = [
            self._decorate_match(match, timezone_name) for match in matches
        ]
        with self._lock:
            self._day_cache[key] = (time.time(), decorated)
            if stage == "all":
                for other_key in list(self._day_cache):
                    if other_key[:4] == key[:4] and other_key != key:
                        self._day_cache.pop(other_key, None)
        if self.storage is not None:
            try:
                self.storage.save_matches(decorated, parsed_day)
            except Exception:
                pass
        return {
            "day": parsed_day,
            "matches": decorated,
            "count": len(decorated),
            "stage": stage,
            "partial": stage in ("initial", "rest"),
            "cached": False,
        }

    def live_updates(self, current_ids: Sequence[int] = ()) -> Dict[str, Any]:
        live = self.extractor.get_live_matches()
        updates = {
            match.get("id"): match for match in live if match.get("id") is not None
        }
        missing = [
            match_id for match_id in current_ids if match_id not in updates
        ][:6]
        for match_id in missing:
            try:
                detail = self.extractor.get_match(int(match_id))
            except Exception:
                continue
            updated = (detail or {}).get("match")
            if updated:
                updates[match_id] = updated
        prefs = self.preferences_snapshot()
        timezone_name = prefs.get("timezone") or "local"
        decorated = [
            self._decorate_match(match, timezone_name)
            for match in updates.values()
        ]
        if self.storage is not None:
            try:
                for match in decorated:
                    self.storage.update_match_result(match)
            except Exception:
                pass
        return {"matches": decorated, "count": len(decorated), "fetched_at": time.time()}

    def match_detail(self, match_id: int) -> Dict[str, Any]:
        detail = self.extractor.get_match(int(match_id), sections=["lineups"])
        match = detail.get("match")
        if not match:
            raise SofaScoreError("El partido no está disponible.")
        prefs = self.preferences_snapshot()
        decorated = self._decorate_match(match, prefs.get("timezone") or "local")
        if self.storage is not None:
            try:
                self.storage.save_match(decorated)
            except Exception:
                pass
        return {
            "match": decorated,
            "lineups": detail.get("lineups"),
        }

    # ------------------------------------------------------------------
    # Análisis y simulación
    # ------------------------------------------------------------------
    def _analysis_key(self, match_id: int, window: Any) -> Tuple[int, str]:
        return (int(match_id), str(window if window is not None else "all"))

    def analyze(
        self,
        match_id: int,
        window: Any = 10,
        progress: Optional[Callable[[int, int, str], None]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        key = self._analysis_key(match_id, window)
        with self._lock:
            cached = self._analysis_cache.get(key)
        if cached is not None and not force:
            age = time.time() - cached[0]
            status = ((cached[1].get("match") or {}).get("status_type"))
            ttl = 25 if status in ("inprogress", "live", "halftime") else 900
            if age < ttl:
                return cached[1]

        if progress:
            progress(0, 1, "Preparando el análisis…")
        analysis = form.analyze_match(
            self.extractor,
            int(match_id),
            window=window,
            progress=progress,
            include_lineups=True,
            include_referee=True,
            include_context=True,
        )
        with self._lock:
            self._analysis_cache[key] = (time.time(), analysis)
        if self.storage is not None:
            try:
                self.storage.save_analysis(analysis)
                match = analysis.get("match") or {}
                if match:
                    self.storage.save_match(
                        self._decorate_match(
                            match,
                            self.preferences_snapshot().get("timezone") or "local",
                        )
                    )
            except Exception:
                pass
        return analysis

    def analysis_cached(
        self, match_id: int, window: Any = 10
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            cached = self._analysis_cache.get(self._analysis_key(match_id, window))
        return cached[1] if cached else None

    def simulate(
        self,
        match_id: int,
        window: Any = 10,
        iterations: int = simulation.DEFAULT_ITERATIONS,
        seed: Optional[int] = 42,
        use_cache: bool = True,
        progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        try:
            iterations = int(iterations)
        except (TypeError, ValueError):
            raise ValueError("El número de simulaciones debe ser un entero.")
        if not (
            simulation.MIN_ITERATIONS
            <= iterations
            <= simulation.MAX_ITERATIONS
        ):
            raise ValueError(
                f"Usa entre {simulation.MIN_ITERATIONS:,} y "
                f"{simulation.MAX_ITERATIONS:,} simulaciones."
            )
        if seed in ("", None):
            seed = None
        else:
            try:
                seed = int(seed)
            except (TypeError, ValueError):
                raise ValueError("La semilla debe ser un número entero.")
        if progress:
            progress(0, 3, "Comprobando el análisis del partido…")
        analysis = self.analyze(match_id, window, progress=progress, force=False)
        cached_summary = None
        if use_cache:
            cached_summary = simulation_cache.load_simulation(
                analysis, iterations, seed
            )
        if cached_summary is not None:
            summary = dict(cached_summary)
            if analysis.get("actual") is not None:
                summary["actual"] = analysis["actual"]
            if progress:
                progress(3, 3, "Simulación recuperada de la caché.")
        else:
            if progress:
                progress(1, 3, "Modelando intensidades y dispersión…")
            summary = simulation.simulate_match(
                analysis, iterations=iterations, seed=seed
            )
            if progress:
                progress(2, 3, "Guardando la simulación…")
            simulation_cache.save_simulation(
                summary, analysis, iterations, seed
            )
        stored = dict(summary)
        meta = dict(stored.get("meta") or {})
        meta["model_version"] = __version__
        stored["meta"] = meta
        prediction_id = None
        if self.storage is not None:
            try:
                prediction_id = self.storage.save_prediction(stored, analysis)
            except Exception:
                prediction_id = None
        match_id_value = _safe_int((summary.get("meta") or {}).get("match_id"))
        if match_id_value is not None:
            with self._lock:
                self._last_simulations[match_id_value] = summary
        if progress:
            progress(3, 3, "Simulación lista.")
        return {
            "summary": summary,
            "cached": cached_summary is not None,
            "prediction_id": prediction_id,
            "iterations": iterations,
            "seed": seed,
        }

    def preview_payload(
        self,
        match_id: int,
        window: Any = 10,
        force: bool = False,
        progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        analysis = self.analyze(
            match_id, window, force=force, progress=progress
        )
        summary = None
        if self.storage is not None:
            try:
                summary = self.storage.latest_prediction_payload(int(match_id))
            except Exception:
                summary = None
        if not summary:
            with self._lock:
                summary = self._last_simulations.get(int(match_id))
        result = preview.build_preview(analysis, summary)
        result["html"] = preview.render_html(analysis, summary)
        result["markdown"] = result.get("markdown") or ""
        result["analysis_meta"] = {
            "match_id": match_id,
            "window": analysis.get("window"),
            "generated_at": analysis.get("generated_at"),
            "warnings": analysis.get("warnings") or [],
        }
        return result

    # ------------------------------------------------------------------
    # Historial, equipos y exportaciones
    # ------------------------------------------------------------------
    def history_matches(
        self, query: str = "", status: str = "", limit: int = 500
    ) -> List[Dict[str, Any]]:
        if self.storage is None:
            return []
        return self.storage.list_matches(
            query=query, status=status, limit=max(1, min(5000, int(limit)))
        )

    def history_predictions(self, limit: int = 1000) -> List[Dict[str, Any]]:
        if self.storage is None:
            return []
        return self.storage.list_predictions(limit=max(1, min(5000, int(limit))))

    def accuracy(self) -> Dict[str, Any]:
        if self.storage is None:
            return {
                "total": 0,
                "correct": 0,
                "accuracy": 0.0,
                "brier": 0.0,
                "log_loss": 0.0,
                "goal_mae": 0.0,
                "by_tournament": [],
            }
        return self.storage.accuracy()

    def clear_history(self) -> None:
        if self.storage is not None:
            self.storage.clear()
        with self._lock:
            self._analysis_cache.clear()
            self._last_simulations.clear()

    def team_search(self, query: str, limit: int = 12) -> List[Dict[str, Any]]:
        return self.extractor.search(
            query, type_filter="team", sport="football", limit=limit
        )

    def team_matches(self, team_id: int, limit: int = 40) -> List[Dict[str, Any]]:
        from . import upcoming

        prefs = self.preferences_snapshot()
        matches = upcoming.list_team_upcoming(
            self.extractor,
            int(team_id),
            region=prefs.get("region") or "ambas",
            limit=max(1, min(100, int(limit))),
            timezone_name=prefs.get("timezone") or "local",
            include_finished=True,
            include_live=True,
        )
        return [
            self._decorate_match(match, prefs.get("timezone") or "local")
            for match in matches
        ]

    def _export_csv_bytes(self, rows: Any) -> bytes:
        directory = Path(tempfile.mkdtemp(prefix="sofascore-export-"))
        path = directory / "export.csv"
        try:
            export.write_csv(rows, path)
            return path.read_bytes()
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def export_analysis(
        self, match_id: int, window: Any = 10, fmt: str = "json"
    ) -> Tuple[bytes, str, str]:
        analysis = self.analysis_cached(match_id, window)
        if analysis is None:
            analysis = self.analyze(match_id, window)
        match = analysis.get("match") or {}
        home = (match.get("home_team") or {}).get("name") or "local"
        away = (match.get("away_team") or {}).get("name") or "visitante"
        base = re.sub(r"[^a-z0-9]+", "_", f"{home}_{away}".lower()).strip("_")
        fmt = (fmt or "json").lower()
        if fmt == "json":
            text = export.to_json(analysis, pretty=True)
            return (
                text.encode("utf-8"),
                f"analisis_{base}.json",
                "application/json; charset=utf-8",
            )
        summary_csv = self._export_csv_bytes(analysis.get("comparison") or [])
        matches_csv = self._export_csv_bytes(form.match_rows(analysis))
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("analisis_forma.csv", summary_csv)
            archive.writestr("analisis_partidos.csv", matches_csv)
        return (
            buffer.getvalue(),
            f"analisis_{base}.zip",
            "application/zip",
        )

    def export_simulation(
        self,
        match_id: Optional[int] = None,
        fmt: str = "json",
        summary: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bytes, str, str]:
        if summary is None and match_id is not None:
            with self._lock:
                summary = self._last_simulations.get(int(match_id))
        if summary is None:
            raise ValueError(
                "No hay una simulación reciente. Ejecuta la simulación primero."
            )
        home = (summary.get("teams", {}).get("home") or {}).get("name") or "local"
        away = (summary.get("teams", {}).get("away") or {}).get("name") or "visitante"
        base = re.sub(r"[^a-z0-9]+", "_", f"{home}_{away}".lower()).strip("_")
        fmt = (fmt or "json").lower()
        if fmt == "csv":
            rows = simulation.summary_rows(summary)
            return (
                self._export_csv_bytes(rows),
                f"simulacion_{base}.csv",
                "text/csv; charset=utf-8",
            )
        text = export.to_json(summary, pretty=True)
        return (
            text.encode("utf-8"),
            f"simulacion_{base}.json",
            "application/json; charset=utf-8",
        )

    def export_history(
        self, kind: str = "matches", query: str = "", status: str = ""
    ) -> Tuple[bytes, str, str]:
        if kind == "predictions":
            rows = self.history_predictions(limit=5000)
            filename = "predicciones.csv"
        else:
            rows = self.history_matches(query=query, status=status, limit=5000)
            filename = "historial_partidos.csv"
        return (
            self._export_csv_bytes(rows),
            filename,
            "text/csv; charset=utf-8",
        )

    # ------------------------------------------------------------------
    # Imágenes
    # ------------------------------------------------------------------
    def image_bytes(self, kind: str, item_id: int) -> Tuple[Optional[bytes], str]:
        if kind not in ("team", "category"):
            return None, ""
        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            return None, ""
        directory = config_dir() / "images"
        directory.mkdir(parents=True, exist_ok=True)
        legacy = directory / f"{kind}_{item_id}.png"
        cache = directory / f"{kind}_{item_id}.img"
        if legacy.exists():
            try:
                return legacy.read_bytes(), "image/png"
            except OSError:
                pass
        if cache.exists():
            try:
                data = cache.read_bytes()
                return data, self._guess_image_type(data)
            except OSError:
                pass
        lock_key = (kind, item_id)
        with self._lock:
            lock = self._image_locks.setdefault(lock_key, threading.Lock())
        with lock:
            if cache.exists():
                try:
                    data = cache.read_bytes()
                    return data, self._guess_image_type(data)
                except OSError:
                    pass
            try:
                from curl_cffi import requests as curl_requests
            except ImportError:
                return None, ""
            if kind == "team":
                url = f"https://img.sofascore.com/api/v1/team/{item_id}/image"
            else:
                url = f"https://img.sofascore.com/api/v1/category/{item_id}/image"
            for interface in ("0.0.0.0", None):
                kwargs: Dict[str, Any] = {
                    "headers": {
                        "Accept": "image/png,image/*",
                        "Referer": "https://www.sofascore.com/",
                    },
                    "timeout": 18,
                    "impersonate": "chrome",
                }
                if interface is not None:
                    kwargs["interface"] = interface
                try:
                    response = curl_requests.get(url, **kwargs)
                except Exception:
                    continue
                if response.status_code == 200 and response.content:
                    data = response.content
                    try:
                        temporary = cache.with_suffix(".tmp")
                        temporary.write_bytes(data)
                        os.replace(temporary, cache)
                    except OSError:
                        pass
                    return data, self._guess_image_type(data)
        return None, ""

    @staticmethod
    def _guess_image_type(data: bytes) -> str:
        if data.startswith(b"\x89PNG"):
            return "image/png"
        if data.startswith(b"\xff\xd8"):
            return "image/jpeg"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        return "application/octet-stream"


class WebHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: Tuple[str, int], service: WebService):
        self.service = service
        super().__init__(address, WebRequestHandler)


class WebRequestHandler(BaseHTTPRequestHandler):
    server_version = "SofaScoreWeb/1.0"
    protocol_version = "HTTP/1.1"

    @property
    def service(self) -> WebService:
        return self.server.service  # type: ignore[attr-defined]

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    # ------------------------------------------------------------------
    # Utilidades de respuesta
    # ------------------------------------------------------------------
    def _allowed_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        host = self.headers.get("Host") or ""
        return origin.rstrip("/") in (
            f"http://{host}",
            f"https://{host}",
        )

    def _send_json(self, payload: Any, status: int = 200) -> None:
        try:
            body = json.dumps(
                payload, ensure_ascii=False, default=_json_default
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            self._send_json(
                {"error": "serialization_error", "detail": str(exc)}, 500
            )
            return
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_bytes(
        self,
        body: bytes,
        content_type: str,
        status: int = 200,
        filename: Optional[str] = None,
        cache_seconds: int = 0,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if cache_seconds:
            self.send_header(
                "Cache-Control", f"public, max-age={int(cache_seconds)}"
            )
        else:
            self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if filename:
            safe = filename.replace('"', "")
            self.send_header(
                "Content-Disposition", f'attachment; filename="{safe}"'
            )
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _error(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message}, status)

    def _read_json(self) -> Dict[str, Any]:
        length = _safe_int(self.headers.get("Content-Length")) or 0
        if length > 12 * 1024 * 1024:
            raise ValueError("El cuerpo de la petición es demasiado grande.")
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"JSON no válido: {exc}")
        if not isinstance(payload, dict):
            raise ValueError("Se esperaba un objeto JSON.")
        return payload

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        if path.startswith("/api/"):
            self._handle_api_get(path, query)
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        if not self._allowed_origin():
            self._error("Origen no permitido.", 403)
            return
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        try:
            payload = self._read_json()
        except ValueError as exc:
            self._error(str(exc), 400)
            return
        self._handle_api_post(path, query, payload)

    def do_DELETE(self) -> None:  # noqa: N802
        if not self._allowed_origin():
            self._error("Origen no permitido.", 403)
            return
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        self._handle_api_delete(path, query)

    def _serve_static(self, path: str) -> None:
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        candidate = (WEB_DIR / relative).resolve()
        try:
            candidate.relative_to(WEB_DIR.resolve())
        except ValueError:
            self._error("Ruta no válida.", 404)
            return
        if not candidate.exists() or candidate.is_dir():
            candidate = WEB_DIR / "index.html"
        if not candidate.exists():
            self._error("No se encontró la interfaz web.", 500)
            return
        content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        if candidate.suffix == ".js":
            content_type = "text/javascript; charset=utf-8"
        elif candidate.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif candidate.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif candidate.suffix == ".svg":
            content_type = "image/svg+xml"
        try:
            body = candidate.read_bytes()
        except OSError:
            self._error("No se pudo leer la interfaz.", 500)
            return
        self._send_bytes(body, content_type, cache_seconds=0)

    # ------------------------------------------------------------------
    # GET de la API
    # ------------------------------------------------------------------
    def _handle_api_get(self, path: str, query: Dict[str, List[str]]) -> None:
        def q(name: str, default: str = "") -> str:
            return (query.get(name) or [default])[0]

        try:
            if path == "/api/health":
                predictions = 0
                if self.service.storage is not None:
                    try:
                        predictions = self.service.storage.count_predictions()
                    except Exception:
                        predictions = 0
                self._send_json(
                    {
                        "status": "ok",
                        "version": __version__,
                        "predictions": predictions,
                        "model": neural.model_version(),
                    }
                )
                return
            if path == "/api/bootstrap":
                payload = self.service.bootstrap()
                payload["api_url"] = f"http://{self.headers.get('Host')}"
                self._send_json(payload)
                return
            if path == "/api/day":
                payload = self.service.list_day(
                    day=q("date") or None,
                    region=q("region"),
                    competitions=q("competitions"),
                    timezone_name=q("timezone"),
                    stage=q("stage", "all"),
                    refresh=q("refresh") in ("1", "true", "yes"),
                )
                self._send_json(payload)
                return
            if path == "/api/live":
                ids = []
                for part in (q("ids") or "").split(","):
                    value = _safe_int(part)
                    if value is not None:
                        ids.append(value)
                self._send_json(self.service.live_updates(ids))
                return
            if path == "/api/match":
                match_id = _safe_int(q("id"))
                if match_id is None:
                    self._error("Falta el identificador del partido.")
                    return
                self._send_json(self.service.match_detail(match_id))
                return
            if path in ("/api/predictions", "/api/history/predictions"):
                self._send_json(
                    {
                        "predictions": self.service.history_predictions(
                            limit=_safe_int(q("limit")) or 1000
                        )
                    }
                )
                return
            if path in ("/api/matches", "/api/history/matches"):
                self._send_json(
                    {
                        "matches": self.service.history_matches(
                            query=q("query"),
                            status=q("status"),
                            limit=_safe_int(q("limit")) or 500,
                        )
                    }
                )
                return
            if path == "/api/accuracy":
                self._send_json(self.service.accuracy())
                return
            if path == "/api/model":
                self._send_json(self.service.model_info())
                return
            if path == "/api/team/search":
                search_query = q("q").strip()
                if not search_query:
                    self._send_json({"results": []})
                    return
                self._send_json(
                    {
                        "results": self.service.team_search(
                            search_query, limit=_safe_int(q("limit")) or 12
                        )
                    }
                )
                return
            if path == "/api/team/matches":
                team_id = _safe_int(q("id"))
                if team_id is None:
                    self._error("Falta el identificador del equipo.")
                    return
                self._send_json(
                    {
                        "matches": self.service.team_matches(
                            team_id, limit=_safe_int(q("limit")) or 40
                        )
                    }
                )
                return
            if path == "/api/preview":
                match_id = _safe_int(q("id"))
                if match_id is None:
                    self._error("Falta el identificador del partido.")
                    return
                self._send_json(
                    self.service.preview_payload(
                        match_id,
                        window=q("window", "10"),
                        force=q("refresh") in ("1", "true", "yes"),
                    )
                )
                return
            if path == "/api/export/analysis":
                match_id = _safe_int(q("id"))
                if match_id is None:
                    self._error("Falta el identificador del partido.")
                    return
                body, filename, content_type = self.service.export_analysis(
                    match_id, window=q("window", "10"), fmt=q("format", "json")
                )
                self._send_bytes(body, content_type, filename=filename)
                return
            if path == "/api/export/simulation":
                match_id = _safe_int(q("id"))
                if match_id is None:
                    self._error("Falta el identificador del partido.")
                    return
                body, filename, content_type = self.service.export_simulation(
                    match_id, fmt=q("format", "json")
                )
                self._send_bytes(body, content_type, filename=filename)
                return
            if path == "/api/export/history":
                body, filename, content_type = self.service.export_history(
                    kind=q("kind", "matches"),
                    query=q("query"),
                    status=q("status"),
                )
                self._send_bytes(body, content_type, filename=filename)
                return
            if path == "/api/image":
                kind = q("kind")
                item_id = _safe_int(q("id"))
                if item_id is None:
                    self._error("Imagen no válida.", 404)
                    return
                data, content_type = self.service.image_bytes(kind, item_id)
                if data is None:
                    self._error("Imagen no disponible.", 404)
                    return
                self._send_bytes(
                    data, content_type or "image/png", cache_seconds=7 * 86400
                )
                return
            if path.startswith("/api/jobs/"):
                job = self.service.jobs.get(path.rsplit("/", 1)[-1])
                if job is None:
                    self._error("Trabajo no encontrado.", 404)
                    return
                self._send_json(job)
                return
            self._error("Ruta no encontrada.", 404)
        except (ValueError, SofaScoreError) as exc:
            self._error(str(exc), 400 if isinstance(exc, ValueError) else 502)
        except Exception as exc:  # noqa: BLE001 - API local
            self._error(f"Error interno: {exc}", 500)

    # ------------------------------------------------------------------
    # POST / DELETE de la API
    # ------------------------------------------------------------------
    def _handle_api_post(
        self, path: str, query: Dict[str, List[str]], payload: Dict[str, Any]
    ) -> None:
        try:
            if path == "/api/jobs/analysis":
                match_id = _safe_int(payload.get("match_id") or payload.get("id"))
                if match_id is None:
                    self._error("Falta el identificador del partido.")
                    return
                window = payload.get("window", 10)
                force = bool(payload.get("force"))
                job = self.service.jobs.submit(
                    "analysis",
                    lambda progress: self.service.analyze(
                        match_id,
                        window=window,
                        progress=progress,
                        force=force,
                    ),
                )
                self._send_json({"job": job})
                return
            if path == "/api/jobs/simulation":
                match_id = _safe_int(payload.get("match_id") or payload.get("id"))
                if match_id is None:
                    self._error("Falta el identificador del partido.")
                    return
                job = self.service.jobs.submit(
                    "simulation",
                    lambda progress: self.service.simulate(
                        match_id,
                        window=payload.get("window", 10),
                        iterations=_safe_int(payload.get("iterations"))
                        or simulation.DEFAULT_ITERATIONS,
                        seed=payload.get("seed"),
                        use_cache=bool(payload.get("use_cache", True)),
                        progress=progress,
                    ),
                )
                self._send_json({"job": job})
                return
            if path == "/api/preferences":
                self._send_json(
                    {
                        "preferences": self.service.update_preferences(payload),
                    }
                )
                return
            if path == "/api/favorites":
                self._send_json(
                    self.service.toggle_favorite(
                        payload.get("team_id") or payload.get("id"),
                        payload.get("name"),
                        favorite=payload.get("favorite"),
                    )
                )
                return
            if path == "/api/open-folder":
                folder = None
                if self.service.storage is not None:
                    folder = self.service.storage.path.parent
                if folder is None:
                    folder = config_dir()
                folder.mkdir(parents=True, exist_ok=True)
                if os.name == "nt":
                    os.startfile(str(folder))  # type: ignore[attr-defined]
                else:
                    webbrowser.open(folder.as_uri())
                self._send_json({"opened": str(folder)})
                return
            if path == "/api/preview/open":
                match_id = _safe_int(payload.get("match_id") or payload.get("id"))
                if match_id is None:
                    self._error("Falta el identificador del partido.")
                    return
                result = self.service.preview_payload(
                    match_id, window=payload.get("window", 10)
                )
                PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
                filename = f"previa_{match_id}.html"
                path_file = PREVIEW_DIR / filename
                path_file.write_text(result["html"], encoding="utf-8")
                webbrowser.open(path_file.as_uri())
                self._send_json(
                    {"opened": str(path_file), "url": path_file.as_uri()}
                )
                return
            if path == "/api/export/simulation":
                body, filename, content_type = self.service.export_simulation(
                    match_id=_safe_int(payload.get("match_id")),
                    fmt=payload.get("format", "json"),
                    summary=payload.get("summary"),
                )
                self._send_bytes(body, content_type, filename=filename)
                return
            if path == "/api/shutdown":
                self._send_json({"status": "closing"})
                threading.Thread(
                    target=self.server.shutdown, daemon=True
                ).start()
                return
            self._error("Ruta no encontrada.", 404)
        except (ValueError, SofaScoreError) as exc:
            self._error(str(exc), 400 if isinstance(exc, ValueError) else 502)
        except Exception as exc:  # noqa: BLE001 - API local
            self._error(f"Error interno: {exc}", 500)

    def _handle_api_delete(
        self, path: str, query: Dict[str, List[str]]
    ) -> None:
        try:
            if path == "/api/history":
                self.service.clear_history()
                self._send_json({"cleared": True})
                return
            if path == "/api/simulation/cache":
                deleted = simulation_cache.clear_simulation_cache()
                with self.service._lock:
                    self.service._last_simulations.clear()
                self._send_json({"deleted": deleted})
                return
            self._error("Ruta no encontrada.", 404)
        except Exception as exc:  # noqa: BLE001 - API local
            self._error(f"Error interno: {exc}", 500)


# ----------------------------------------------------------------------
# Arranque de la ventana y del servidor
# ----------------------------------------------------------------------
def find_edge() -> Optional[Path]:
    candidates = [
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles(x86)", ""))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Microsoft/Edge/Application/msedge.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _server_health(port: int) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.5) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("status") == "ok"
    except Exception:
        return False


def start_server(
    service: WebService, port: int = 8765
) -> Tuple[WebHTTPServer, str]:
    last_error: Optional[BaseException] = None
    for candidate in range(port, port + 12):
        try:
            server = WebHTTPServer(("127.0.0.1", candidate), service)
        except OSError as exc:
            last_error = exc
            continue
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.25},
            daemon=True,
            name="sofascore-web",
        )
        thread.start()
        bound_port = server.server_address[1]
        return server, f"http://127.0.0.1:{bound_port}"
    raise OSError(
        f"No se pudo abrir el servidor web local: {last_error or 'puerto ocupado'}"
    )


def launch_window(
    url: str,
    position: Optional[str] = None,
    size: str = "1440,920",
    edge: Optional[Path] = None,
) -> Optional[subprocess.Popen]:
    edge = edge or find_edge()
    if edge is None:
        webbrowser.open(url)
        return None
    try:
        port = urlparse(url).port or 8765
    except ValueError:
        port = 8765
    profile_name = "webview" if port == 8765 else f"webview-{port}"
    profile = config_dir() / profile_name
    profile.mkdir(parents=True, exist_ok=True)
    args = [
        str(edge),
        f"--app={url}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-sync",
        "--disable-extensions",
        "--disable-component-extensions-with-background-pages",
        "--disable-features=msEdgeSyncConfirmation,msEdgeFirstRunExperience,msEdgeSidebarV2,msEdgeCollections",
        "--disable-background-networking",
        f"--window-size={size}",
    ]
    if position:
        args.append(f"--window-position={position}")
    debug_port = os.environ.get("SOFASCORE_DEBUG_PORT", "").strip()
    if debug_port:
        args.append(f"--remote-debugging-port={debug_port}")
    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sofascore-gui",
        description="SofaScore · interfaz web local y modo clásico.",
    )
    parser.add_argument(
        "--classic",
        action="store_true",
        help="Abre la interfaz clásica de Tkinter.",
    )
    parser.add_argument(
        "--theme",
        choices=["auto", "claro", "oscuro"],
        default="auto",
        help="Tema inicial del modo clásico.",
    )
    parser.add_argument(
        "--timezone",
        default="local",
        help="Zona horaria inicial del modo clásico.",
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="Puerto local (por defecto 8765)."
    )
    parser.add_argument(
        "--no-window",
        action="store_true",
        help="Solo inicia el servidor; no abre la ventana.",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Abre en el navegador predeterminado en vez de la ventana Edge.",
    )
    parser.add_argument(
        "--position",
        default="",
        help="Posición de la ventana, por ejemplo -1650,-37.",
    )
    parser.add_argument(
        "--size", default="1440,920", help="Tamaño de la ventana, por ejemplo 1380,880."
    )
    parser.add_argument(
        "--workers", type=int, default=6, help="Hilos de consulta a SofaScore."
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.classic:
        from .gui import main as gui_main

        return gui_main(
            workers=max(1, int(args.workers)),
            timezone_name=args.timezone,
            theme=args.theme,
        )

    service = WebService(workers=max(1, int(args.workers)))
    existing = _server_health(args.port)
    if existing:
        url = f"http://127.0.0.1:{args.port}"
        if not args.no_window:
            if args.browser:
                webbrowser.open(url)
            else:
                proc = launch_window(
                    url,
                    position=args.position or None,
                    size=args.size,
                )
                if proc is not None:
                    try:
                        proc.wait()
                    except KeyboardInterrupt:
                        pass
        return 0

    server, url = start_server(service, port=args.port)
    if args.no_window:
        print(url, flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            server.server_close()
        return 0

    if args.browser:
        webbrowser.open(url)
        # Sin ventana propia no hay forma fiable de saber cuándo cerrar.
        print(url, flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            server.server_close()
        return 0

    proc = launch_window(
        url, position=args.position or None, size=args.size
    )
    try:
        if proc is not None:
            proc.wait()
        else:
            print(url, flush=True)
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
