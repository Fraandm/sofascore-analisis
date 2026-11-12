"""Recolecta partidos oficiales de selecciones absolutas para la red neuronal.

Uso:
    python training/collect_national.py

Fuente: SofaScore (API interna). Solo se guardan competiciones oficiales de
selecciones masculinas absolutas. Los amistosos internacionales (851 y 852)
quedan excluidos de forma explícita, tanto del dataset como del entrenamiento.

El resultado se escribe en ``training/data/dataset_national.jsonl`` y se
deduplica contra ``dataset.jsonl`` y ``dataset_extra.jsonl``.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "training"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TRAINING) not in sys.path:
    sys.path.insert(0, str(TRAINING))

import collect_dataset as base  # noqa: E402
from sofascore import form  # noqa: E402
from sofascore.client import ClientConfig, SofaScoreClient  # noqa: E402
from sofascore.extractor import SofaScoreExtractor  # noqa: E402

OUTPUT = TRAINING / "data" / "dataset_national.jsonl"
BASE_DATA = (
    TRAINING / "data" / "dataset.jsonl",
    TRAINING / "data" / "dataset_extra.jsonl",
)
STATS_TTL = 7 * 24 * 3600
MIN_SEASON_YEAR = 2010
MAX_SEASONS = 12

# Competiciones oficiales de selecciones masculinas absolutas.
# (unique_tournament_id, etiqueta)
OFFICIAL_TOURNAMENTS: Tuple[Tuple[int, str], ...] = (
    (10783, "UEFA Nations League"),
    (133, "Copa América"),
    (16, "Copa Mundial de la FIFA"),
    (11, "Eliminatorias Mundial · UEFA"),
    (295, "Eliminatorias Mundial · CONMEBOL"),
    (13, "Eliminatorias Mundial · CAF"),
    (14, "Eliminatorias Mundial · CONCACAF"),
    (308, "Eliminatorias Mundial · AFC"),
    (309, "Eliminatorias Mundial · OFC"),
    (1, "Eurocopa"),
    (27, "Clasificación Eurocopa"),
    (28, "Clasificación Copa Asiática"),
    (1848, "Clasificación Copa Africana"),
    (140, "Copa Oro CONCACAF"),
    (270, "Copa Africana de Naciones"),
    (246, "Copa Asiática"),
    (14100, "CONCACAF Nations League"),
    (22716, "OFC Men's Nations Cup"),
    (18654, "Finalissima"),
    (10618, "Repesca intercontinental al Mundial"),
)

# Amistosos: nunca se recolectan ni se usan para entrenar.
FRIENDLY_TOURNAMENT_IDS = frozenset({851, 852})


def _existing_ids() -> set:
    ids = set()
    for path in (*BASE_DATA, OUTPUT):
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    ids.add(int(json.loads(line)["id"]))
                except (ValueError, KeyError, TypeError):
                    continue
    return ids


def _season_year(season: Dict[str, Any]) -> int:
    year = form.season_start_year(season)
    return int(year or 0)


def collect_matches(
    extractor: SofaScoreExtractor, existing: set
) -> List[Dict[str, Any]]:
    matches: Dict[int, Dict[str, Any]] = {}
    for tournament_id, tournament_name in OFFICIAL_TOURNAMENTS:
        if tournament_id in FRIENDLY_TOURNAMENT_IDS:
            continue
        try:
            seasons = extractor.get_tournament_seasons(tournament_id)
        except Exception as exc:  # noqa: BLE001 - se informa y se continúa
            print(f"[aviso] {tournament_name}: {exc}", file=sys.stderr)
            continue
        selected = [
            season
            for season in seasons
            if _season_year(season) >= MIN_SEASON_YEAR
        ][:MAX_SEASONS]
        if not selected:
            print(f"{tournament_name}: sin temporadas recientes", flush=True)
            continue
        for season in selected:
            season_id = season.get("id")
            if season_id is None:
                continue
            season_name = season.get("name") or str(season.get("year") or season_id)
            try:
                season_matches = extractor.get_season_matches(
                    tournament_id, int(season_id), "last", 1000
                )
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[aviso] {tournament_name} · {season_name}: {exc}",
                    file=sys.stderr,
                )
                continue
            count = 0
            for match in season_matches:
                if match.get("status_type") != "finished":
                    continue
                event_id = match.get("id")
                if event_id is None or int(event_id) in existing:
                    continue
                if int(event_id) in matches:
                    continue
                tournament = match.get("tournament") or {}
                if int(tournament.get("id") or 0) in FRIENDLY_TOURNAMENT_IDS:
                    continue
                match["_competition"] = f"{tournament_name} · {season_name}"
                matches[int(event_id)] = match
                count += 1
            print(f"{tournament_name} · {season_name}: {count} partidos", flush=True)
    return list(matches.values())


def main() -> int:
    existing = _existing_ids()
    print(f"Partidos ya existentes: {len(existing)}", flush=True)

    config = ClientConfig(
        timeout=30,
        rate_limit=0.08,
        cache_ttl=STATS_TTL,
        use_cache=True,
    )
    client = SofaScoreClient(config)
    extractor = SofaScoreExtractor(client, workers=8)
    started = time.perf_counter()
    matches = [
        match
        for match in collect_matches(extractor, existing)
        if int(match.get("id") or 0) not in existing
    ]
    print(f"Partidos nuevos de selecciones: {len(matches)}", flush=True)
    print("Descargando estadísticas…", flush=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    records = 0
    total = len(matches)
    with OUTPUT.open("a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(base.fetch_statistics, client, int(match["id"])): match
                for match in matches
                if match.get("id") is not None
            }
            done = 0
            for future in as_completed(futures):
                match = futures[future]
                record = base.build_record(match, future.result())
                if record is not None:
                    record["is_national"] = True
                    record["tournament_name"] = (
                        match.get("tournament") or {}
                    ).get("name")
                    records += 1
                    handle.write(
                        json.dumps(record, ensure_ascii=False, separators=(",", ":"))
                        + "\n"
                    )
                    if records % 100 == 0:
                        handle.flush()
                done += 1
                if done % 100 == 0 or done == total:
                    elapsed = time.perf_counter() - started
                    print(
                        f"{done}/{total} consultados · {records} válidos · "
                        f"{elapsed:.0f}s",
                        flush=True,
                    )
    elapsed = time.perf_counter() - started
    print(
        f"Dataset de selecciones: {records} nuevos partidos añadidos a {OUTPUT} "
        f"({elapsed:.0f}s)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
