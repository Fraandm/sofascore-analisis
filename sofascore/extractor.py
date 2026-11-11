"""Lógica de alto nivel: partidos por fecha, detalles, equipos y torneos."""

from __future__ import annotations

import difflib
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import endpoints, normalize
from .client import SofaScoreClient
from .exceptions import BlockedError, NotFoundError, SofaScoreError

# Nombres de país en español que no coinciden con la API (en inglés).
COUNTRY_ALIASES = {
    "espana": "Spain",
    "alemania": "Germany",
    "inglaterra": "England",
    "francia": "France",
    "italia": "Italy",
    "portugal": "Portugal",
    "paises bajos": "Netherlands",
    "holanda": "Netherlands",
    "brasil": "Brazil",
    "argentina": "Argentina",
    "mexico": "Mexico",
    "estados unidos": "USA",
    "usa": "USA",
    "turquia": "Türkiye",
    "turkiye": "Türkiye",
    "belgica": "Belgium",
    "suiza": "Switzerland",
    "austria": "Austria",
    "escocia": "Scotland",
    "gales": "Wales",
    "irlanda": "Ireland",
    "dinamarca": "Denmark",
    "suecia": "Sweden",
    "noruega": "Norway",
    "polonia": "Poland",
    "ucrania": "Ukraine",
    "rusia": "Russia",
    "grecia": "Greece",
    "croacia": "Croatia",
    "serbia": "Serbia",
    "chequia": "Czechia",
    "republica checa": "Czechia",
    "japon": "Japan",
    "corea del sur": "South Korea",
    "china": "China",
    "australia": "Australia",
    "marruecos": "Morocco",
    "argelia": "Algeria",
    "tunez": "Tunisia",
    "egipto": "Egypt",
    "sudafrica": "South Africa",
    "colombia": "Colombia",
    "chile": "Chile",
    "peru": "Peru",
    "uruguay": "Uruguay",
    "ecuador": "Ecuador",
    "paraguay": "Paraguay",
    "bolivia": "Bolivia",
    "venezuela": "Venezuela",
    "costa rica": "Costa Rica",
    "canada": "Canada",
    "europa": "Europe",
    "sudamerica": "South America",
    "america": "Americas",
    "africa": "Africa",
    "asia": "Asia",
}


def resolve_timezone(name: Optional[str]):
    """Resuelve 'local', 'UTC', '+02:00' o una zona IANA como Europe/Madrid."""
    if not name or normalize.normalize_text(name) in ("local", "sistema", "system"):
        return datetime.now().astimezone().tzinfo or timezone.utc

    text = str(name).strip()
    if text.upper() in ("UTC", "GMT", "Z"):
        return timezone.utc

    match = re.fullmatch(r"([+-])(\d{1,2})(?::?(\d{2}))?", text)
    if match:
        sign = 1 if match.group(1) == "+" else -1
        hours = int(match.group(2))
        minutes = int(match.group(3) or 0)
        if hours > 14 or minutes > 59:
            raise SofaScoreError(
                f'Offset de zona horaria no válido: "{name}".'
            )
        return timezone(sign * timedelta(hours=hours, minutes=minutes))

    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(text)
    except Exception as exc:  # ZoneInfoNotFoundError y falta de tzdata
        raise SofaScoreError(
            f'Zona horaria no válida: "{name}". Usa "local", "UTC", '
            'un offset como "+02:00" o una zona IANA como "Europe/Madrid". '
            "En Windows puede hacer falta instalar el paquete 'tzdata'."
        ) from exc


def parse_day(value: Optional[str]) -> str:
    """Acepta YYYY-MM-DD, DD/MM/YYYY, hoy, ayer y mañana."""
    if not value:
        return date.today().isoformat()

    key = normalize.normalize_text(value)
    today = date.today()
    if key in ("hoy", "today"):
        return today.isoformat()
    if key in ("ayer", "yesterday"):
        return (today - timedelta(days=1)).isoformat()
    if key in ("manana", "tomorrow"):
        return (today + timedelta(days=1)).isoformat()

    text = str(value).strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue

    raise SofaScoreError(
        f'Fecha no válida: "{value}". Usa YYYY-MM-DD, hoy, ayer o mañana.'
    )


