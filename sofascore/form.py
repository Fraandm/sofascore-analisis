"""Análisis de forma reciente de dos equipos antes de un partido.

Obtiene los últimos partidos disputados por cada club en la temporada del
partido seleccionado y calcula medias y totales de las estadísticas clave:

* goles a favor y en contra
* tiros de esquina
* tarjetas (amarillas y rojas)
* remates totales
* remates al arco
* faltas
* paradas del portero

Toda la información procede de la API interna de SofaScore. No se usa
Opta ni otra plataforma porque SofaScore ya publica estas siete métricas
para las competiciones profesionales de Europa y Sudamérica.
"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from . import endpoints, normalize, regions
from .exceptions import NotFoundError, SofaScoreError

ProgressCallback = Callable[[int, int, str], None]

STAT_LABELS: Dict[str, str] = {
    "goals_for": "Goles a favor",
    "goals_against": "Goles en contra",
    "xg_for": "xG a favor",
    "xg_against": "xG en contra",
    "big_chances_for": "Ocasiones claras a favor",
    "big_chances_against": "Ocasiones claras en contra",
    "shots_inside_box": "Remates dentro del área",
    "corners": "Tiros de esquina",
    "cards": "Tarjetas",
    "yellow_cards": "Tarjetas amarillas",
    "red_cards": "Tarjetas rojas",
    "shots": "Remates totales",
    "shots_on_target": "Remates al arco",
    "fouls": "Faltas",
    "saves": "Paradas del portero",
}

STAT_ORDER: List[str] = list(STAT_LABELS)

# Claves que usa SofaScore en cada estadística. Se aceptan varias porque
# el nombre puede cambiar según la competición.
STAT_SOURCE_KEYS: Dict[str, Sequence[str]] = {
    "corners": ("cornerKicks", "corners"),
    "cards": (),
    "yellow_cards": ("yellowCards", "yellowCard"),
    "red_cards": ("redCards", "redCard"),
    "shots": ("totalShotsOnGoal", "totalShots", "shots"),
    "shots_on_target": ("shotsOnGoal", "shotsOnTarget", "onTarget"),
    "fouls": ("fouls",),
    "saves": ("goalkeeperSaves", "saves"),
    "xg_for": ("expectedGoals",),
    "xg_against": ("expectedGoals",),
    "big_chances_for": ("bigChanceCreated",),
    "big_chances_against": ("bigChanceCreated",),
    "shots_inside_box": ("totalShotsInsideBox",),
}

STATS_TTL = 7 * 24 * 3600  # las estadísticas de un partido terminado no cambian
EVENTS_TTL = 600
MAX_ALL_MATCHES = 80


def season_start_year(season: Any) -> Optional[int]:
    """Año de inicio de una temporada.

    SofaScore usa etiquetas como ``26/27``, ``2026`` o ``2025/2026``.
    """
    if not isinstance(season, dict) or not season:
        return None
    for key in ("year", "name"):
        text = season.get(key)
        if not text:
            continue
        text = str(text)
        match = re.search(r"(\d{4})", text)
        if match:
            return int(match.group(1))
        match = re.search(r"(\d{2})\s*/\s*(\d{2})", text)
        if match:
            return 2000 + int(match.group(1))
        match = re.search(r"\b(\d{2})\b", text)
        if match:
            return 2000 + int(match.group(1))
    return None


def parse_window(value: Any) -> Optional[int]:
    """Convierte la ventana pedida en un entero o ``None`` (todos)."""
    if value is None:
        return None
    if isinstance(value, int):
        return None if value <= 0 else value
    text = str(value).strip().casefold()
    if text in ("", "0", "all", "todo", "todos", "toda", "completa", "total"):
        return None
    try:
        number = int(text)
    except ValueError as exc:
        raise SofaScoreError(
            f'Ventana no válida: "{value}". Usa 5, 10, 15 o "all".'
        ) from exc
    return None if number <= 0 else number


LIVE_STATUSES = {"inprogress", "live", "halftime"}


def is_live_status(status: Any) -> bool:
    return str(status or "").casefold() in LIVE_STATUSES


def match_minute(
    match: Dict[str, Any], now: Optional[float] = None
) -> float:
    """Minuto aproximado de un partido en vivo (0 si no ha empezado)."""
    status = match.get("status_type")
    if status == "finished":
        return 90.0
    if status in (None, "notstarted", "delayed"):
        return 0.0
    reference = time.time() if now is None else float(now)
    status_time = match.get("status_time") or {}
    initial = status_time.get("initial")
    timestamp = status_time.get("timestamp")
    if initial is not None and timestamp:
        try:
            elapsed = max(0.0, reference - float(timestamp))
            return round(min(120.0, (float(initial) + elapsed) / 60.0), 1)
        except (TypeError, ValueError):
            pass
    time_info = match.get("time") or {}
    start = time_info.get("current_period_start")
    end = time_info.get("last_period_end")
    if start and end:
        try:
            return round(
                min(90.0, max(0.0, (float(end) - float(start)) / 60.0)), 1
            )
        except (TypeError, ValueError):
            pass
    start_timestamp = match.get("start_timestamp")
    if start_timestamp:
        try:
            return round(
                min(120.0, max(0.0, (reference - float(start_timestamp)) / 60.0)),
                1,
            )
        except (TypeError, ValueError):
            pass
    return 0.0


def _same_season(season: Any, target_year: int) -> bool:
    year = season_start_year(season)
    if year is not None:
        return year == target_year
    return False


def _stat_items(payload: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Índice ``clave -> item`` de las estadísticas del partido completo."""
    items: Dict[str, Dict[str, Any]] = {}
    for block in (payload or {}).get("statistics") or []:
        period = block.get("period")
        if period not in (None, "ALL"):
            continue
        for group in block.get("groups") or []:
            for item in group.get("statisticsItems") or []:
                key = item.get("key")
                if key and key not in items:
                    items[key] = item
    return items


