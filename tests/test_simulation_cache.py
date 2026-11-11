"""Pruebas de la caché persistente de simulaciones (sin red)."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from sofascore import simulation_cache

ANALYSIS = {
    "match": {"id": 123, "start_timestamp": 1000},
    "window": 10,
    "season": {"id": 1},
    "teams": {
        "home": {"matches": [{"event_id": 1}, {"event_id": 2}]},
        "away": {"matches": [{"event_id": 3}, {"event_id": 4}]},
    },
    "lineups": {
        "confirmed": True,
        "home": {
            "players": [
                {"id": 10, "substitute": False},
                {"id": 11, "substitute": False},
            ]
        },
        "away": {
            "players": [
                {"id": 20, "substitute": False},
                {"id": 21, "substitute": False},
            ]
        },
    },
    "referee": {
        "id": 99,
        "name": "Test",
        "cards_per_match": 5.0,
        "fouls_per_match": 24.0,
    },
}


class SimulationCacheTests(unittest.TestCase):
    def test_save_load_and_clear(self):
        summary = {"meta": {"iterations": 1000}, "actual": {"score": "2-3"}}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.assertIsNone(
                simulation_cache.load_simulation(
                    ANALYSIS, 1000, 42, directory=directory
                )
            )
            path = simulation_cache.save_simulation(
                summary, ANALYSIS, 1000, 42, directory=directory
            )
            self.assertIsNotNone(path)
            self.assertEqual(simulation_cache.cache_count(directory), 1)
            loaded = simulation_cache.load_simulation(
                ANALYSIS, 1000, 42, directory=directory
            )
            self.assertEqual(loaded, summary)
            self.assertEqual(
                simulation_cache.clear_simulation_cache(directory), 1
            )
            self.assertEqual(simulation_cache.cache_count(directory), 0)
            self.assertIsNone(
                simulation_cache.load_simulation(
                    ANALYSIS, 1000, 42, directory=directory
                )
            )

    def test_fingerprint_changes_with_context(self):
        first = simulation_cache.fingerprint(ANALYSIS, 1000, 42)
        other = dict(ANALYSIS)
        other["lineups"] = {
            "confirmed": False,
            "home": ANALYSIS["lineups"]["home"],
            "away": ANALYSIS["lineups"]["away"],
        }
        self.assertNotEqual(first, simulation_cache.fingerprint(other, 1000, 42))
        self.assertNotEqual(
            first, simulation_cache.fingerprint(ANALYSIS, 2000, 42)
        )
        self.assertNotEqual(
            first, simulation_cache.fingerprint(ANALYSIS, 1000, 7)
        )

    def test_expired_cache_is_ignored(self):
        summary = {"meta": {"iterations": 1000}}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            simulation_cache.save_simulation(
                summary, ANALYSIS, 1000, 42, directory=directory
            )
            self.assertIsNone(
                simulation_cache.load_simulation(
                    ANALYSIS,
                    1000,
                    42,
                    directory=directory,
                    max_age=-1,
                )
            )

    def test_live_actual_does_not_invalidate_model_cache(self):
        other = copy.deepcopy(ANALYSIS)
        other["actual"] = {
            "status": "live",
            "minute": 70,
            "totals": {"goals": 1},
        }
        self.assertEqual(
            simulation_cache.fingerprint(ANALYSIS, 1000, 42),
            simulation_cache.fingerprint(other, 1000, 42),
        )


if __name__ == "__main__":
    unittest.main()
