"""Amplía el dataset con más temporadas europeas y competiciones sudamericanas.

Uso:
    python training/collect_extra.py

Escribe ``training/data/dataset_extra.jsonl`` y evita duplicar partidos que ya
estén en ``dataset.jsonl``. Se apoya en las funciones de collect_dataset.py.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "training"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TRAINING) not in sys.path:
    sys.path.insert(0, str(TRAINING))

import collect_dataset as base  # noqa: E402
from sofascore.client import ClientConfig, SofaScoreClient  # noqa: E402
from sofascore.extractor import SofaScoreExtractor  # noqa: E402

BASE_DATA = TRAINING / "data" / "dataset.jsonl"
OUTPUT = TRAINING / "data" / "dataset_extra.jsonl"
STATS_TTL = 7 * 24 * 3600

COMPETITIONS = (
    # Europa: dos temporadas adicionales
    (17, 61627, "Premier League 24/25"),
    (17, 52186, "Premier League 23/24"),
    (8, 61643, "LaLiga 24/25"),
    (8, 52376, "LaLiga 23/24"),
    (23, 63515, "Serie A 24/25"),
    (23, 52760, "Serie A 23/24"),
    (35, 63516, "Bundesliga 24/25"),
    (35, 52608, "Bundesliga 23/24"),
    (34, 61736, "Ligue 1 24/25"),
    (34, 52571, "Ligue 1 23/24"),
    (7, 61644, "Champions League 24/25"),
    (7, 52162, "Champions League 23/24"),
    # Sudamérica: ligas profesionales 2025
    (325, 72034, "Brasileirão Série A 2025"),
    (155, 70268, "Primera División Argentina 2025 Apertura"),
    (155, 77826, "Primera División Argentina 2025 Clausura"),
    (11539, 70681, "Primera A Colombia 2025"),
    (240, 71184, "LigaPro Ecuador 2025"),
    (406, 70962, "Liga 1 Perú 2025"),
    (11653, 71131, "Primera División Chile 2025"),
    (30743, 85915, "Primera División Uruguay 2025"),
    (11541, 69831, "Primera División Paraguay 2025"),
    (16736, 73577, "División Profesional Bolivia 2025"),
    (231, 71012, "Primera División Venezuela 2025"),
    # Sudamérica: ligas profesionales 2024
    (325, 58766, "Brasileirão Série A 2024"),
    (155, 57478, "Primera División Argentina 2024"),
    (11539, 57374, "Primera A Colombia 2024"),
    (240, 58043, "LigaPro Ecuador 2024"),
    (406, 57741, "Liga 1 Perú 2024"),
    (11653, 57883, "Primera División Chile 2024"),
    (11541, 63769, "Primera División Paraguay 2024"),
    (16736, 58156, "División Profesional Bolivia 2024"),
    (231, 57694, "Primera División Venezuela 2024"),
    # Copas sudamericanas
    (16940, 74657, "Copa Libertadores 2025"),
    (16940, 60372, "Copa Libertadores 2024"),
    (480, 70070, "Copa Sudamericana 2025"),
    (480, 57297, "Copa Sudamericana 2024"),
)


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


def main() -> int:
    existing = set()
    if BASE_DATA.exists():
        with BASE_DATA.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    existing.add(int(json.loads(line)["id"]))
                except (ValueError, KeyError, TypeError):
                    continue
    print(f"Partidos ya existentes: {len(existing)}", flush=True)

    config = ClientConfig(
        timeout=30,
        rate_limit=0.10,
        cache_ttl=STATS_TTL,
        use_cache=True,
    )
    client = SofaScoreClient(config)
    extractor = SofaScoreExtractor(client, workers=8)
    started = time.perf_counter()
    matches = [
        match for match in collect_matches(extractor)
        if int(match.get("id") or 0) not in existing
    ]
    print(f"Partidos nuevos: {len(matches)}", flush=True)
    print("Descargando estadísticas…", flush=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    records = 0
    total = len(matches)
    with OUTPUT.open("w", encoding="utf-8") as handle:
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
    print(
        f"Dataset extra: {records} partidos en {OUTPUT} "
        f"({time.perf_counter() - started:.0f}s)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
