"""Normalización de las respuestas crudas de SofaScore.

La API devuelve objetos muy grandes y con nombres inconsistentes. Estas
funciones producen diccionarios estables, en snake_case y fáciles de
exportar a JSON o CSV.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

def normalize_text(value: Any) -> str:
    """Minúsculas, sin acentos ni signos, para comparar nombres."""
    if value is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value))
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", plain.casefold()).strip()


def to_number(value: Any) -> Any:
    """Convierte '13', '45%', '1,5' en números cuando es posible."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip().replace("%", "").replace(",", ".")
        if not text:
            return None
        try:
            number = float(text)
            return int(number) if number.is_integer() else number
        except ValueError:
            return None
    return None


def score_value(value: Any) -> Optional[int]:
    """SofaScore puede devolver el marcador como int o como dict."""
    if isinstance(value, dict):
        for key in ("current", "display", "period1", "normaltime"):
            if key in value:
                number = to_number(value.get(key))
                if number is not None:
                    return int(number)
        return None
    number = to_number(value)
    return int(number) if number is not None else None


def iso_utc(timestamp: Any) -> Optional[str]:
    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def normalize_country(country: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(country, dict) or not country.get("name"):
        return None
    return {
        "name": country.get("name"),
        "alpha2": country.get("alpha2"),
        "alpha3": country.get("alpha3"),
        "slug": country.get("slug"),
    }


def normalize_category(category: Any) -> Dict[str, Any]:
    if not isinstance(category, dict):
        return {}
    sport = category.get("sport") or {}
    return {
        "id": category.get("id"),
        "name": category.get("name"),
        "slug": category.get("slug"),
        "alpha2": category.get("alpha2"),
        "flag": category.get("flag"),
        "priority": category.get("priority"),
        "sport": sport.get("slug"),
    }


def normalize_team(team: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(team, dict) or not team:
        return None
    return {
        "id": team.get("id"),
        "name": team.get("name"),
        "short_name": team.get("shortName"),
        "code": team.get("nameCode"),
        "slug": team.get("slug"),
        "country": (team.get("country") or {}).get("name"),
        "national": team.get("national"),
    }


def normalize_tournament(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tournament = event.get("tournament") or {}
    unique = tournament.get("uniqueTournament") or {}
    category = tournament.get("category") or unique.get("category") or {}
    country = category.get("country") or {}

    if not tournament and not unique:
        return None

    return {
        "id": unique.get("id") or tournament.get("id"),
        "edition_id": tournament.get("id"),
        "name": unique.get("name") or tournament.get("name"),
        "slug": unique.get("slug") or tournament.get("slug"),
        "category": category.get("name"),
        "category_id": category.get("id"),
        "country": country.get("name") or category.get("name"),
        "priority": tournament.get("priority"),
        "is_group": tournament.get("isGroup"),
    }


def normalize_season(season: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(season, dict) or not season:
        return None
    return {
        "id": season.get("id"),
        "name": season.get("name"),
        "year": season.get("year"),
    }


def normalize_venue(venue: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(venue, dict) or not venue:
        return None
    city = venue.get("city") or {}
    country = venue.get("country") or city.get("country") or {}
    stadium = venue.get("stadium") or {}
    name = venue.get("name") or stadium.get("name")
    if not name and not city:
        return None
    return {
        "name": name,
        "city": city.get("name"),
        "country": country.get("name"),
        "capacity": venue.get("capacity") or stadium.get("capacity"),
    }


def normalize_referee(referee: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(referee, dict) or not referee:
        return None
    return {
        "id": referee.get("id"),
        "name": referee.get("name"),
        "country": (referee.get("country") or {}).get("name"),
    }


def normalize_event(event: Any) -> Optional[Dict[str, Any]]:
    """Resumen estable de un partido."""
    if not isinstance(event, dict) or not event:
        return None

    status = event.get("status") or {}
    home_score = score_value(event.get("homeScore"))
    away_score = score_value(event.get("awayScore"))
    winner_code = event.get("winnerCode")

    winner = None
    if winner_code == 1:
        winner = "home"
    elif winner_code == 2:
        winner = "away"
    elif winner_code == 3:
        winner = "draw"
    elif (
        status.get("type") == "finished"
        and home_score is not None
        and away_score is not None
    ):
        if home_score > away_score:
            winner = "home"
        elif away_score > home_score:
            winner = "away"
        else:
            winner = "draw"

    round_info = event.get("roundInfo") or {}
    status_time = event.get("statusTime") or {}
    time_info = event.get("time") or {}

    return {
        "id": event.get("id"),
        "slug": event.get("slug"),
        "custom_id": event.get("customId"),
        "start_timestamp": event.get("startTimestamp"),
        "start_time": iso_utc(event.get("startTimestamp")),
        "status": status.get("description"),
        "status_type": status.get("type"),
        "status_code": status.get("code"),
        "status_time": (
            {
                "initial": status_time.get("initial"),
                "max": status_time.get("max"),
                "timestamp": status_time.get("timestamp"),
                "extra": status_time.get("extra"),
            }
            if status_time
            else None
        ),
        "time": (
            {
                "current_period_start": time_info.get("currentPeriodStartTimestamp"),
                "last_period_end": time_info.get("lastPeriodEndTimestamp"),
                "period_length": time_info.get("periodLength"),
                "initial": time_info.get("initial"),
                "max": time_info.get("max"),
                "extra": time_info.get("extra"),
            }
            if time_info
            else None
        ),
        "tournament": normalize_tournament(event),
        "season": normalize_season(event.get("season")),
        "round": round_info.get("round"),
        "home_team": normalize_team(event.get("homeTeam")),
        "away_team": normalize_team(event.get("awayTeam")),
        "home_score": home_score,
        "away_score": away_score,
        "winner": winner,
        "venue": normalize_venue(event.get("venue")),
        "referee": normalize_referee(event.get("referee")),
        "has_xg": event.get("hasXg"),
        "has_player_statistics": event.get("hasEventPlayerStatistics"),
        "has_heatmap": event.get("hasEventPlayerHeatMap"),
    }


def normalize_events(events: Iterable[Any]) -> List[Dict[str, Any]]:
    result = []
    for event in events or []:
        normalized = normalize_event(event)
        if normalized:
            result.append(normalized)
    return result


def _search_sport(entity: Dict[str, Any]) -> Optional[str]:
    sport = entity.get("sport") or {}
    if not sport:
        category = entity.get("category") or {}
        sport = category.get("sport") or {}
    if not sport:
        unique = entity.get("uniqueTournament") or {}
        category = unique.get("category") or {}
        sport = category.get("sport") or {}
    if not sport:
        tournament = entity.get("tournament") or {}
        category = tournament.get("category") or {}
        sport = category.get("sport") or {}
        if not sport:
            unique = tournament.get("uniqueTournament") or {}
            category = unique.get("category") or {}
            sport = category.get("sport") or {}
    if not sport:
        team = entity.get("team") or {}
        sport = team.get("sport") or {}
    return sport.get("slug")


def _search_country(entity: Dict[str, Any]) -> Optional[str]:
    country = entity.get("country") or {}
    if country.get("name"):
        return country.get("name")
    category = entity.get("category") or {}
    if (category.get("country") or {}).get("name"):
        return category["country"]["name"]
    if category.get("name"):
        return category.get("name")
    unique = entity.get("uniqueTournament") or {}
    category = unique.get("category") or {}
    return category.get("name")


def _type_matches(entity_type: str, wanted: str) -> bool:
    wanted_norm = normalize_text(wanted or "all")
    type_norm = normalize_text(entity_type)

    if wanted_norm in ("", "all", "todo", "todos", "cualquiera"):
        return True
    if wanted_norm in (
        "tournament",
        "tournaments",
        "torneo",
        "torneos",
        "competicion",
        "competiciones",
    ):
        return type_norm in ("tournament", "uniquetournament", "uniquestage")
    if wanted_norm in ("event", "events", "match", "matches", "partido", "partidos"):
        return type_norm in ("event", "match")
    if wanted_norm in ("team", "teams", "equipo", "equipos"):
        return type_norm == "team"
    if wanted_norm in ("player", "players", "jugador", "jugadores"):
        return type_norm == "player"
    if wanted_norm in ("manager", "managers", "entrenador", "entrenadores"):
        return type_norm == "manager"
    if wanted_norm in ("category", "categories", "categoria", "categorias"):
        return type_norm == "category"
    return type_norm == wanted_norm


def normalize_search_results(
    payload: Dict[str, Any],
    type_filter: str = "all",
    sport: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Convierte el buscador global en una lista plana de entidades."""
    rows: List[Dict[str, Any]] = []
    sport_norm = normalize_text(sport) if sport else None
    if sport_norm in ("all", "todo", "todos", "cualquiera"):
        sport_norm = None
    elif sport_norm in ("futbol", "football", "soccer"):
        sport_norm = "football"

    for result in (payload or {}).get("results", []) or []:
        entity_type = result.get("type") or ""
        if not _type_matches(entity_type, type_filter):
            continue

        entity = result.get("entity") or {}
        entity_sport = _search_sport(entity)
        if sport_norm and normalize_text(entity_sport) != sport_norm:
            continue

        row: Dict[str, Any] = {
            "type": entity_type,
            "id": entity.get("id"),
            "name": entity.get("name"),
            "slug": entity.get("slug"),
            "sport": entity_sport,
            "country": _search_country(entity),
        }

        team = entity.get("team") or {}
        if isinstance(team, dict) and team.get("name"):
            row["team"] = team.get("name")
            row["team_id"] = team.get("id")

        if entity.get("position") is not None:
            row["position"] = entity.get("position")
        if entity.get("jerseyNumber") is not None:
            row["jersey_number"] = entity.get("jerseyNumber")
        if entity.get("userCount") is not None:
            row["followers"] = entity.get("userCount")

        if entity_type == "event" or (
            entity.get("homeTeam") and entity.get("awayTeam")
        ):
            row["event"] = normalize_event(entity)

        if entity_type in ("uniqueTournament", "tournament"):
            category = entity.get("category") or {}
            unique = entity.get("uniqueTournament") or {}
            row["category"] = category.get("name")
            row["category_id"] = category.get("id")
            row["unique_tournament_id"] = (
                entity.get("id") if entity_type == "uniqueTournament" else unique.get("id")
            )

        rows.append(row)
        if limit is not None and len(rows) >= limit:
            break

    return rows


def normalize_statistics(
    payload: Optional[Dict[str, Any]],
    period: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Aplana las estadísticas a filas: periodo, grupo, nombre, local, visitante."""
    if not payload:
        return []

    rows: List[Dict[str, Any]] = []
    wanted = normalize_text(period) if period else None

    for period_block in payload.get("statistics", []) or []:
        period_name = period_block.get("period") or "ALL"
        if wanted and normalize_text(period_name) != wanted:
            continue

        for group in period_block.get("groups", []) or []:
            group_name = group.get("groupName")
            for item in group.get("statisticsItems", []) or []:
                rows.append(
                    {
                        "period": period_name,
                        "group": group_name,
                        "name": item.get("name"),
                        "home": item.get("home"),
                        "away": item.get("away"),
                        "home_value": item.get("homeValue", to_number(item.get("home"))),
                        "away_value": item.get("awayValue", to_number(item.get("away"))),
                        "compare_code": item.get("compareCode"),
                        "statistics_type": item.get("statisticsType"),
                        "key": item.get("key"),
                    }
                )
    return rows


def _incident_player(incident: Dict[str, Any], key: str = "player") -> Optional[str]:
    value = incident.get(key)
    if isinstance(value, dict):
        return value.get("name") or value.get("shortName")
    return None


def normalize_incidents(
    payload: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Aplana goles, tarjetas, cambios y periodos."""
    if not payload:
        return []

    rows: List[Dict[str, Any]] = []
    for incident in payload.get("incidents", []) or []:
        is_home = incident.get("isHome")
        if is_home is True:
            side = "home"
        elif is_home is False:
            side = "away"
        else:
            side = None

        rows.append(
            {
                "type": incident.get("incidentType"),
                "class": incident.get("incidentClass"),
                "minute": incident.get("time"),
                "added_time": incident.get("addedTime"),
                "side": side,
                "player": _incident_player(incident, "player"),
                "player_in": _incident_player(incident, "playerIn"),
                "player_out": _incident_player(incident, "playerOut"),
                "assist": _incident_player(incident, "assist1")
                or _incident_player(incident, "assist"),
                "home_score": incident.get("homeScore"),
                "away_score": incident.get("awayScore"),
                "text": incident.get("text") or incident.get("description"),
                "reason": incident.get("reason"),
            }
        )
    return rows


def _normalize_missing_player(entry: Any) -> Dict[str, Any]:
    entry = entry if isinstance(entry, dict) else {}
    player = entry.get("player") or {}
    market = player.get("proposedMarketValueRaw") or {}
    return {
        "id": player.get("id"),
        "name": player.get("name") or player.get("shortName"),
        "short_name": player.get("shortName"),
        "position": player.get("position"),
        "reason": entry.get("description") or entry.get("reason"),
        "type": entry.get("type"),
        "expected_end_date": entry.get("expectedEndDate"),
        "market_value": market.get("value"),
    }


def _normalize_lineup_side(
    side: Optional[Dict[str, Any]],
    include_stats: bool = False,
) -> Dict[str, Any]:
    side = side or {}
    players: List[Dict[str, Any]] = []

    for entry in side.get("players", []) or []:
        player = entry.get("player") or {}
        stats = entry.get("statistics") or {}
        breakdown = entry.get("seasonRatingBreakdown") or {}
        season = None
        if breakdown:
            shot = breakdown.get("shot") or {}
            passing = breakdown.get("pass") or {}
            defending = breakdown.get("defending") or {}
            goalkeeping = breakdown.get("goalkeeping") or {}
            season = {
                "expected_goals": to_number(shot.get("expectedGoals")),
                "expected_assists": to_number(passing.get("expectedAssists")),
                "shots_per_game": to_number(shot.get("totalShotsPerGame")),
                "shots_on_target_per_game": to_number(
                    shot.get("shotsOnTargetPerGame")
                ),
                "defensive_contributions_per_game": to_number(
                    defending.get("defensiveContributionsPerGame")
                ),
                "duels_won_per_game": to_number(defending.get("duelsWonPerGame")),
                "goals_prevented": to_number(goalkeeping.get("goalsPrevented")),
                "saves_per_game": to_number(goalkeeping.get("savesPerGame")),
            }
        market = player.get("proposedMarketValueRaw") or {}
        row: Dict[str, Any] = {
            "id": player.get("id"),
            "name": player.get("name"),
            "short_name": player.get("shortName"),
            "shirt_number": entry.get("shirtNumber")
            if entry.get("shirtNumber") is not None
            else player.get("jerseyNumber"),
            "position": entry.get("position") or player.get("position"),
            "substitute": bool(entry.get("substitute")),
            "captain": bool(entry.get("captain")),
            "rating": to_number(stats.get("rating")),
            "avg_rating": to_number(entry.get("avgRating")),
            "market_value": market.get("value"),
            "country": (player.get("country") or {}).get("name"),
            "season": season,
        }
        if include_stats:
            row["statistics"] = stats
        players.append(row)

    missing = [
        _normalize_missing_player(entry)
        for entry in side.get("missingPlayers", []) or []
    ]
    return {
        "formation": side.get("formation"),
        "players": players,
        "missing_players": missing,
    }


def lineup_starters(
    lineups: Optional[Dict[str, Any]], side: str
) -> List[Dict[str, Any]]:
    """Jugadores titulares de un lado (los suplentes quedan fuera)."""
    players = ((lineups or {}).get(side) or {}).get("players") or []
    return [player for player in players if not player.get("substitute")]


def lineup_status(lineups: Optional[Dict[str, Any]]) -> str:
    """Devuelve ``confirmada``, ``probable`` o ``sin datos``."""
    if not lineups:
        return "sin datos"
    has_players = any(
        lineup_starters(lineups, side) for side in ("home", "away")
    )
    if not has_players:
        return "sin datos"
    return "confirmada" if lineups.get("confirmed") else "probable"


def normalize_lineups(
    payload: Optional[Dict[str, Any]],
    include_stats: bool = False,
) -> Optional[Dict[str, Any]]:
    if not payload:
        return None
    return {
        "confirmed": bool(payload.get("confirmed")),
        "home": _normalize_lineup_side(payload.get("home"), include_stats),
        "away": _normalize_lineup_side(payload.get("away"), include_stats),
    }


def lineup_players(lineups: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filas de jugadores con el lado (home/away), útil para CSV."""
    if not lineups:
        return []
    rows: List[Dict[str, Any]] = []
    for side in ("home", "away"):
        for player in (lineups.get(side) or {}).get("players", []) or []:
            row = {"side": side}
            row.update(player)
            rows.append(row)
    return rows


def normalize_standings(
    payload: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not payload:
        return []

    rows: List[Dict[str, Any]] = []
    for standing in payload.get("standings", []) or []:
        group = standing.get("name")
        for row in standing.get("rows", []) or []:
            scores_for = row.get("scoresFor")
            scores_against = row.get("scoresAgainst", row.get("scoresAgains"))
            goal_difference = None
            if isinstance(scores_for, (int, float)) and isinstance(
                scores_against, (int, float)
            ):
                goal_difference = scores_for - scores_against

            promotion = row.get("promotion") or {}
            rows.append(
                {
                    "group": group,
                    "position": row.get("position"),
                    "team": normalize_team(row.get("team")),
                    "matches": row.get("matches"),
                    "wins": row.get("wins"),
                    "draws": row.get("draws"),
                    "losses": row.get("losses"),
                    "scores_for": scores_for,
                    "scores_against": scores_against,
                    "goal_difference": goal_difference,
                    "points": row.get("points"),
                    "promotion": promotion.get("text"),
                    "form": row.get("form"),
                }
            )
    return rows


def normalize_seasons(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not payload:
        return []
    seasons = []
    for season in payload.get("seasons", []) or []:
        normalized = normalize_season(season)
        if normalized:
            seasons.append(normalized)
    return seasons


def normalize_team_info(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not payload:
        return {}
    team = payload.get("team") or {}
    primary = team.get("primaryUniqueTournament") or {}
    primary_category = primary.get("category") or {}
    return {
        "team": normalize_team(team),
        "full_name": team.get("fullName"),
        "manager": (team.get("manager") or {}).get("name"),
        "venue": normalize_venue(team.get("venue")),
        "country": (team.get("country") or {}).get("name"),
        "primary_tournament": {
            "id": primary.get("id"),
            "name": primary.get("name"),
            "slug": primary.get("slug"),
            "category": primary_category.get("name"),
        }
        if primary
        else None,
        "pregame_form": payload.get("pregameForm"),
    }


def normalize_player_info(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not payload:
        return {}
    player = payload.get("player") or {}
    market_value = player.get("proposedMarketValueRaw") or {}
    return {
        "id": player.get("id"),
        "name": player.get("name"),
        "short_name": player.get("shortName"),
        "slug": player.get("slug"),
        "position": player.get("position"),
        "positions_detailed": player.get("positionsDetailed"),
        "jersey_number": player.get("jerseyNumber"),
        "height": player.get("height"),
        "preferred_foot": player.get("preferredFoot"),
        "date_of_birth_timestamp": player.get("dateOfBirthTimestamp"),
        "date_of_birth": iso_utc(player.get("dateOfBirthTimestamp")),
        "country": (player.get("country") or {}).get("name"),
        "team": normalize_team(player.get("team")),
        "market_value": market_value.get("value"),
        "market_value_currency": market_value.get("currency"),
        "contract_until_timestamp": player.get("contractUntilTimestamp"),
    }