def _item_value(item: Optional[Dict[str, Any]], home: bool) -> Optional[Any]:
    if not item:
        return None
    value = item.get("homeValue" if home else "awayValue")
    if value is None:
        value = item.get("home" if home else "away")
    return normalize.to_number(value)


def _first_value(
    items: Dict[str, Dict[str, Any]], keys: Iterable[str], home: bool
) -> Optional[Any]:
    for key in keys:
        if key in items:
            return _item_value(items[key], home)
    return None


def _cards_value(
    items: Dict[str, Dict[str, Any]], home: bool
) -> Optional[int]:
    """Tarjetas de un lado; 0 si hay estadísticas pero no se muestran."""
    if not items:
        return None
    yellow = _first_value(items, STAT_SOURCE_KEYS["yellow_cards"], home)
    red = _first_value(items, STAT_SOURCE_KEYS["red_cards"], home)
    if yellow is None and red is None:
        return 0
    return int(yellow or 0) + int(red or 0)


def extract_team_match_stats(
    event: Dict[str, Any],
    statistics_payload: Optional[Dict[str, Any]],
    team_id: Optional[int],
    side: Optional[str] = None,
) -> Dict[str, Any]:
    """Fila de estadísticas de un equipo en un partido.

    ``team_id`` identifica al equipo y determina si jugó como local o
    visitante en ese partido concreto. ``side`` solo se usa como respaldo
    cuando el evento no trae los IDs de los equipos.
    """
    home_team = event.get("home_team") or {}
    away_team = event.get("away_team") or {}

    try:
        numeric_id = int(team_id) if team_id is not None else None
    except (TypeError, ValueError):
        numeric_id = None

    if numeric_id is not None and home_team.get("id") == numeric_id:
        is_home = True
    elif numeric_id is not None and away_team.get("id") == numeric_id:
        is_home = False
    else:
        is_home = side == "home"

    items = _stat_items(statistics_payload)
    available = bool(items)

    goals_for = event.get("home_score") if is_home else event.get("away_score")
    goals_against = event.get("away_score") if is_home else event.get("home_score")

    corners = _first_value(items, STAT_SOURCE_KEYS["corners"], is_home)
    shots = _first_value(items, STAT_SOURCE_KEYS["shots"], is_home)
    shots_on_target = _first_value(
        items, STAT_SOURCE_KEYS["shots_on_target"], is_home
    )
    fouls = _first_value(items, STAT_SOURCE_KEYS["fouls"], is_home)
    saves = _first_value(items, STAT_SOURCE_KEYS["saves"], is_home)

    xg_for = _first_value(items, STAT_SOURCE_KEYS["xg_for"], is_home)
    xg_against = _first_value(items, STAT_SOURCE_KEYS["xg_against"], not is_home)
    xg_on_target_for = _first_value(
        items, ("expectedGoalsOnTarget",), is_home
    )
    xg_on_target_against = _first_value(
        items, ("expectedGoalsOnTarget",), not is_home
    )
    big_chances_for = _first_value(
        items, STAT_SOURCE_KEYS["big_chances_for"], is_home
    )
    big_chances_against = _first_value(
        items, STAT_SOURCE_KEYS["big_chances_against"], not is_home
    )
    shots_inside_box = _first_value(
        items, STAT_SOURCE_KEYS["shots_inside_box"], is_home
    )
    shots_inside_box_against = _first_value(
        items, STAT_SOURCE_KEYS["shots_inside_box"], not is_home
    )
    shots_against = _first_value(
        items, STAT_SOURCE_KEYS["shots"], not is_home
    )
    shots_on_target_against = _first_value(
        items, STAT_SOURCE_KEYS["shots_on_target"], not is_home
    )
    corners_against = _first_value(
        items, STAT_SOURCE_KEYS["corners"], not is_home
    )
    fouls_against = _first_value(
        items, STAT_SOURCE_KEYS["fouls"], not is_home
    )
    saves_against = _first_value(
        items, STAT_SOURCE_KEYS["saves"], not is_home
    )
    cards_against = _cards_value(items, not is_home)

    yellow = _first_value(items, STAT_SOURCE_KEYS["yellow_cards"], is_home)
    red = _first_value(items, STAT_SOURCE_KEYS["red_cards"], is_home)

    if available:
        yellow_cards = int(yellow) if yellow is not None else 0
        red_cards = int(red) if red is not None else 0
        cards = yellow_cards + red_cards
    else:
        yellow_cards = None
        red_cards = None
        cards = None

    opponent = away_team if is_home else home_team
    team = home_team if is_home else away_team
    tournament = event.get("tournament") or {}

    outcome = None
    if goals_for is not None and goals_against is not None:
        if goals_for > goals_against:
            outcome = "G"
        elif goals_for < goals_against:
            outcome = "P"
        else:
            outcome = "E"

    timestamp = event.get("start_timestamp")
    try:
        day = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        day = None

    return {
        "team": team.get("name"),
        "event_id": event.get("id"),
        "date": day,
        "start_time": event.get("start_time"),
        "tournament": tournament.get("name"),
        "tournament_id": tournament.get("id"),
        "opponent": opponent.get("name"),
        "venue": "casa" if is_home else "fuera",
        "home": is_home,
        "score": (
            f"{goals_for}-{goals_against}"
            if goals_for is not None and goals_against is not None
            else None
        ),
        "outcome": outcome,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "xg_for": xg_for,
        "xg_against": xg_against,
        "xg_on_target_for": xg_on_target_for,
        "xg_on_target_against": xg_on_target_against,
        "big_chances_for": big_chances_for,
        "big_chances_against": big_chances_against,
        "shots_inside_box": shots_inside_box,
        "shots_inside_box_against": shots_inside_box_against,
        "corners": corners,
        "corners_against": corners_against,
        "cards": cards,
        "cards_against": cards_against,
        "yellow_cards": yellow_cards,
        "red_cards": red_cards,
        "shots": shots,
        "shots_against": shots_against,
        "shots_on_target": shots_on_target,
        "shots_on_target_against": shots_on_target_against,
        "fouls": fouls,
        "fouls_against": fouls_against,
        "saves": saves,
        "saves_against": saves_against,
        "stats_available": available,
    }


