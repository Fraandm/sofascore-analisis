"""Pruebas de historial, previas y API local."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import urllib.request
from pathlib import Path

from sofascore import preview
from sofascore.api_server import LocalAPIServer
from sofascore.storage import HistoryStore


def match_payload(match_id=1, status="finished", home_score=2, away_score=1):
    return {
        "id": match_id,
        "status_type": status,
        "start_timestamp": 1794200000,
        "start_time": "2026-11-10T20:00:00+00:00",
        "region": "Europa",
        "home_team": {"id": 1, "name": "Real Madrid"},
        "away_team": {"id": 2, "name": "Barcelona"},
        "home_score": home_score,
        "away_score": away_score,
        "tournament": {"id": 8, "name": "LaLiga"},
    }


def summary_payload(match_id=1):
    return {
        "meta": {
            "match_id": match_id,
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "tournament": "LaLiga",
            "start_time": "2026-11-10T20:00:00+00:00",
            "window": 10,
            "iterations": 1000,
            "seed": 42,
        },
        "model": {},
        "teams": {
            "home": {"expected": {"goals_for": 2.1}},
            "away": {"expected": {"goals_for": 0.9}},
        },
        "totals": {"mean": {"goals": 3.0, "corners": 10.2}},
        "probabilities": {
            "winner": {"home": 0.61, "draw": 0.22, "away": 0.17},
            "btts": 0.55,
            "over_under": {"goals": {"2.5": {"over": 0.6}}},
        },
    }


def analysis_payload():
    return {
        "match": match_payload(),
        "window": 10,
        "use_neural": False,
        "teams": {
            "home": {
                "team": {"name": "Real Madrid"},
                "sample_size": 8,
                "stats_sample_size": 8,
                "form": "WWWDW",
            },
            "away": {
                "team": {"name": "Barcelona"},
                "sample_size": 8,
                "stats_sample_size": 8,
                "form": "WDLWW",
            },
        },
        "comparison": [
            {
                "label": "Goles",
                "home": 2.1,
                "away": 0.9,
                "difference": 1.2,
            }
        ],
        "lineups": {"status": "sin datos", "home": {}, "away": {}},
        "referee": {"name": "Test Referee", "cards_per_match": 4.2},
        "actual": {"score": "2-1", "status": "finished"},
    }


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = HistoryStore(self.tmp / "history.db")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_matches_search_and_prediction_accuracy(self):
        match = match_payload()
        self.store.save_matches([match], "2026-11-10")
        rows = self.store.list_matches(query="madrid")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["home_name"], "Real Madrid")
        self.assertTrue(self.store.list_matches(status="finished"))
        self.assertFalse(self.store.list_matches(status="inprogress"))

        prediction_id = self.store.save_prediction(
            summary_payload(), analysis_payload()
        )
        self.assertIsNotNone(prediction_id)
        latest = self.store.latest_predictions([1])
        self.assertIn(1, latest)
        self.assertEqual(self.store.count_predictions(), 1)
        metrics = self.store.accuracy()
        self.assertEqual(metrics["total"], 1)
        self.assertEqual(metrics["correct"], 1)
        self.assertAlmostEqual(metrics["accuracy"], 1.0)
        self.assertGreaterEqual(metrics["brier"], 0.0)
        self.assertGreaterEqual(metrics["goal_mae"], 0.0)
        self.assertEqual(metrics["by_tournament"][0]["tournament"], "LaLiga")

    def test_finished_prediction_updates_accuracy(self):
        self.store.save_matches(
            [match_payload(status="inprogress", home_score=1, away_score=0)],
            "2026-11-10",
        )
        analysis = analysis_payload()
        analysis["actual"] = {"score": None, "status": "live"}
        self.store.save_prediction(summary_payload(), analysis)
        self.assertEqual(self.store.accuracy()["total"], 0)
        self.store.update_match_result(
            match_payload(status="finished", home_score=2, away_score=1)
        )
        self.assertEqual(self.store.accuracy()["total"], 1)

    def test_analysis_and_clear(self):
        self.store.save_analysis(analysis_payload())
        self.store.clear()
        self.assertEqual(self.store.list_predictions(), [])
        self.assertEqual(self.store.list_matches(), [])


class PreviewTests(unittest.TestCase):
    def test_markdown_and_html(self):
        markdown = preview.render_markdown(analysis_payload(), summary_payload())
        self.assertIn("# Real Madrid vs Barcelona", markdown)
        self.assertIn("Probabilidades simuladas", markdown)
        self.assertIn("61,0 %", markdown)
        self.assertIn("Test Referee", markdown)
        html = preview.render_html(analysis_payload(), summary_payload())
        self.assertIn("<html", html)
        self.assertIn("<table>", html)
        self.assertIn("Real Madrid", html)
        self.assertIn("61,0 %", html)


class LocalAPIServerTests(unittest.TestCase):
    def test_endpoints(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            store = HistoryStore(tmp / "history.db")
            store.save_matches([match_payload()], "2026-11-10")
            store.save_prediction(summary_payload(), analysis_payload())
            server = LocalAPIServer(store, port=0)
            try:
                base = server.start()
                with urllib.request.urlopen(base + "/api/health", timeout=5) as response:
                    health = json.loads(response.read().decode("utf-8"))
                self.assertEqual(health["status"], "ok")
                self.assertEqual(health["predictions"], 1)
                with urllib.request.urlopen(
                    base + "/api/matches?query=real&limit=10", timeout=5
                ) as response:
                    matches = json.loads(response.read().decode("utf-8"))["matches"]
                self.assertEqual(len(matches), 1)
                with urllib.request.urlopen(
                    base + "/api/accuracy", timeout=5
                ) as response:
                    accuracy = json.loads(response.read().decode("utf-8"))
                self.assertEqual(accuracy["total"], 1)
            finally:
                server.stop()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

