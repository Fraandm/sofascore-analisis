"""Recolecta resúmenes de alineaciones históricas (calidad de plantilla).

Uso:
    python training/collect_lineups.py

Salida: ``training/data/lineups.jsonl``.
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

from sofascore import endpoints, normalize  # noqa: E402
from sofascore.client import ClientConfig, SofaScoreClient  # noqa: E402

DATA_PATHS = (
    ROOT / "training" / "data" / "dataset.jsonl",
    ROOT / "training" / "data" / "dataset_extra.jsonl",
)
OUTPUT = ROOT / "training" / "data" / "lineups.jsonl"
LINEUPS_TTL = 7 * 24 * 3600


def side_summary(lineups: Dict[str, Any] | None, side: str) -> Dict[str, Any]:
    starters = normalize.lineup_starters(lineups, side)
    market = []
    ratings = []
    for player in starters:
        value = player.get("market_value")
        if isinstance(value, (int, float)) and value > 0:
            market.append(float(value))
        rating = player.get("avg_rating")
        if isinstance(rating, (int, float)):
            ratings.append(float(rating))
    missing = ((lineups or {}).get(side) or {}).get("missing_players") or []
    missing_values = [
        float(item["market_value"])
        for item in missing
        if isinstance(item.get("market_value"), (int, float))
    ]
    minimum = max(5, int(len(starters) * 0.6))
    return {
        "starters": len(starters),
        "market_value": sum(market) if len(market) >= minimum else None,
        "avg_rating": (
            sum(ratings) / len(ratings)
            if len(ratings) >= minimum
            else None
        ),
        "missing_count": len(missing),
        "missing_market_value": sum(missing_values) if missing_values else 0.0,
    }


def fetch_lineups(client: SofaScoreClient, event_id: int) -> Dict[str, Any]:
    try:
        payload = client.get_json(
            endpoints.event_lineups(event_id), ttl=LINEUPS_TTL
        )
    except Exception:  # noqa: BLE001 - se marca como no disponible
        return {
            "id": event_id,
            "available": False,
            "home": side_summary(None, "home"),
            "away": side_summary(None, "away"),
        }
    lineups = normalize.normalize_lineups(payload)
    return {
        "id": event_id,
        "available": bool(lineups),
        "confirmed": bool((lineups or {}).get("confirmed")),
        "home": side_summary(lineups, "home"),
        "away": side_summary(lineups, "away"),
    }


def main() -> int:
    event_ids = []
    seen = set()
    for path in DATA_PATHS:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    event_id = int(json.loads(line)["id"])
                except (ValueError, KeyError, TypeError):
                    continue
                if event_id not in seen:
                    seen.add(event_id)
                    event_ids.append(event_id)
    existing = set()
    if OUTPUT.exists():
        with OUTPUT.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    existing.add(int(json.loads(line)["id"]))
                except (ValueError, KeyError, TypeError):
                    continue
    pending = [event_id for event_id in event_ids if event_id not in existing]
    print(
        f"Partidos: {len(event_ids)} · ya recogidos: {len(existing)} · "
        f"pendientes: {len(pending)}",
        flush=True,
    )

    client = SofaScoreClient(
        ClientConfig(timeout=30, rate_limit=0.10, cache_ttl=LINEUPS_TTL)
    )
    started = time.perf_counter()
    with OUTPUT.open("a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(fetch_lineups, client, event_id): event_id
                for event_id in pending
            }
            done = 0
            for future in as_completed(futures):
                record = future.result()
                handle.write(
                    json.dumps(record, ensure_ascii=False, separators=(",", ":"))
                    + "\n"
                )
                done += 1
                if done % 100 == 0 or done == len(pending):
                    handle.flush()
                    print(
                        f"{done}/{len(pending)} · "
                        f"{time.perf_counter() - started:.0f}s",
                        flush=True,
                    )
    print(f"Guardado en {OUTPUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