def summarize_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Totales y medias de una lista de filas de partido."""
    totals: Dict[str, Optional[float]] = {}
    averages: Dict[str, Optional[float]] = {}
    counts: Dict[str, int] = {}

    for key in STAT_ORDER:
        values = [row.get(key) for row in rows if row.get(key) is not None]
        counts[key] = len(values)
        if values:
            total = sum(values)
            totals[key] = round(total, 2) if isinstance(total, float) else total
            averages[key] = round(total / len(values), 2)
        else:
            totals[key] = None
            averages[key] = None

    return {
        "matches": len(rows),
        "matches_with_stats": sum(1 for row in rows if row.get("stats_available")),
        "totals": totals,
        "averages": averages,
        "counts": counts,
    }


def build_actual_block(
    match: Dict[str, Any],
    statistics_payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Resumen real de un partido finalizado para validar la simulación."""
    home_id = (match.get("home_team") or {}).get("id")
    away_id = (match.get("away_team") or {}).get("id")
    home_row = extract_team_match_stats(
        match, statistics_payload, home_id, side="home"
    )
    away_row = extract_team_match_stats(
        match, statistics_payload, away_id, side="away"
    )

    totals: Dict[str, Optional[float]] = {}
    for key in (
        "goals_for",
        "corners",
        "cards",
        "shots",
        "shots_on_target",
        "fouls",
        "saves",
        "xg_for",
    ):
        values = [home_row.get(key), away_row.get(key)]
        if all(value is not None for value in values):
            totals[key] = round(sum(float(value) for value in values), 2)
        else:
            totals[key] = None

    totals["goals"] = totals.get("goals_for")

    return {
        "status": (
            "finished"
            if match.get("status_type") == "finished"
            else "live"
        ),
        "minute": match_minute(match),
        "score": (
            f"{match.get('home_score')}-{match.get('away_score')}"
            if match.get("home_score") is not None
            and match.get("away_score") is not None
            else None
        ),
        "stats_available": bool(
            home_row.get("stats_available") or away_row.get("stats_available")
        ),
        "home": home_row,
        "away": away_row,
        "totals": totals,
    }


