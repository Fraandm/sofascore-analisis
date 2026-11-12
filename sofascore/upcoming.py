"""Selección de próximos partidos de Europa y Sudamérica.

La API no ofrece un listado global de partidos por fecha, así que se
consulta la lista de torneos del día y después los partidos de cada
torneo relevante. Para que la interfaz responda rápido se limita a las
competiciones con mayor prioridad y se consultan en paralelo.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional

from . import endpoints, normalize, regions
from .exceptions import NotFoundError, SofaScoreError
from .extractor import parse_day, resolve_timezone

ProgressCallback = Callable[[int, int, str], None]

COMPETITION_CHOICES = ("principales", "todas")
COMPETITION_LABELS = {
    "principales": "Principales",
    "todas": "Todas",
}
LIVE_STATUSES = {"inprogress", "live", "halftime"}


def _scheduled_entries(
    extractor: Any, day: str, pages: int = 1
) -> List[Dict[str, Any]]:
    """Torneos con partidos ese día, deduplicados."""
    seen = set()
    result: List[Dict[str, Any]] = []

    for page in range(1, max(1, pages) + 1):
        payload = extractor.client.get_json(
            endpoints.scheduled_tournaments(day, page), ttl=180
        )
        scheduled = payload.get("scheduled") or []
        for entry in scheduled:
            tournament = entry.get("tournament") or {}
            unique = tournament.get("uniqueTournament") or {}
            unique_id = unique.get("id")
            if not unique_id or unique_id in seen:
                continue
            category = tournament.get("category") or unique.get("category") or {}
            seen.add(unique_id)
            result.append(
                {
                    "unique_tournament_id": unique_id,
                    "name": unique.get("name") or tournament.get("name"),
                    "slug": unique.get("slug") or tournament.get("slug"),
                    "category_id": category.get("id"),
                    "country": (category.get("country") or {}).get("name")
                    or category.get("name"),
                    "region": regions.region_for_tournament(
                        unique_id, category.get("id")
                    ),
                    "priority": tournament.get("priority") or 0,
                }
            )
        if not payload.get("hasNextPage"):
            break

    return result


def _fetch_tournament_events(
    extractor: Any, unique_tournament_id: int, day: str
) -> List[Dict[str, Any]]:
    payload = extractor.client.get_json(
        endpoints.tournament_scheduled_events(unique_tournament_id, day),
        ttl=180,
    )
    return payload.get("events") or []


def is_upcoming(match: Dict[str, Any], now: Optional[float] = None) -> bool:
    """¿Es un partido que todavía no ha empezado?"""
    status = match.get("status_type")
    if status not in (None, "notstarted", "delayed"):
        return False
    timestamp = match.get("start_timestamp")
    if timestamp is None:
        return False
    reference = time.time() if now is None else now
    return int(timestamp) >= int(reference) - 300


def is_live(match: Dict[str, Any]) -> bool:
    """¿El partido está en juego?"""
    return match.get("status_type") in LIVE_STATUSES


def include_match(
    match: Dict[str, Any],
    include_finished: bool = False,
    include_live: bool = True,
    now: Optional[float] = None,
) -> bool:
    """Partido válido para el listado: próximo, en vivo o finalizado."""
    status = match.get("status_type")
    if status == "finished":
        return bool(include_finished)
    if status in LIVE_STATUSES:
        return bool(include_live)
    return is_upcoming(match, now=now)


def _add_local_time(match: Dict[str, Any], tz) -> None:
    timestamp = match.get("start_timestamp")
    if timestamp is None or tz is None:
        return
    try:
        match["start_time_local"] = datetime.fromtimestamp(
            int(timestamp), tz=tz
        ).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        pass


def list_upcoming(
    extractor: Any,
    day: Optional[str] = None,
    region: str = "ambas",
    competitions: str = "principales",
    limit: int = 120,
    timezone_name: str = "local",
    progress: Optional[ProgressCallback] = None,
    include_finished: bool = False,
    include_live: bool = True,
    tournament_filter: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> List[Dict[str, Any]]:
    """Partidos de un día en Europa, Sudamérica y selecciones.

    ``region``: ``ambas``, ``europa``, ``sudamerica`` o ``selecciones``.
    ``competitions``: ``principales`` (prioridad alta) o ``todas``.
    ``include_finished``: añade partidos terminados con su marcador final.
    ``include_live``: añade partidos en vivo con su marcador y minuto.
    ``tournament_filter``: permite cargar solo un subconjunto de torneos
    (por ejemplo, primero las cinco grandes y Sudamérica).
    """
    day = parse_day(day)
    region = regions.normalize_region(region)
    competitions = (
        competitions if competitions in COMPETITION_CHOICES else "principales"
    )
    tz = resolve_timezone(timezone_name)

    if progress:
        progress(0, 1, f"Buscando torneos del {day}…")

    pages = 1 if competitions == "principales" else 3
    entries = _scheduled_entries(extractor, day, pages=pages)

    candidates = [
        entry
        for entry in entries
        if entry.get("region") is not None
        and (
            region == "ambas"
            or regions.normalize_region(entry.get("region")) == region
        )
    ]
    if competitions == "principales":
        strong = [
            entry for entry in candidates if (entry.get("priority") or 0) >= 50
        ]
        if len(strong) >= 10:
            candidates = strong
        else:
            candidates = [
                entry for entry in candidates if (entry.get("priority") or 0) > 0
            ]
        max_tournaments = 45
    else:
        max_tournaments = 100

    if tournament_filter is not None:
        candidates = [entry for entry in candidates if tournament_filter(entry)]

    candidates.sort(
        key=lambda entry: (
            -(entry.get("priority") or 0),
            entry.get("name") or "",
        )
    )
    candidates = candidates[:max_tournaments]

    if not candidates:
        if progress:
            progress(1, 1, "No se encontraron competiciones para ese día.")
        return []

    if progress:
        progress(0, len(candidates), f"Consultando {len(candidates)} competición(es)…")

    events: List[Dict[str, Any]] = []
    done = 0
    workers = max(1, int(getattr(extractor, "workers", 4)))
    with ThreadPoolExecutor(max_workers=min(workers, len(candidates))) as pool:
        futures = {
            pool.submit(
                _fetch_tournament_events,
                extractor,
                int(entry["unique_tournament_id"]),
                day,
            ): entry
            for entry in candidates
        }
        for future in as_completed(futures):
            entry = futures[future]
            done += 1
            try:
                events.extend(future.result())
            except NotFoundError:
                pass
            except SofaScoreError as exc:
                extractor._warn(f'{entry.get("name")}: {exc}')
            if progress:
                progress(
                    done,
                    len(candidates),
                    f"Competiciones: {done}/{len(candidates)}",
                )

    matches = normalize.normalize_events(events)
    if tz is not None:
        matches = extractor._filter_by_local_date(matches, day, tz)

    seen = set()
    result: List[Dict[str, Any]] = []
    for match in matches:
        match_id = match.get("id")
        if match_id in seen:
            continue
        seen.add(match_id)
        if not regions.match_in_region(match, region):
            continue
        if not include_match(
            match,
            include_finished=include_finished,
            include_live=include_live,
        ):
            continue
        match["region"] = regions.region_for_match(match)
        _add_local_time(match, tz)
        result.append(match)

    def priority(item: Dict[str, Any]) -> int:
        if is_live(item):
            return 0
        if item.get("status_type") == "finished":
            return 2
        return 1

    result.sort(
        key=lambda item: (
            priority(item),
            item.get("start_timestamp") or 0,
            item.get("id") or 0,
        )
    )
    return result[: max(0, int(limit))]


def list_team_upcoming(
    extractor: Any,
    team_id: int,
    region: str = "ambas",
    limit: int = 20,
    days: int = 120,
    timezone_name: str = "local",
    include_finished: bool = False,
    include_live: bool = True,
) -> List[Dict[str, Any]]:
    """Partidos de un equipo en Europa/Sudamérica o de una selección.

    Incluye próximos partidos, partidos en vivo y, con ``include_finished``,
    también los últimos resultados. Para selecciones se aceptan amistosos y
    competiciones nacionales, aunque los amistosos no se usan para entrenar.
    """
    region = regions.normalize_region(region)
    tz = resolve_timezone(timezone_name)
    now = time.time()
    horizon = now + max(1, int(days)) * 86400

    # Se piden más partidos de los necesarios porque algunos pueden ser
    # amistosos o de competiciones fuera de las regiones admitidas.
    candidates = list(
        extractor.get_team_matches(team_id, "next", max(30, limit * 3))
    )
    if include_finished or include_live:
        candidates += list(
            extractor.get_team_matches(team_id, "last", max(10, limit))
        )

    result: List[Dict[str, Any]] = []
    seen: set = set()
    for match in candidates:
        match_id = match.get("id")
        if match_id is not None and match_id in seen:
            continue
        timestamp = match.get("start_timestamp")
        if timestamp is None:
            continue
        status = match.get("status_type")
        if status == "finished":
            if not include_finished:
                continue
        elif status in LIVE_STATUSES:
            if not include_live:
                continue
        else:
            if not include_match(match, include_finished=False, now=now):
                continue
            if not (now - 300 <= int(timestamp) <= horizon):
                continue
        if not regions.match_in_region(match, region):
            continue
        match["region"] = regions.region_for_match(match)
        _add_local_time(match, tz)
        if match_id is not None:
            seen.add(match_id)
        result.append(match)

    def priority(item: Dict[str, Any]) -> int:
        if is_live(item):
            return 0
        if item.get("status_type") == "finished":
            return 2
        return 1

    result.sort(
        key=lambda item: (
            priority(item),
            item.get("start_timestamp") or 0,
            item.get("id") or 0,
        )
    )
    return result[: max(0, int(limit))]
