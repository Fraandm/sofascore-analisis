"""Constructores de rutas de la API interna de SofaScore.

La API no está documentada oficialmente y puede cambiar sin aviso.
Rutas verificadas en noviembre de 2026.
"""

from __future__ import annotations

from typing import Dict, Optional
from urllib.parse import quote


def search(query: str) -> str:
    return f"/search/all?q={quote(query)}"


def scheduled_tournaments(day: str, page: int = 1) -> str:
    return f"/sport/football/scheduled-tournaments/{day}/page/{page}"


def category_scheduled_events(category_id: int, day: str) -> str:
    return f"/category/{category_id}/scheduled-events/{day}"


def tournament_scheduled_events(unique_tournament_id: int, day: str) -> str:
    return f"/unique-tournament/{unique_tournament_id}/scheduled-events/{day}"


def live_events() -> str:
    return "/sport/football/events/live"


def all_categories() -> str:
    return "/sport/football/categories/all"


def event(event_id: int) -> str:
    return f"/event/{event_id}"


def event_statistics(event_id: int) -> str:
    return f"/event/{event_id}/statistics"


def event_lineups(event_id: int) -> str:
    return f"/event/{event_id}/lineups"


def event_incidents(event_id: int) -> str:
    return f"/event/{event_id}/incidents"


def event_h2h(event_id: int) -> str:
    return f"/event/{event_id}/h2h"


def event_graph(event_id: int) -> str:
    return f"/event/{event_id}/graph"


def event_best_players(event_id: int) -> str:
    return f"/event/{event_id}/best-players/summary"


def referee(referee_id: int) -> str:
    return f"/referee/{referee_id}"


def referee_statistics(referee_id: int) -> str:
    return f"/referee/{referee_id}/statistics"


def referee_events(referee_id: int, page: int = 0) -> str:
    return f"/referee/{referee_id}/events/last/{page}"


def team(team_id: int) -> str:
    return f"/team/{team_id}"


def team_events(team_id: int, direction: str, page: int = 0) -> str:
    return f"/team/{team_id}/events/{direction}/{page}"


def tournament_seasons(unique_tournament_id: int) -> str:
    return f"/unique-tournament/{unique_tournament_id}/seasons"


def tournament_season_events(
    unique_tournament_id: int,
    season_id: int,
    direction: str,
    page: int = 0,
) -> str:
    return (
        f"/unique-tournament/{unique_tournament_id}/season/{season_id}"
        f"/events/{direction}/{page}"
    )


def tournament_season_round(
    unique_tournament_id: int,
    season_id: int,
    round_number: int,
) -> str:
    return (
        f"/unique-tournament/{unique_tournament_id}/season/{season_id}"
        f"/events/round/{round_number}"
    )


def tournament_standings(unique_tournament_id: int, season_id: int) -> str:
    return f"/unique-tournament/{unique_tournament_id}/season/{season_id}/standings/total"


def player(player_id: int) -> str:
    return f"/player/{player_id}"


def with_params(path: str, params: Optional[Dict[str, object]] = None) -> str:
    """Utilidad para depuración: añade parámetros a una ruta."""
    if not params:
        return path
    from urllib.parse import urlencode

    return f"{path}?{urlencode(params)}"