def recent_form(rows: Sequence[Dict[str, Any]], limit: int = 5) -> str:
    """Cadena tipo ``G G E P G`` con los resultados más recientes."""
    outcomes = [row.get("outcome") for row in rows[:limit] if row.get("outcome")]
    return " ".join(outcomes)


def _fetch_season_events(
    extractor: Any,
    team_id: int,
    target_year: int,
    max_pages: int = 6,
    needed: Optional[int] = None,
    before_timestamp: Optional[int] = None,
    national: bool = False,
) -> Dict[int, Dict[str, Any]]:
    """Descarga partidos recientes del equipo hasta salir de la temporada.

    Para selecciones no se limita a una temporada: su calendario mezcla
    eliminatorias, torneos continentales y amistosos de distintos años.
    """
    found: Dict[int, Dict[str, Any]] = {}
    cutoff = datetime(target_year, 1, 1, tzinfo=timezone.utc).timestamp()
    usable = 0

    for page in range(max_pages):
        payload = extractor.client.get_json(
            endpoints.team_events(team_id, "last", page), ttl=EVENTS_TTL
        )
        events = payload.get("events") or []
        if not events:
            break
        batch = normalize.normalize_events(events)
        for match in batch:
            if match.get("id") is not None:
                found[match["id"]] = match
            timestamp = match.get("start_timestamp")
            season_ok = national or _same_season(match.get("season"), target_year)
            region_ok = (
                regions.is_national_match(match)
                if national
                else regions.region_for_match(match) is not None
            )
            if (
                match.get("status_type") == "finished"
                and timestamp is not None
                and (before_timestamp is None or int(timestamp) < int(before_timestamp))
                and season_ok
                and region_ok
            ):
                usable += 1

        if needed is not None and usable >= needed:
            break

        timestamps = [
            match.get("start_timestamp")
            for match in batch
            if match.get("start_timestamp")
        ]
        if not national and timestamps and min(timestamps) < cutoff:
            break
        if not payload.get("hasNextPage"):
            break

    return found


def matches_for_team(
    extractor: Any,
    team_id: int,
    season: Any,
    before_timestamp: Optional[int] = None,
    limit: Optional[int] = 10,
    max_pages: int = 6,
    national: bool = False,
) -> List[Dict[str, Any]]:
    """Partidos terminados del equipo en la temporada y región admitidas.

    Con ``national=True`` se recogen los últimos partidos de la selección sin
    exigir que pertenezcan a la misma temporada. Así el análisis funciona con
    eliminatorias, Nations League, Copa América, Eurocopa o amistosos.
    """
    target_year = season_start_year(season)
    if target_year is None and before_timestamp:
        target_year = datetime.fromtimestamp(
            int(before_timestamp), tz=timezone.utc
        ).year
    if target_year is None:
        target_year = datetime.now(timezone.utc).year

    found = _fetch_season_events(
        extractor,
        team_id,
        target_year,
        max_pages=max_pages,
        needed=limit,
        before_timestamp=before_timestamp,
        national=national,
    )
    matches: List[Dict[str, Any]] = []

    for match in found.values():
        if match.get("status_type") != "finished":
            continue
        timestamp = match.get("start_timestamp")
        if timestamp is None:
            continue
        if before_timestamp and int(timestamp) >= int(before_timestamp):
            continue
        if national:
            if not regions.is_national_match(match):
                continue
        else:
            if not _same_season(match.get("season"), target_year):
                continue
            if regions.region_for_match(match) is None:
                continue
        matches.append(match)

    matches.sort(key=lambda item: item.get("start_timestamp") or 0, reverse=True)
    if limit is not None:
        matches = matches[: max(0, int(limit))]
    return matches


