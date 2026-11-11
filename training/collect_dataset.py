"""Recolecta un dataset de partidos finalizados para entrenar la red neuronal.

Uso:
    python training/collect_dataset.py

Fuente: SofaScore (API interna). Se guardan las filas de estadísticas de
ambos equipos y el contexto básico del partido. El resultado se escribe en
``training/data/dataset.jsonl``.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sofascore import endpoints, form  # noqa: E402
from sofascore.client import ClientConfig, SofaScoreClient  # noqa: E402
from sofascore.extractor import SofaScoreExtractor  # noqa: E402

OUTPUT = ROOT / "training" / "data" / "dataset.jsonl"
STATS_TTL = 7 * 24 * 3600

# (unique_tournament_id, season_id, etiqueta)
COMPETITIONS = (
    (17, 76986, "Premier League 25/26"),
    (17, 96668, "Premier League 26/27"),
    (8, 77559, "LaLiga 25/26"),
    (8, 97268, "LaLiga 26/27"),
    (23, 76457, "Serie A 25/26"),
    (23, 95836, "Serie A 26/27"),
    (35, 77333, "Bundesliga 25/26"),
    (35, 97464, "Bundesliga 26/27"),
    (34, 77356, "Ligue 1 25/26"),
    (34, 96127, "Ligue 1 26/27"),
    (7, 76953, "Champions League 25/26"),
    (7, 96518, "Champions League 26/27"),
)

TARGET_KEYS = ("shots", "shots_on_target", "corners", "cards", "fouls", "saves")


def collect_matches(extractor: SofaScoreExtractor) -> List[Dict[str, Any]]:
    matches: Dict[int, Dict[str, Any]] = {}
    for tournament_id, season_id, label in COMPETITIONS:
        try:
            season_matches = extractor.get_season_matches(
                tournament_id, season_id, "last", 1000
            )
        except Exception as exc:  # noqa: BLE001 - se informa y se continúa
            print(f"[aviso] {label}: {exc}", file=sys.stderr)
            continue
        count = 0
        for match in season_matches:
            if match.get("status_type") != "finished":
                continue
            event_id = match.get("id")
            if event_id is None or event_id in matches:
                continue
            match["_competition"] = label
            matches[event_id] = match
            count += 1
        print(f"{label}: {count} partidos", flush=True)
    return list(matches.values())


def fetch_statistics(
    client: SofaScoreClient, event_id: int
) -> Dict[str, Any] | None:
    try:
        return client.get_json(
            endpoints.event_statistics(event_id), ttl=STATS_TTL
        )
    except Exception:  # noqa: BLE001 - se marca como sin estadísticas
        return None


def build_record(
    match: Dict[str, Any], payload: Dict[str, Any] | None
) -> Dict[str, Any] | None:
    home_id = (match.get("home_team") or {}).get("id")
    away_id = (match.get("away_team") or {}).get("id")
    home_row = form.extract_team_match_stats(
        match, payload, home_id, side="home"
    )
    away_row = form.extract_team_match_stats(
        match, payload, away_id, side="away"
    )
    if not (home_row.get("stats_available") and away_row.get("stats_available")):
        return None
    if any(home_row.get(key) is None for key in TARGET_KEYS):
        return None
    if any(away_row.get(key) is None for key in TARGET_KEYS):
        return None
    return {
        "id": match.get("id"),
        "timestamp": match.get("start_timestamp"),
        "date": match.get("start_time"),
        "competition": match.get("_competition"),
        "tournament_id": (match.get("tournament") or {}).get("id"),
        "season_id": (match.get("season") or {}).get("id"),
        "home_team_id": home_id,
        "away_team_id": away_id,
        "home_team": (match.get("home_team") or {}).get("name"),
        "away_team": (match.get("away_team") or {}).get("name"),
        "home_score": match.get("home_score"),
        "away_score": match.get("away_score"),
        "home": home_row,
        "away": away_row,
    }


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    config = ClientConfig(
        timeout=30,
        rate_limit=0.12,
        cache_ttl=STATS_TTL,
        use_cache=True,
    )
    client = SofaScoreClient(config)
    extractor = SofaScoreExtractor(client, workers=8)
    started = time.perf_counter()
    matches = collect_matches(extractor)
    print(f"Partidos únicos: {len(matches)}", flush=True)
    print("Descargando estadísticas…", flush=True)

    records: List[Dict[str, Any]] = []
    total = len(matches)
    with OUTPUT.open("w", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(fetch_statistics, client, int(match["id"])): match
                for match in matches
                if match.get("id") is not None
            }
            done = 0
            for future in as_completed(futures):
                match = futures[future]
                payload = future.result()
                record = build_record(match, payload)
                if record is not None:
                    records.append(record)
                    handle.write(
                        json.dumps(record, ensure_ascii=False, separators=(",", ":"))
                        + "\n"
                    )
                    if len(records) % 100 == 0:
                        handle.flush()
                done += 1
                if done % 100 == 0 or done == total:
                    elapsed = time.perf_counter() - started
                    print(
                        f"{done}/{total} consultados · {len(records)} válidos · "
                        f"{elapsed:.0f}s",
                        flush=True,
                    )

    elapsed = time.perf_counter() - started
    print(
        f"Dataset: {len(records)} partidos en {OUTPUT} "
        f"({elapsed:.0f}s)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
