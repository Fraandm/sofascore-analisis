"""Interfaz de línea de comandos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import __version__, export, form, normalize, simulation, upcoming
from .client import ClientConfig, SofaScoreClient, default_cache_dir
from .exceptions import SofaScoreError
from .extractor import SofaScoreExtractor


def _add_common(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("conexión y caché")
    group.add_argument(
        "--no-cache",
        action="store_true",
        help="No leer ni escribir la caché en disco.",
    )
    group.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Directorio de caché (por defecto: %%LOCALAPPDATA%%).",
    )
    group.add_argument(
        "--cache-ttl",
        type=int,
        default=300,
        help="Segundos que se conserva una respuesta en caché (por defecto 300).",
    )
    group.add_argument(
        "--rate-limit",
        type=float,
        default=0.2,
        help="Segundos mínimos entre peticiones (por defecto 0.2).",
    )
    group.add_argument(
        "--timeout", type=float, default=30.0, help="Timeout por petición en segundos."
    )
    group.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Hilos para consultar varios torneos (por defecto 4).",
    )
    group.add_argument("--proxy", default=None, help="Proxy HTTP(S), p. ej. http://host:8080.")
    group.add_argument(
        "--no-ipv4",
        action="store_true",
        help="No forzar IPv4 (SofaScore suele bloquear la ruta IPv6).",
    )
    group.add_argument(
        "--base-url",
        default=None,
        help="URL base alternativa de la API (avanzado).",
    )
    group.add_argument(
        "--dump-raw",
        type=Path,
        default=None,
        help="Guarda cada respuesta cruda en este directorio (depuración).",
    )
    group.add_argument("--debug", action="store_true", help="Muestra cada petición HTTP.")
    group.add_argument(
        "-v", "--verbose", action="store_true", help="Muestra progreso y avisos."
    )


def _add_output(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("salida")
    group.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Archivo de salida. Si se omite, escribe por stdout.",
    )
    group.add_argument(
        "-f",
        "--format",
        choices=["json", "jsonl", "csv"],
        default=None,
        help="Formato de salida. Si se omite, se deduce de la extensión.",
    )
    group.add_argument(
        "--compact", action="store_true", help="JSON compacto (sin indentación)."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sofascore",
        description=(
            "Extrae partidos, estadísticas, alineaciones e incidencias de fútbol "
            "desde la API interna de SofaScore."
        ),
        epilog="Ejemplo: python -m sofascore date 2026-11-04 --country Spain -f csv -o partidos.csv",
    )
    parser.add_argument(
        "--version", action="version", version=f"sofascore-extractor {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search ------------------------------------------------------------
    p = subparsers.add_parser(
        "search",
        help="Busca equipos, jugadores, torneos o partidos.",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument("query", help="Texto a buscar, p. ej. 'real madrid'.")
    p.add_argument(
        "--type",
        choices=["all", "team", "player", "tournament", "event", "manager"],
        default="all",
        help="Filtra por tipo de entidad.",
    )
    p.add_argument(
        "--sport",
        default="football",
        help="Filtra por deporte (por defecto football; usa 'all' para todos).",
    )
    p.add_argument("--limit", type=int, default=20, help="Máximo de resultados.")

    # date --------------------------------------------------------------
    p = subparsers.add_parser(
        "date",
        help="Partidos de una fecha (YYYY-MM-DD, hoy, ayer, mañana).",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument("date", help="Fecha: 2026-11-04, 04/11/2026, hoy, ayer...")
    p.add_argument(
        "--country",
        default=None,
        help="País o categoría (Spain, England, España...). Reduce a 1 petición.",
    )
    p.add_argument(
        "--tournament",
        default=None,
        help="Nombre del torneo (Champions League, LaLiga...).",
    )
    p.add_argument(
        "--timezone",
        default="local",
        help=(
            "Zona horaria para decidir qué partidos caen en la fecha: local, "
            "UTC, Europe/Madrid o +02:00 (por defecto local)."
        ),
    )
    p.add_argument(
        "--live", action="store_true", help="Solo partidos en juego en ese momento."
    )
    p.add_argument("--limit", type=int, default=None, help="Máximo de partidos.")
    p.add_argument(
        "--max-tournaments",
        type=int,
        default=0,
        help="Limita el número de torneos a consultar (0 = todos).",
    )

    # live --------------------------------------------------------------
    p = subparsers.add_parser(
        "live",
        help="Partidos que se están jugando ahora.",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument("--country", default=None, help="Filtra por país/categoría.")
    p.add_argument("--tournament", default=None, help="Filtra por torneo.")
    p.add_argument("--limit", type=int, default=None, help="Máximo de partidos.")

    # match -------------------------------------------------------------
    p = subparsers.add_parser(
        "match",
        help="Detalle de un partido por su ID de SofaScore.",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument("event_id", type=int, help="ID del partido en SofaScore.")
    p.add_argument("--stats", action="store_true", help="Incluye estadísticas.")
    p.add_argument("--lineups", action="store_true", help="Incluye alineaciones.")
    p.add_argument("--incidents", action="store_true", help="Incluye goles/tarjetas/cambios.")
    p.add_argument("--h2h", action="store_true", help="Incluye historial H2H.")
    p.add_argument("--graph", action="store_true", help="Incluye gráfico de juego.")
    p.add_argument(
        "--best-players", action="store_true", help="Incluye mejores jugadores."
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Incluye todas las secciones anteriores.",
    )
    p.add_argument(
        "--period",
        choices=["ALL", "1ST", "2ND", "ET", "PEN"],
        default=None,
        help="Filtra estadísticas por periodo.",
    )
    p.add_argument(
        "--lineup-stats",
        action="store_true",
        help="Incluye las estadísticas individuales de cada jugador.",
    )
    p.add_argument(
        "--raw",
        action="store_true",
        help="Incluye las respuestas crudas de la API en '_raw'.",
    )

    # team --------------------------------------------------------------
    p = subparsers.add_parser(
        "team",
        help="Información y partidos de un equipo.",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument("team_id", type=int, help="ID del equipo en SofaScore.")
    p.add_argument("--last", type=int, default=None, help="Últimos N partidos.")
    p.add_argument("--next", type=int, default=None, help="Próximos N partidos.")

    # tournament --------------------------------------------------------
    p = subparsers.add_parser(
        "tournament",
        help="Temporadas, partidos y clasificación de un torneo.",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument("tournament_id", type=int, help="ID único del torneo.")
    p.add_argument("--seasons", action="store_true", help="Lista las temporadas.")
    p.add_argument("--season", type=int, default=None, help="ID de temporada.")
    p.add_argument("--last", type=int, default=None, help="Últimos N partidos.")
    p.add_argument("--next", type=int, default=None, help="Próximos N partidos.")
    p.add_argument("--round", type=int, default=None, help="Partidos de una jornada.")
    p.add_argument(
        "--standings", action="store_true", help="Clasificación de la temporada."
    )

    # player ------------------------------------------------------------
    p = subparsers.add_parser(
        "player",
        help="Información de un jugador.",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument("player_id", type=int, help="ID del jugador en SofaScore.")

    # categories --------------------------------------------------------
    p = subparsers.add_parser(
        "categories",
        help="Lista países/categorías disponibles (útil para --country).",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument("--filter", default=None, help="Filtra por nombre.")

    # upcoming ----------------------------------------------------------
    p = subparsers.add_parser(
        "upcoming",
        help="Partidos de una fecha: próximos y, opcionalmente, finalizados.",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument(
        "date",
        nargs="?",
        default="hoy",
        help="Fecha: YYYY-MM-DD, DD/MM/YYYY, hoy, ayer o mañana.",
    )
    p.add_argument(
        "--region",
        choices=["ambas", "europa", "sudamerica", "selecciones"],
        default="ambas",
        help="Región de las competiciones (por defecto todas).",
    )
    p.add_argument(
        "--competitions",
        choices=["principales", "todas"],
        default="principales",
        help="Principales (más rápido) o todas las competiciones.",
    )
    p.add_argument(
        "--timezone",
        default="local",
        help="Zona horaria para mostrar y filtrar la fecha (por defecto local).",
    )
    p.add_argument("--limit", type=int, default=120, help="Máximo de partidos.")
    p.add_argument(
        "--include-finished",
        action="store_true",
        help="Incluye partidos terminados con su marcador final.",
    )
    p.add_argument(
        "--no-live",
        action="store_true",
        help="Excluye los partidos en vivo (por defecto se incluyen).",
    )

    # form --------------------------------------------------------------
    p = subparsers.add_parser(
        "form",
        help="Analiza los últimos partidos de ambos equipos antes de un partido.",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument("event_id", type=int, help="ID del partido en SofaScore.")
    p.add_argument(
        "--last",
        choices=["5", "10", "15", "all"],
        default="10",
        help="Ventana de partidos por equipo: 5, 10, 15 o all (por defecto 10).",
    )
    p.add_argument(
        "--context",
        action="store_true",
        help="Incluye alineaciones, árbitro, clasificación y H2H.",
    )

    # simulate ----------------------------------------------------------
    p = subparsers.add_parser(
        "simulate",
        help="Simula miles de partidos con Monte Carlo y NumPy.",
    )
    _add_common(p)
    _add_output(p)
    p.add_argument("event_id", type=int, help="ID del partido en SofaScore.")
    p.add_argument(
        "--last",
        choices=["5", "10", "15", "all"],
        default="10",
        help="Ventana de partidos por equipo: 5, 10, 15 o all (por defecto 10).",
    )
    p.add_argument(
        "--iterations",
        type=int,
        default=simulation.DEFAULT_ITERATIONS,
        help=(
            "Número de escenarios simulados "
            f"(por defecto {simulation.DEFAULT_ITERATIONS}; "
            f"mínimo {simulation.MIN_ITERATIONS}, "
            f"máximo {simulation.MAX_ITERATIONS})."
        ),
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semilla para resultados reproducibles (por defecto 42).",
    )

    # gui ---------------------------------------------------------------
    p = subparsers.add_parser(
        "gui",
        help="Abre la interfaz gráfica de análisis de forma.",
    )
    _add_common(p)
    p.add_argument(
        "--timezone",
        default="local",
        help="Zona horaria inicial de la interfaz (por defecto local).",
    )
    p.add_argument(
        "--theme",
        choices=["auto", "claro", "oscuro"],
        default="auto",
        help=(
            "Tema inicial: auto (recuerda el último usado), claro u oscuro."
        ),
    )

    return parser


def _build_client(args: argparse.Namespace) -> SofaScoreClient:
    config = ClientConfig(
        timeout=max(1.0, float(args.timeout)),
        rate_limit=max(0.0, float(args.rate_limit)),
        use_cache=not bool(args.no_cache),
        cache_dir=args.cache_dir or default_cache_dir(),
        cache_ttl=max(0, int(args.cache_ttl)),
        proxy=args.proxy,
        force_ipv4=not bool(getattr(args, "no_ipv4", False)),
        debug=bool(args.debug),
        dump_raw=args.dump_raw,
    )
    if args.base_url:
        config.base_url = args.base_url
    return SofaScoreClient(config)


def _selected_sections(args: argparse.Namespace) -> List[str]:
    if getattr(args, "all", False):
        return [
            "statistics",
            "lineups",
            "incidents",
            "h2h",
            "graph",
            "best_players",
        ]
    sections = []
    for flag, name in (
        ("stats", "statistics"),
        ("lineups", "lineups"),
        ("incidents", "incidents"),
        ("h2h", "h2h"),
        ("graph", "graph"),
        ("best_players", "best_players"),
    ):
        if getattr(args, flag, False):
            sections.append(name)
    return sections


def _run_command(
    args: argparse.Namespace, extractor: SofaScoreExtractor
) -> Tuple[Any, Optional[str]]:
    command = args.command

    if command == "search":
        rows = extractor.search(
            args.query,
            type_filter=args.type,
            sport=args.sport,
            limit=args.limit,
        )
        return rows, None

    if command == "date":
        matches = extractor.get_matches_by_date(
            args.date,
            country=args.country,
            tournament=args.tournament,
            live=args.live,
            limit=args.limit,
            max_tournaments=args.max_tournaments,
            timezone_name=args.timezone,
        )
        return matches, None

    if command == "live":
        matches = extractor.get_live_matches(
            country=args.country,
            tournament=args.tournament,
            limit=args.limit,
        )
        return matches, None

    if command == "match":
        sections = _selected_sections(args)
        detail = extractor.get_match(
            args.event_id,
            sections=sections,
            period=args.period,
            lineup_stats=args.lineup_stats,
            include_raw=args.raw,
        )
        return detail, "match"

    if command == "team":
        team_info = extractor.get_team(args.team_id)
        last_n = args.last
        next_n = args.next
        if last_n is None and next_n is None:
            last_n = 10

        if last_n and next_n:
            return (
                {
                    "team": team_info,
                    "last_matches": extractor.get_team_matches(
                        args.team_id, "last", last_n
                    ),
                    "next_matches": extractor.get_team_matches(
                        args.team_id, "next", next_n
                    ),
                },
                None,
            )
        if next_n:
            return (
                {
                    "team": team_info,
                    "matches": extractor.get_team_matches(
                        args.team_id, "next", next_n
                    ),
                },
                "matches",
            )
        return (
            {
                "team": team_info,
                "matches": extractor.get_team_matches(
                    args.team_id, "last", last_n or 0
                ),
            },
            "matches",
        )

    if command == "tournament":
        tournament_id = args.tournament_id
        seasons = extractor.get_tournament_seasons(tournament_id)

        if args.seasons:
            return seasons, "seasons"

        season = seasons[0]
        if args.season is not None:
            season = next(
                (item for item in seasons if item.get("id") == args.season),
                {"id": args.season, "name": None, "year": None},
            )

        if args.standings:
            return (
                {
                    "tournament_id": tournament_id,
                    "season": season,
                    "standings": extractor.get_standings(
                        tournament_id, int(season["id"])
                    ),
                },
                "standings",
            )

        if args.round is not None:
            matches = extractor.get_season_matches(
                tournament_id,
                int(season["id"]),
                limit=0,
                round_number=args.round,
            )
            return (
                {
                    "tournament_id": tournament_id,
                    "season": season,
                    "round": args.round,
                    "matches": matches,
                },
                "matches",
            )

        last_n = args.last
        next_n = args.next
        if last_n is None and next_n is None:
            last_n = 10

        if last_n and next_n:
            return (
                {
                    "tournament_id": tournament_id,
                    "season": season,
                    "last_matches": extractor.get_season_matches(
                        tournament_id, int(season["id"]), "last", last_n
                    ),
                    "next_matches": extractor.get_season_matches(
                        tournament_id, int(season["id"]), "next", next_n
                    ),
                },
                None,
            )
        if next_n:
            return (
                {
                    "tournament_id": tournament_id,
                    "season": season,
                    "matches": extractor.get_season_matches(
                        tournament_id, int(season["id"]), "next", next_n
                    ),
                },
                "matches",
            )
        return (
            {
                "tournament_id": tournament_id,
                "season": season,
                "matches": extractor.get_season_matches(
                    tournament_id, int(season["id"]), "last", last_n or 0
                ),
            },
            "matches",
        )

    if command == "player":
        return extractor.get_player(args.player_id), None

    if command == "categories":
        categories = extractor.get_categories()
        if args.filter:
            wanted = normalize.normalize_text(args.filter)
            categories = [
                category
                for category in categories
                if wanted in normalize.normalize_text(category.get("name"))
                or wanted in normalize.normalize_text(category.get("slug"))
            ]
        return categories, None

    if command == "upcoming":
        progress = None
        if getattr(args, "verbose", False):
            progress = lambda done, total, message: print(  # noqa: E731
                f"[sofascore] {message}", file=sys.stderr
            )
        return (
            upcoming.list_upcoming(
                extractor,
                args.date,
                region=args.region,
                competitions=args.competitions,
                limit=args.limit,
                timezone_name=args.timezone,
                progress=progress,
                include_finished=bool(getattr(args, "include_finished", False)),
                include_live=not bool(getattr(args, "no_live", False)),
            ),
            None,
        )

    if command == "form":
        window = None if args.last == "all" else int(args.last)
        progress = None
        if getattr(args, "verbose", False):
            progress = lambda done, total, message: print(  # noqa: E731
                f"[sofascore] {message}", file=sys.stderr
            )
        analysis = form.analyze_match(
            extractor,
            args.event_id,
            window=window,
            progress=progress,
            include_lineups=bool(getattr(args, "context", False)),
            include_referee=bool(getattr(args, "context", False)),
            include_context=bool(getattr(args, "context", False)),
        )
        return analysis, "comparison"

    if command == "simulate":
        window = None if args.last == "all" else int(args.last)
        progress = None
        if getattr(args, "verbose", False):
            progress = lambda done, total, message: print(  # noqa: E731
                f"[sofascore] {message}", file=sys.stderr
            )
        analysis = form.analyze_match(
            extractor,
            args.event_id,
            window=window,
            progress=progress,
            include_lineups=True,
            include_referee=True,
            include_context=True,
        )
        summary = simulation.simulate_match(
            analysis,
            iterations=args.iterations,
            seed=args.seed,
        )
        if getattr(args, "verbose", False):
            meta = summary.get("meta") or {}
            print(
                f"[sofascore] {meta.get('iterations')} escenarios en "
                f"{meta.get('elapsed_seconds')} s",
                file=sys.stderr,
            )
        return summary, None

    raise SofaScoreError(f"Comando no soportado: {command}")


def _match_section_rows(
    detail: Dict[str, Any], section: str
) -> List[Dict[str, Any]]:
    if section == "statistics":
        return detail.get("statistics") or []
    if section == "incidents":
        return detail.get("incidents") or []
    if section == "lineups":
        return normalize.lineup_players(detail.get("lineups"))
    return []


def _export_match_csv(args: argparse.Namespace, detail: Dict[str, Any]) -> int:
    """Exporta un detalle de partido a CSV.

    - Una sola sección tabular (--stats, --incidents o --lineups): escribe
      solo esa tabla.
    - Varias secciones o --all: escribe el resumen y un archivo por sección.
    """
    sections = _selected_sections(args)
    tabular = [s for s in sections if s in ("statistics", "incidents", "lineups")]

    if len(tabular) == 1 and len(sections) == 1:
        rows = _match_section_rows(detail, tabular[0])
        return export.write_csv(rows, args.output)

    if args.output is None:
        raise SofaScoreError(
            "Para exportar varias secciones en CSV usa -o archivo.csv "
            "(se generarán varios archivos)."
        )

    output = Path(args.output)
    if output.suffix.lower() == ".csv":
        summary_path = output
        stem = output.with_suffix("")
    else:
        summary_path = output.with_suffix(".csv")
        stem = output

    written: List[Path] = []
    count = export.write_csv([detail.get("match") or {}], summary_path)
    written.append(summary_path)

    labels = {
        "statistics": "stats",
        "incidents": "incidents",
        "lineups": "lineups",
    }
    for section in sections:
        if section in labels:
            rows = _match_section_rows(detail, section)
            path = Path(f"{stem}_{labels[section]}.csv")
            export.write_csv(rows, path)
            written.append(path)
        elif section in ("h2h", "graph", "best_players"):
            payload = detail.get(section)
            if payload is not None:
                path = Path(f"{stem}_{section}.json")
                export.write_output(payload, "json", path)
                written.append(path)

    print(
        "OK: archivos generados:\n  " + "\n  ".join(str(path) for path in written),
        file=sys.stderr,
    )
    return count


def main(argv: Optional[Sequence[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        client = _build_client(args)
        extractor = SofaScoreExtractor(
            client,
            workers=max(1, int(args.workers)),
            verbose=bool(args.verbose),
        )

        if args.command == "gui":
            from .gui import run_gui

            return run_gui(
                client=client,
                workers=max(1, int(args.workers)),
                timezone_name=args.timezone,
                theme=getattr(args, "theme", "auto"),
            )

        data, table = _run_command(args, extractor)
        fmt = args.format or export.format_from_path(args.output)

        if args.command == "simulate" and fmt in ("csv", "jsonl"):
            rows = simulation.summary_rows(data)
            count = export.write_output(
                rows,
                fmt=fmt,
                output=args.output,
                pretty=not args.compact,
            )
            if args.output:
                print(
                    f"OK: {count} registro(s) guardados en {args.output}",
                    file=sys.stderr,
                )
            return 0

        if (
            fmt in ("csv", "jsonl")
            and isinstance(data, dict)
            and "last_matches" in data
            and "next_matches" in data
        ):
            raise SofaScoreError(
                "Para CSV/JSONL elige --last o --next por separado. "
                "Para obtener ambos en un solo archivo usa JSON."
            )

        if args.command == "match" and fmt == "csv":
            _export_match_csv(args, data)
            return 0

        count = export.write_output(
            data,
            fmt=fmt,
            output=args.output,
            pretty=not args.compact,
            table=table,
        )
        if args.output:
            print(
                f"OK: {count} registro(s) guardados en {args.output}",
                file=sys.stderr,
            )
        return 0

    except SofaScoreError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelado por el usuario.", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