def _fetch_statistics(
    extractor: Any, event_id: int
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        payload = extractor.client.get_json(
            endpoints.event_statistics(event_id), ttl=STATS_TTL
        )
        return payload, None
    except NotFoundError:
        return None, None
    except SofaScoreError as exc:
        return None, str(exc)


def _team_block(
    side: str,
    team: Dict[str, Any],
    rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    summary = summarize_rows(rows)
    split_rows = [row for row in rows if bool(row.get("home")) == (side == "home")]
    split = summarize_rows(split_rows)
    return {
        "side": side,
        "team": team,
        "matches": rows,
        "sample_size": len(rows),
        "stats_sample_size": summary["matches_with_stats"],
        "totals": summary["totals"],
        "averages": summary["averages"],
        "counts": summary["counts"],
        "form": recent_form(rows),
        "split": {
            "label": "en casa" if side == "home" else "fuera",
            "sample_size": split["matches"],
            "stats_sample_size": split["matches_with_stats"],
            "totals": split["totals"],
            "averages": split["averages"],
        },
    }


def _standing_summary(
    rows: Sequence[Dict[str, Any]], team_id: Any
) -> Optional[Dict[str, Any]]:
    for row in rows or []:
        team = row.get("team") or {}
        if team.get("id") != team_id:
            continue
        matches = int(row.get("matches") or 0)
        points = int(row.get("points") or 0)
        goal_difference = row.get("goal_difference")
        if goal_difference is None and row.get("scores_for") is not None:
            goal_difference = int(row.get("scores_for") or 0) - int(
                row.get("scores_against") or 0
            )
        return {
            "position": row.get("position"),
            "matches": matches,
            "wins": row.get("wins"),
            "draws": row.get("draws"),
            "losses": row.get("losses"),
            "points": points,
            "scores_for": row.get("scores_for"),
            "scores_against": row.get("scores_against"),
            "goal_difference": goal_difference,
            "points_per_game": round(points / matches, 2) if matches else None,
            "goal_difference_per_game": (
                round(float(goal_difference) / matches, 2)
                if matches and goal_difference is not None
                else None
            ),
        }
    return None


def _h2h_summary(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    duel = (payload or {}).get("teamDuel") or {}
    home_wins = int(duel.get("homeWins") or 0)
    away_wins = int(duel.get("awayWins") or 0)
    draws = int(duel.get("draws") or 0)
    matches = home_wins + away_wins + draws
    if matches <= 0:
        return None
    return {
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "matches": matches,
    }


def analyze_match(
    extractor: Any,
    match: Any,
    window: Any = 10,
    progress: Optional[ProgressCallback] = None,
    max_workers: int = 6,
    max_all_matches: int = MAX_ALL_MATCHES,
    include_lineups: bool = False,
    include_referee: bool = False,
    include_context: bool = False,
    referee_matches: int = 6,
) -> Dict[str, Any]:
    """Analiza la forma de ambos equipos antes de ``match``.

    ``match`` puede ser un partido normalizado o un ID de evento.
    ``window`` puede ser 5, 10, 15, ``None`` o ``"all"``.

    Si ``include_lineups`` o ``include_referee`` son verdaderos se consulta
    el detalle del partido objetivo para añadir alineaciones y árbitro.
    ``include_context`` añade clasificación y H2H para los partidos que aún
    no han terminado.
    """
    warnings: List[str] = []
    lineups: Optional[Dict[str, Any]] = None
    referee_profile: Optional[Dict[str, Any]] = None

    if isinstance(match, int):
        event_id = int(match)
        if include_lineups:
            detail = extractor.get_match(event_id, sections=["lineups"])
        else:
            detail = extractor.get_match(event_id)
        match = detail.get("match")
        lineups = detail.get("lineups") if include_lineups else None
    elif isinstance(match, dict):
        event_id = match.get("id")
        if event_id is not None and (include_lineups or include_referee):
            try:
                if include_lineups:
                    detail = extractor.get_match(
                        event_id, sections=["lineups"]
                    )
                else:
                    detail = extractor.get_match(event_id)
            except SofaScoreError as exc:
                warnings.append(
                    f"No se pudo consultar el contexto del partido: {exc}"
                )
            else:
                if detail.get("match"):
                    match = {**match, **detail["match"]}
                lineups = detail.get("lineups") if include_lineups else None
    else:
        event_id = None

    if not isinstance(match, dict) or not match:
        raise SofaScoreError("No se pudo cargar el partido indicado.")

    if include_lineups and lineups is None:
        warnings.append(
            "El partido no tiene alineaciones disponibles todavía."
        )

    if include_referee:
        referee = match.get("referee") or {}
        if referee.get("id") is not None:
            try:
                referee_profile = extractor.get_referee_profile(
                    int(referee["id"]),
                    tournament_id=(match.get("tournament") or {}).get("id"),
                    season_id=(match.get("season") or {}).get("id"),
                    before_timestamp=match.get("start_timestamp"),
                    max_matches=referee_matches,
                )
            except SofaScoreError as exc:
                warnings.append(f"No se pudo consultar al árbitro: {exc}")
                referee_profile = dict(referee)
        else:
            warnings.append("El partido todavía no tiene árbitro designado.")
    else:
        referee_profile = dict(match.get("referee") or {}) or None

    actual = None
    actual_client = getattr(extractor, "client", None)
    if (
        is_live_status(match.get("status_type"))
        and event_id is not None
        and actual_client is not None
    ):
        try:
            live_payload = actual_client.get_json(
                endpoints.event(event_id), ttl=0
            )
            live_match = normalize.normalize_event(
                live_payload.get("event") or {}
            )
            if live_match:
                match = {**match, **live_match}
        except SofaScoreError:
            pass

    should_fetch_actual = (
        match.get("status_type") == "finished"
        or is_live_status(match.get("status_type"))
    )
    if should_fetch_actual and event_id is not None and actual_client is not None:
        try:
            payload = actual_client.get_json(
                endpoints.event_statistics(event_id),
                ttl=STATS_TTL
                if match.get("status_type") == "finished"
                else 0,
            )
        except SofaScoreError as exc:
            warnings.append(
                f"No se pudieron cargar las estadísticas reales del partido: {exc}"
            )
            payload = None
        actual = build_actual_block(match, payload)

    standings: Dict[str, Any] = {}
    h2h: Optional[Dict[str, Any]] = None
    if include_context:
        if match.get("status_type") == "finished":
            warnings.append(
                "Clasificación y H2H omitidos en un partido finalizado para "
                "evitar fuga de información; se usa la calidad de la "
                "alineación y la forma previa."
            )
        else:
            tournament_id = (match.get("tournament") or {}).get("id")
            season_id = (match.get("season") or {}).get("id")
            if tournament_id is not None and season_id is not None:
                try:
                    standing_rows = extractor.get_standings(
                        int(tournament_id), int(season_id)
                    )
                except SofaScoreError as exc:
                    warnings.append(
                        f"No se pudo consultar la clasificación: {exc}"
                    )
                    standing_rows = []
                home_standing = _standing_summary(
                    standing_rows, (match.get("home_team") or {}).get("id")
                )
                away_standing = _standing_summary(
                    standing_rows, (match.get("away_team") or {}).get("id")
                )
                if home_standing or away_standing:
                    standings = {
                        "home": home_standing,
                        "away": away_standing,
                    }
            if event_id is not None and actual_client is not None:
                try:
                    h2h_payload = actual_client.get_json(
                        endpoints.event_h2h(event_id), ttl=3600
                    )
                except SofaScoreError:
                    h2h_payload = None
                h2h = _h2h_summary(h2h_payload)

    window_value = parse_window(window)
    before_timestamp = match.get("start_timestamp")
    season = match.get("season") or {}

    teams = {
        "home": match.get("home_team") or {},
        "away": match.get("away_team") or {},
    }
    national_match = regions.is_national_match(match)
    scope = "partidos recientes" if national_match else "partidos de la temporada"

    selected: Dict[str, List[Dict[str, Any]]] = {}
    for side in ("home", "away"):
        team = teams[side]
        team_name = team.get("name") or side
        if team.get("id") is None:
            raise SofaScoreError(
                f"No se pudo identificar al equipo {team_name} del partido."
            )
        if progress:
            progress(0, 1, f"Buscando partidos de {team_name}…")
        limit = window_value
        if window_value is None:
            limit = max_all_matches + 1
        rows = matches_for_team(
            extractor,
            int(team["id"]) if team.get("id") is not None else 0,
            season,
            before_timestamp=before_timestamp,
            limit=limit,
            national=national_match,
        )
        target_id = match.get("id")
        if target_id is not None:
            rows = [row for row in rows if row.get("id") != target_id]
        if window_value is None and len(rows) > max_all_matches:
            rows = rows[:max_all_matches]
            warnings.append(
                f"{team_name}: se analizan como máximo {max_all_matches} "
                f"{scope}."
            )
        elif window_value and len(rows) < window_value:
            warnings.append(
                f"{team_name}: solo hay {len(rows)} partido(s) terminado(s) "
                f"en los {scope} (se pidieron {window_value})."
            )
        selected[side] = rows

    event_ids: List[int] = []
    for rows in selected.values():
        for row in rows:
            event_id = row.get("id")
            if event_id is not None and event_id not in event_ids:
                event_ids.append(event_id)

    payloads: Dict[int, Optional[Dict[str, Any]]] = {}
    total = len(event_ids)
    if progress:
        progress(0, max(1, total), "Descargando estadísticas de los partidos…")

    if event_ids:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(event_ids))) as pool:
            futures = {
                pool.submit(_fetch_statistics, extractor, event_id): event_id
                for event_id in event_ids
            }
            done = 0
            for future in as_completed(futures):
                event_id = futures[future]
                try:
                    payload, error = future.result()
                except Exception as exc:  # noqa: BLE001 - se informa y se continúa
                    payload, error = None, str(exc)
                payloads[event_id] = payload
                if error:
                    warnings.append(f"Partido {event_id}: {error}")
                done += 1
                if progress:
                    progress(done, total, f"Estadísticas: {done}/{total}")

    blocks: Dict[str, Dict[str, Any]] = {}
    for side in ("home", "away"):
        team_id = teams[side].get("id")
        rows = [
            extract_team_match_stats(
                row, payloads.get(row.get("id")), team_id, side=side
            )
            for row in selected[side]
        ]
        blocks[side] = _team_block(side, teams[side], rows)

    comparison: List[Dict[str, Any]] = []
    for key in STAT_ORDER:
        home_value = blocks["home"]["averages"].get(key)
        away_value = blocks["away"]["averages"].get(key)
        difference = None
        if home_value is not None and away_value is not None:
            difference = round(home_value - away_value, 2)
        comparison.append(
            {
                "stat": key,
                "label": STAT_LABELS[key],
                "home": home_value,
                "away": away_value,
                "difference": difference,
                "home_total": blocks["home"]["totals"].get(key),
                "away_total": blocks["away"]["totals"].get(key),
                "home_split": blocks["home"]["split"]["averages"].get(key),
                "away_split": blocks["away"]["split"]["averages"].get(key),
            }
        )

    result = {
        "match": match,
        "window": window_value if window_value is not None else "all",
        "season": season,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "SofaScore (API interna)",
        "teams": blocks,
        "comparison": comparison,
        "warnings": warnings,
    }
    if include_lineups:
        result["lineups"] = lineups
    if include_referee or match.get("referee"):
        result["referee"] = referee_profile
    if actual is not None:
        result["actual"] = actual
    if standings:
        result["standings"] = standings
    if h2h:
        result["h2h"] = h2h
    return result


def match_rows(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filas de partido de ambos equipos, útiles para CSV."""
    rows: List[Dict[str, Any]] = []
    for side in ("home", "away"):
        block = (analysis.get("teams") or {}).get(side) or {}
        for row in block.get("matches") or []:
            rows.append({"side": side, **row})
    return rows