class SofaScoreExtractor:
    def __init__(
        self,
        client: Optional[SofaScoreClient] = None,
        workers: int = 4,
        verbose: bool = False,
    ) -> None:
        self.client = client or SofaScoreClient()
        self.workers = max(1, int(workers))
        self.verbose = verbose

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"[sofascore] {message}", file=sys.stderr)

    def _warn(self, message: str) -> None:
        print(f"Aviso: {message}", file=sys.stderr)

    @staticmethod
    def _dedupe_matches(matches: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        result = []
        for match in matches:
            match_id = match.get("id")
            if match_id in seen:
                continue
            seen.add(match_id)
            result.append(match)
        return result

    @staticmethod
    def _match_tournament(match: Dict[str, Any], query: str) -> bool:
        tournament = match.get("tournament") or {}
        name = normalize.normalize_text(tournament.get("name"))
        slug = normalize.normalize_text(tournament.get("slug"))
        q = normalize.normalize_text(query)
        return bool(q) and (q == name or q == slug or q in name or name in q)

    # ------------------------------------------------------------------
    # Búsqueda y catálogos
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        type_filter: str = "all",
        sport: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            raise SofaScoreError("La búsqueda no puede estar vacía.")
        payload = self.client.get_json(endpoints.search(query.strip()), ttl=300)
        return normalize.normalize_search_results(
            payload,
            type_filter=type_filter,
            sport=sport,
            limit=limit,
        )

    def get_categories(self) -> List[Dict[str, Any]]:
        payload = self.client.get_json(endpoints.all_categories(), ttl=86400)
        return [
            normalize.normalize_category(category)
            for category in payload.get("categories") or []
        ]

    def resolve_country(self, query: str) -> Dict[str, Any]:
        """Resuelve 'España', 'spain' o 'SP' a una categoría de SofaScore."""
        original = query
        wanted = normalize.normalize_text(query)
        alias = COUNTRY_ALIASES.get(wanted)
        if alias:
            wanted = normalize.normalize_text(alias)

        categories = self.get_categories()
        partial: List[Dict[str, Any]] = []
        for category in categories:
            name = normalize.normalize_text(category.get("name"))
            slug = normalize.normalize_text(category.get("slug"))
            if wanted and wanted in (name, slug):
                return category
            if len(wanted) >= 3 and (wanted in name or name in wanted):
                partial.append(category)

        if partial:
            partial.sort(
                key=lambda c: (
                    len(normalize.normalize_text(c.get("name"))),
                    -(c.get("priority") or 0),
                )
            )
            return partial[0]

        names = {
            normalize.normalize_text(category.get("name")): category
            for category in categories
        }
        close = difflib.get_close_matches(wanted, list(names.keys()), n=3, cutoff=0.6)
        suggestions = ", ".join(names[key].get("name") for key in close if key in names)
        hint = f" Quizá quisiste decir: {suggestions}." if suggestions else ""
        raise NotFoundError(
            f'No se encontró el país o categoría "{original}".{hint} '
            "Prueba con el nombre en inglés (Spain, England, Brazil...) "
            "o ejecuta: python -m sofascore categories --filter <texto>."
        )

    def resolve_tournament(self, query: str) -> Dict[str, Any]:
        results = self.search(
            query, type_filter="tournament", sport="football", limit=10
        )
        if not results:
            raise NotFoundError(
                f'No se encontró el torneo "{query}". '
                "Prueba con otro nombre o usa el ID del torneo."
            )
        first = results[0]
        unique_id = first.get("unique_tournament_id") or first.get("id")
        return {
            "unique_tournament_id": unique_id,
            "name": first.get("name"),
            "slug": first.get("slug"),
            "category": first.get("category"),
            "category_id": first.get("category_id"),
        }

    # ------------------------------------------------------------------
    # Partidos
    # ------------------------------------------------------------------
    def _scheduled_tournaments(self, day: str) -> List[Dict[str, Any]]:
        """Lista los torneos que tienen partidos en una fecha."""
        tournaments: List[Dict[str, Any]] = []
        seen = set()
        page = 1

        while page <= 50:
            payload = self.client.get_json(
                endpoints.scheduled_tournaments(day, page), ttl=180
            )
            scheduled = payload.get("scheduled") or []
            for entry in scheduled:
                tournament = entry.get("tournament") or {}
                unique = tournament.get("uniqueTournament") or {}
                unique_id = unique.get("id")
                if not unique_id or unique_id in seen:
                    continue
                seen.add(unique_id)
                category = tournament.get("category") or unique.get("category") or {}
                tournaments.append(
                    {
                        "unique_tournament_id": unique_id,
                        "name": unique.get("name") or tournament.get("name"),
                        "slug": unique.get("slug") or tournament.get("slug"),
                        "category": category.get("name"),
                        "category_id": category.get("id"),
                        "country": (category.get("country") or {}).get("name")
                        or category.get("name"),
                        "priority": tournament.get("priority"),
                    }
                )

            if not payload.get("hasNextPage"):
                break
            page += 1

        return tournaments

    def _filter_tournaments(
        self, tournaments: Sequence[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        wanted = normalize.normalize_text(query)
        exact: List[Dict[str, Any]] = []
        partial: List[Dict[str, Any]] = []

        for tournament in tournaments:
            name = normalize.normalize_text(tournament.get("name"))
            slug = normalize.normalize_text(tournament.get("slug"))
            if wanted and wanted in (name, slug):
                exact.append(tournament)
            elif wanted and (wanted in name or name in wanted or wanted in slug):
                partial.append(tournament)

        return exact or partial

    def _fetch_tournament_events(
        self, unique_tournament_id: int, day: str
    ) -> List[Dict[str, Any]]:
        payload = self.client.get_json(
            endpoints.tournament_scheduled_events(unique_tournament_id, day),
            ttl=180,
        )
        return payload.get("events") or []

    @staticmethod
    def _dedupe_tournaments(
        tournaments: Iterable[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        seen = set()
        result = []
        for tournament in tournaments:
            unique_id = tournament.get("unique_tournament_id")
            if not unique_id or unique_id in seen:
                continue
            seen.add(unique_id)
            result.append(tournament)
        return result

    @staticmethod
    def _api_days(day: str, tz) -> List[str]:
        """Días de API necesarios para cubrir el día local completo.

        La API devuelve una ventana de 48 h centrada en el día solicitado:
        [D-1 12:00 UTC, D+1 12:00 UTC). Para zonas UTC+13/+14 hace falta
        consultar también D-1.
        """
        target = date.fromisoformat(day)
        start_utc = datetime.combine(
            target, datetime_time.min, tzinfo=tz
        ).astimezone(timezone.utc)
        window_start = datetime.combine(
            target - timedelta(days=1),
            datetime_time(12, 0),
            tzinfo=timezone.utc,
        )
        api_days = [target]
        if start_utc < window_start:
            api_days.insert(0, target - timedelta(days=1))
        return [item.isoformat() for item in api_days]

    @staticmethod
    def _filter_by_local_date(
        matches: Iterable[Dict[str, Any]], day: str, tz
    ) -> List[Dict[str, Any]]:
        target = date.fromisoformat(day)
        result = []
        for match in matches:
            timestamp = match.get("start_timestamp")
            if timestamp is None:
                continue
            try:
                local = datetime.fromtimestamp(int(timestamp), tz=tz)
            except (TypeError, ValueError, OSError, OverflowError):
                continue
            if local.date() == target:
                match["start_time_local"] = local.isoformat()
                result.append(match)
        return result

    def _fetch_many_tournaments(
        self, tournaments: Sequence[Dict[str, Any]], day: str
    ) -> List[Dict[str, Any]]:
        if not tournaments:
            return []

        if len(tournaments) == 1 or self.workers <= 1:
            events: List[Dict[str, Any]] = []
            for tournament in tournaments:
                try:
                    events.extend(
                        self._fetch_tournament_events(
                            int(tournament["unique_tournament_id"]), day
                        )
                    )
                except NotFoundError:
                    continue
                except SofaScoreError as exc:
                    self._warn(f'{tournament.get("name")}: {exc}')
            return events

        events = []
        errors: List[BaseException] = []
        total = len(tournaments)

        with ThreadPoolExecutor(max_workers=min(self.workers, total)) as executor:
            futures = {
                executor.submit(
                    self._fetch_tournament_events,
                    int(tournament["unique_tournament_id"]),
                    day,
                ): tournament
                for tournament in tournaments
            }
            completed = 0
            for future in as_completed(futures):
                tournament = futures[future]
                completed += 1
                try:
                    events.extend(future.result())
                except NotFoundError:
                    pass
                except Exception as exc:  # noqa: BLE001 - se reporta al final
                    errors.append(exc)
                    self._log(f'Aviso en {tournament.get("name")}: {exc}')
                if self.verbose and (completed % 10 == 0 or completed == total):
                    self._log(f"Progreso: {completed}/{total} torneos")

        if errors and not events:
            raise errors[0]
        if errors:
            self._warn(
                f"{len(errors)} torneo(s) fallaron; se muestran los datos disponibles."
            )
        return events

    def get_matches_by_date(
        self,
        day: Optional[str],
        country: Optional[str] = None,
        tournament: Optional[str] = None,
        live: bool = False,
        limit: Optional[int] = None,
        max_tournaments: int = 0,
        timezone_name: str = "local",
    ) -> List[Dict[str, Any]]:
        """Partidos de una fecha en la zona horaria indicada.

        La API devuelve una ventana de 48 h centrada en la fecha, así que
        después se filtra por el día local real. Si se indica ``country``,
        se usa el endpoint de categoría. Si no, se consulta la lista de
        torneos y luego cada torneo.
        """
        day = parse_day(day)
        api_mode = normalize.normalize_text(timezone_name) in (
            "api",
            "none",
            "ninguna",
            "sin filtro",
        )
        if api_mode:
            tz = None
            api_days = [day]
        else:
            tz = resolve_timezone(timezone_name)
            api_days = self._api_days(day, tz)

        self._log(
            f"Fecha local: {day} ({timezone_name}). Días de API: {', '.join(api_days)}"
        )
        events: List[Dict[str, Any]] = []

        if country:
            category = self.resolve_country(country)
            self._log(
                f'Categoría: {category.get("name")} (id {category.get("id")})'
            )
            for api_day in api_days:
                payload = self.client.get_json(
                    endpoints.category_scheduled_events(
                        int(category["id"]), api_day
                    ),
                    ttl=180,
                )
                events.extend(payload.get("events") or [])
        else:
            tournaments: List[Dict[str, Any]] = []
            for api_day in api_days:
                tournaments.extend(self._scheduled_tournaments(api_day))
            tournaments = self._dedupe_tournaments(tournaments)

            if tournament:
                filtered = self._filter_tournaments(tournaments, tournament)
                if filtered:
                    tournaments = filtered
                else:
                    resolved = self.resolve_tournament(tournament)
                    tournaments = [resolved]

            if max_tournaments and max_tournaments > 0:
                tournaments = tournaments[:max_tournaments]

            self._log(f"{len(tournaments)} torneo(s) con partidos el {day}")
            for api_day in api_days:
                events.extend(self._fetch_many_tournaments(tournaments, api_day))

        matches = normalize.normalize_events(events)
        matches = self._dedupe_matches(matches)

        if tz is not None:
            matches = self._filter_by_local_date(matches, day, tz)

        if tournament:
            matches = [
                match for match in matches if self._match_tournament(match, tournament)
            ]
        if live:
            matches = [
                match
                for match in matches
                if match.get("status_type") == "inprogress"
            ]

        matches.sort(key=lambda m: (m.get("start_timestamp") or 0, m.get("id") or 0))
        if limit is not None:
            matches = matches[: max(0, int(limit))]
        return matches

    def get_live_matches(
        self,
        country: Optional[str] = None,
        tournament: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        payload = self.client.get_json(endpoints.live_events(), ttl=30)
        matches = normalize.normalize_events(payload.get("events") or [])
        matches = self._dedupe_matches(matches)

        if country:
            category = self.resolve_country(country)
            category_id = category.get("id")
            matches = [
                match
                for match in matches
                if (match.get("tournament") or {}).get("category_id") == category_id
            ]
        if tournament:
            matches = [
                match for match in matches if self._match_tournament(match, tournament)
            ]

        matches.sort(key=lambda m: (m.get("start_timestamp") or 0, m.get("id") or 0))
        if limit is not None:
            matches = matches[: max(0, int(limit))]
        return matches

    # ------------------------------------------------------------------
    # Detalle de un partido
    # ------------------------------------------------------------------
    def get_match(
        self,
        event_id: int,
        sections: Optional[Iterable[str]] = None,
        period: Optional[str] = None,
        lineup_stats: bool = False,
        include_raw: bool = False,
    ) -> Dict[str, Any]:
        sections = set(sections or [])
        event_payload = self.client.get_json(endpoints.event(event_id), ttl=45)
        event_raw = event_payload.get("event") or {}

        detail: Dict[str, Any] = {
            "match": normalize.normalize_event(event_raw),
        }
        raw: Dict[str, Any] = {}
        if include_raw:
            raw["event"] = event_raw

        if "statistics" in sections:
            try:
                payload = self.client.get_json(
                    endpoints.event_statistics(event_id), ttl=45
                )
            except NotFoundError:
                payload = None
                self._warn(f"El partido {event_id} no tiene estadísticas disponibles.")
            detail["statistics"] = normalize.normalize_statistics(payload, period)
            if include_raw:
                raw["statistics"] = payload

        if "lineups" in sections:
            try:
                payload = self.client.get_json(
                    endpoints.event_lineups(event_id), ttl=45
                )
            except NotFoundError:
                payload = None
                self._warn(f"El partido {event_id} no tiene alineaciones disponibles.")
            detail["lineups"] = normalize.normalize_lineups(payload, lineup_stats)
            if include_raw:
                raw["lineups"] = payload

        if "incidents" in sections:
            try:
                payload = self.client.get_json(
                    endpoints.event_incidents(event_id), ttl=45
                )
            except NotFoundError:
                payload = None
                self._warn(f"El partido {event_id} no tiene incidencias disponibles.")
            detail["incidents"] = normalize.normalize_incidents(payload)
            if include_raw:
                raw["incidents"] = payload

        if "h2h" in sections:
            try:
                detail["h2h"] = self.client.get_json(
                    endpoints.event_h2h(event_id), ttl=300
                )
            except NotFoundError:
                detail["h2h"] = None
                self._warn(f"El partido {event_id} no tiene historial H2H.")
            if include_raw:
                raw["h2h"] = detail["h2h"]

        if "graph" in sections:
            try:
                detail["graph"] = self.client.get_json(
                    endpoints.event_graph(event_id), ttl=45
                )
            except NotFoundError:
                detail["graph"] = None
                self._warn(f"El partido {event_id} no tiene gráfico de juego.")
            if include_raw:
                raw["graph"] = detail["graph"]

        if "best_players" in sections:
            try:
                detail["best_players"] = self.client.get_json(
                    endpoints.event_best_players(event_id), ttl=45
                )
            except NotFoundError:
                detail["best_players"] = None
                self._warn(f"El partido {event_id} no tiene mejores jugadores.")

        if include_raw:
            detail["_raw"] = raw
        return detail

    # ------------------------------------------------------------------
    # Árbitros
    # ------------------------------------------------------------------
    @staticmethod
    def _referee_stats_from_payload(payload: Any) -> Dict[str, Optional[float]]:
        """Tarjetas y faltas de un partido a partir de sus estadísticas."""
        rows = normalize.normalize_statistics(payload, "ALL")
        values: Dict[str, Optional[float]] = {}
        for row in rows:
            key = row.get("key")
            if not key or key in values:
                continue
            home = row.get("home_value")
            away = row.get("away_value")
            total = 0.0
            found = False
            for value in (home, away):
                if value is None:
                    continue
                try:
                    total += float(value)
                    found = True
                except (TypeError, ValueError):
                    continue
            if found:
                values[key] = total

        yellow = values.get("yellowCards")
        red = values.get("redCards")
        if yellow is None and red is None:
            cards = None
        else:
            cards = (yellow or 0.0) + (red or 0.0)
        return {
            "yellow_cards": yellow,
            "red_cards": red,
            "cards": cards,
            "fouls": values.get("fouls"),
        }

    def _referee_match_stats(self, event_id: int) -> Dict[str, Any]:
        payload = self.client.get_json(
            endpoints.event_statistics(event_id), ttl=7 * 24 * 3600
        )
        row = self._referee_stats_from_payload(payload)
        row["event_id"] = event_id
        return row

    def get_referee_profile(
        self,
        referee_id: int,
        tournament_id: Optional[int] = None,
        season_id: Optional[int] = None,
        before_timestamp: Optional[int] = None,
        max_matches: int = 6,
    ) -> Dict[str, Any]:
        """Perfil del árbitro: tarjetas y faltas por partido.

        Combina las estadísticas de competición con una muestra de sus
        últimos partidos dirigidos. La muestra es la fuente principal de
        faltas porque la ficha del árbitro solo publica tarjetas.
        """
        detail_payload = self.client.get_json(
            endpoints.referee(int(referee_id)), ttl=7 * 24 * 3600
        )
        referee = detail_payload.get("referee") or {}

        stats_rows: List[Dict[str, Any]] = []
        try:
            stats_payload = self.client.get_json(
                endpoints.referee_statistics(int(referee_id)),
                ttl=7 * 24 * 3600,
            )
            stats_rows = stats_payload.get("statistics") or []
        except NotFoundError:
            stats_rows = []

        competition = None
        for row in stats_rows:
            row_tournament = row.get("uniqueTournament") or {}
            if tournament_id is not None and row_tournament.get("id") == tournament_id:
                competition = row
                break
        if competition is None and stats_rows:
            competition = max(
                stats_rows, key=lambda row: row.get("appearances") or 0
            )

        events: List[Dict[str, Any]] = []
        try:
            events_payload = self.client.get_json(
                endpoints.referee_events(int(referee_id)), ttl=3600
            )
            events = events_payload.get("events") or []
        except NotFoundError:
            events = []

        candidates: List[Dict[str, Any]] = []
        for event in events:
            if (event.get("status") or {}).get("type") != "finished":
                continue
            timestamp = event.get("startTimestamp") or 0
            if before_timestamp is not None and int(timestamp) >= int(before_timestamp):
                continue
            event_season = (event.get("season") or {}).get("id")
            if (
                season_id is not None
                and event_season is not None
                and event_season != season_id
            ):
                continue
            event_tournament = (
                (event.get("tournament") or {}).get("uniqueTournament") or {}
            ).get("id")
            if (
                tournament_id is not None
                and event_tournament is not None
                and event_tournament != tournament_id
            ):
                continue
            candidates.append(event)
        candidates.sort(
            key=lambda event: event.get("startTimestamp") or 0, reverse=True
        )
        sample = candidates[: max(0, int(max_matches))]

        match_stats: List[Dict[str, Any]] = []
        if sample:
            with ThreadPoolExecutor(max_workers=min(4, len(sample))) as pool:
                futures = {
                    pool.submit(self._referee_match_stats, int(event["id"])): event
                    for event in sample
                    if event.get("id") is not None
                }
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    except Exception:  # noqa: BLE001 - se informa y se continúa
                        continue
                    if result:
                        match_stats.append(result)

        def average(key: str) -> Optional[float]:
            values = [
                float(item[key])
                for item in match_stats
                if item.get(key) is not None
            ]
            if not values:
                return None
            return round(sum(values) / len(values), 2)

        sample_cards = average("cards")
        sample_fouls = average("fouls")
        sample_matches = len(match_stats)

        career_apps = float(referee.get("games") or 0)
        career_cards = (
            float(referee.get("yellowCards") or 0)
            + float(referee.get("redCards") or 0)
            + float(referee.get("yellowRedCards") or 0)
        )
        career_cards_per_match = (
            round(career_cards / career_apps, 2) if career_apps else None
        )

        competition_cards_per_match = None
        if competition:
            appearances = float(competition.get("appearances") or 0)
            cards = (
                float(competition.get("yellowCards") or 0)
                + float(competition.get("redCards") or 0)
                + float(competition.get("yellowRedCards") or 0)
            )
            if appearances:
                competition_cards_per_match = round(cards / appearances, 2)

        if sample_matches >= 2 and sample_cards is not None:
            cards_per_match = sample_cards
            source = f"muestra reciente ({sample_matches} partidos)"
        elif competition_cards_per_match is not None:
            cards_per_match = competition_cards_per_match
            source = "estadísticas de la competición"
        else:
            cards_per_match = career_cards_per_match
            source = "estadísticas de carrera"

        return {
            "id": referee.get("id") or int(referee_id),
            "name": referee.get("name"),
            "country": (referee.get("country") or {}).get("name"),
            "career": {
                "games": referee.get("games"),
                "yellow_cards": referee.get("yellowCards"),
                "red_cards": referee.get("redCards"),
                "yellow_red_cards": referee.get("yellowRedCards"),
                "cards_per_match": career_cards_per_match,
            },
            "competition": (
                {
                    "id": (competition.get("uniqueTournament") or {}).get("id"),
                    "name": (competition.get("uniqueTournament") or {}).get("name"),
                    "appearances": competition.get("appearances"),
                    "yellow_cards": competition.get("yellowCards"),
                    "red_cards": competition.get("redCards"),
                    "yellow_red_cards": competition.get("yellowRedCards"),
                    "penalties": competition.get("penalty"),
                    "cards_per_match": competition_cards_per_match,
                }
                if competition
                else None
            ),
            "sample": {
                "matches": sample_matches,
                "cards_per_match": sample_cards,
                "fouls_per_match": sample_fouls,
                "event_ids": [item.get("event_id") for item in match_stats],
            },
            "cards_per_match": cards_per_match,
            "fouls_per_match": sample_fouls,
            "source": source,
        }

    # ------------------------------------------------------------------
    # Equipos
    # ------------------------------------------------------------------
    def get_team(self, team_id: int) -> Dict[str, Any]:
        payload = self.client.get_json(endpoints.team(team_id), ttl=3600)
        return normalize.normalize_team_info(payload)

    def get_team_matches(
        self,
        team_id: int,
        direction: str = "last",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        if direction not in ("last", "next"):
            raise SofaScoreError('direction debe ser "last" o "next".')
        limit = max(0, int(limit))
        if limit == 0:
            return []

        matches: List[Dict[str, Any]] = []
        seen = set()
        page = 0

        while len(matches) < limit and page < 30:
            payload = self.client.get_json(
                endpoints.team_events(team_id, direction, page), ttl=120
            )
            events = payload.get("events") or []
            for match in normalize.normalize_events(events):
                match_id = match.get("id")
                if match_id in seen:
                    continue
                seen.add(match_id)
                matches.append(match)

            if not payload.get("hasNextPage") or not events:
                break
            page += 1

        reverse = direction == "last"
        matches.sort(
            key=lambda m: (m.get("start_timestamp") or 0, m.get("id") or 0),
            reverse=reverse,
        )
        return matches[:limit]

    # ------------------------------------------------------------------
    # Torneos
    # ------------------------------------------------------------------
    def get_tournament_seasons(self, unique_tournament_id: int) -> List[Dict[str, Any]]:
        payload = self.client.get_json(
            endpoints.tournament_seasons(unique_tournament_id), ttl=3600
        )
        seasons = normalize.normalize_seasons(payload)
        if not seasons:
            raise NotFoundError(
                f"El torneo {unique_tournament_id} no tiene temporadas disponibles."
            )
        return seasons

    def get_season_matches(
        self,
        unique_tournament_id: int,
        season_id: int,
        direction: str = "last",
        limit: int = 10,
        round_number: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if direction not in ("last", "next"):
            raise SofaScoreError('direction debe ser "last" o "next".')
        limit = max(0, int(limit))

        matches: List[Dict[str, Any]] = []
        seen = set()

        if round_number is not None:
            payload = self.client.get_json(
                endpoints.tournament_season_round(
                    unique_tournament_id, season_id, int(round_number)
                ),
                ttl=120,
            )
            for match in normalize.normalize_events(payload.get("events") or []):
                if match.get("id") not in seen:
                    seen.add(match.get("id"))
                    matches.append(match)
            matches.sort(key=lambda m: (m.get("start_timestamp") or 0, m.get("id") or 0))
            return matches[:limit] if limit else matches

        page = 0
        while len(matches) < limit and page < 30:
            payload = self.client.get_json(
                endpoints.tournament_season_events(
                    unique_tournament_id, season_id, direction, page
                ),
                ttl=120,
            )
            events = payload.get("events") or []
            for match in normalize.normalize_events(events):
                match_id = match.get("id")
                if match_id in seen:
                    continue
                seen.add(match_id)
                matches.append(match)
            if not payload.get("hasNextPage") or not events:
                break
            page += 1

        reverse = direction == "last"
        matches.sort(
            key=lambda m: (m.get("start_timestamp") or 0, m.get("id") or 0),
            reverse=reverse,
        )
        return matches[:limit]

    def get_standings(
        self, unique_tournament_id: int, season_id: int
    ) -> List[Dict[str, Any]]:
        payload = self.client.get_json(
            endpoints.tournament_standings(unique_tournament_id, season_id), ttl=300
        )
        return normalize.normalize_standings(payload)

    # ------------------------------------------------------------------
    # Jugadores
    # ------------------------------------------------------------------
    def get_player(self, player_id: int) -> Dict[str, Any]:
        payload = self.client.get_json(endpoints.player(player_id), ttl=3600)
        return normalize.normalize_player_info(payload)
