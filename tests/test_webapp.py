"""Pruebas de la interfaz web local y su API, sin abrir el navegador."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from sofascore import webapp
from sofascore.storage import HistoryStore


def sample_match(match_id=1, status="finished", home=2, away=1):
    return {
        "id": match_id,
        "status_type": status,
        "status": "Ended" if status == "finished" else "Not started",
        "start_timestamp": 1794332700,
        "tournament": {
            "id": 8,
            "name": "LaLiga",
            "category_id": 32,
            "category": "Spain",
        },
        "home_team": {"id": 2829, "name": "Real Madrid"},
        "away_team": {"id": 2817, "name": "Barcelona"},
        "home_score": home,
        "away_score": away,
        "region": "Europa",
    }


def sample_analysis(match_id=1):
    match = sample_match(match_id, status="finished")
    return {
        "match": match,
        "window": 10,
        "season": {"id": 1, "name": "Test"},
        "teams": {
            "home": {
                "team": match["home_team"],
                "sample_size": 8,
                "stats_sample_size": 8,
                "form": "WWWDW",
                "averages": {"goals_for": 2.1, "goals_against": 0.9},
                "matches": [],
            },
            "away": {
                "team": match["away_team"],
                "sample_size": 8,
                "stats_sample_size": 8,
                "form": "WDLWW",
                "averages": {"goals_for": 1.4, "goals_against": 1.2},
                "matches": [],
            },
        },
        "comparison": [
            {
                "stat": "goals_for",
                "label": "Goles a favor",
                "home": 2.1,
                "away": 1.4,
                "difference": 0.7,
            }
        ],
        "lineups": None,
        "referee": {"name": "Test Referee"},
        "generated_at": "2026-11-10T20:00:00+00:00",
        "warnings": [],
    }


def sample_summary(match_id=1):
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
            "home": {
                "name": "Real Madrid",
                "expected": {"goals_for": 2.1, "goals_against": 1.0},
            },
            "away": {
                "name": "Barcelona",
                "expected": {"goals_for": 1.0, "goals_against": 2.1},
            },
        },
        "totals": {"mean": {"goals": 3.1}, "percentiles": {}},
        "probabilities": {
            "winner": {"home": 0.6, "draw": 0.22, "away": 0.18},
            "btts": 0.55,
            "over_under": {"goals": {"2.5": {"over": 0.6, "under": 0.4}}},
        },
        "scorelines": [{"score": "2-1", "home": 2, "away": 1, "probability": 0.12}],
        "score_matrix": {"labels": ["0", "1"], "probabilities": [[0.1, 0.2], [0.3, 0.4]]},
        "histograms": {},
        "actual": {"status": "finished", "score": "2-1", "totals": {}},
    }


class WebHelperTests(unittest.TestCase):
    def test_grouping_and_merging(self):
        top = sample_match(1)
        other = sample_match(2)
        other["tournament"] = {"id": 679, "name": "Europa League", "category_id": 4}
        south = sample_match(3)
        south["tournament"] = {"id": 325, "name": "Brasileirao", "category_id": 13}
        south["region"] = "Sudamérica"

        self.assertEqual(webapp.top_league_index(top), 1)
        self.assertEqual(webapp.match_section(top), "top")
        self.assertEqual(webapp.match_section(other), "other")
        self.assertEqual(webapp.match_section(south), "south")

        merged = webapp._merge_matches([top, other], [sample_match(1, home=4)])
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["home_score"], 4)

    def test_image_type_detection(self):
        self.assertEqual(
            webapp.WebService._guess_image_type(b"\x89PNG\r\n"), "image/png"
        )
        self.assertEqual(
            webapp.WebService._guess_image_type(b"\xff\xd8\xff"), "image/jpeg"
        )
        self.assertEqual(
            webapp.WebService._guess_image_type(b"RIFF0000WEBP"), "image/webp"
        )


class WebServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = HistoryStore(self.tmp / "history.db")
        self.prefs_patch = patch(
            "sofascore.webapp.load_preferences", return_value={}
        )
        self.save_patch = patch("sofascore.webapp.save_preferences")
        self.prefs_patch.start()
        self.save_patch.start()
        self.service = webapp.WebService(
            client=object(), extractor=object(), store=self.store
        )

    def tearDown(self):
        self.prefs_patch.stop()
        self.save_patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_preferences_and_favorites(self):
        self.service.preferences = {"dark": True}
        legacy = self.service.preferences_snapshot()
        self.assertEqual(legacy["theme"], "dark")
        self.assertTrue(legacy["dark"])
        self.service.preferences = {}
        self.assertEqual(self.service.preferences_snapshot()["theme"], "light")

        result = self.service.toggle_favorite(2829, "Real Madrid", True)
        self.assertTrue(result["favorite"])
        self.assertEqual(result["favorites"]["2829"], "Real Madrid")
        result = self.service.toggle_favorite(2829, "Real Madrid", False)
        self.assertFalse(result["favorite"])
        self.assertNotIn("2829", result["favorites"])

        prefs = self.service.update_preferences(
            {
                "theme": "forest",
                "timezone": "UTC",
                "region": "europa",
                "competitions": "todas",
            }
        )
        self.assertEqual(prefs["theme"], "forest")
        self.assertTrue(prefs["dark"])
        self.assertEqual(prefs["timezone"], "UTC")
        self.assertEqual(prefs["region"], "europa")
        self.assertEqual(prefs["competitions"], "todas")

        prefs = self.service.update_preferences({"theme": "sunset"})
        self.assertEqual(prefs["theme"], "sunset")
        self.assertFalse(prefs["dark"])

        prefs = self.service.update_preferences({"dark": True})
        self.assertEqual(prefs["theme"], "dark")
        self.assertTrue(prefs["dark"])

    def test_list_day_and_history(self):
        fake_matches = [sample_match(1), sample_match(2, status="notstarted", home=None, away=None)]
        with patch("sofascore.upcoming.list_upcoming", return_value=fake_matches):
            first = self.service.list_day(
                day="2026-11-10", stage="all", refresh=True
            )
            second = self.service.list_day(day="2026-11-10", stage="all")
        self.assertEqual(first["count"], 2)
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(self.service.history_matches()[0]["home_name"], "Real Madrid")
        self.assertEqual(len(self.service.history_predictions()), 0)

    def test_live_updates(self):
        class FakeExtractor:
            def get_live_matches(self):
                return [sample_match(1, status="inprogress", home=1, away=0)]

            def get_match(self, match_id):
                return {"match": sample_match(match_id, status="finished", home=2, away=1)}

        self.service.extractor = FakeExtractor()
        result = self.service.live_updates([1, 2])
        self.assertEqual(result["count"], 2)
        ids = {match["id"] for match in result["matches"]}
        self.assertEqual(ids, {1, 2})

    def test_analysis_and_simulation_with_fakes(self):
        analysis = sample_analysis()
        with patch("sofascore.webapp.form.analyze_match", return_value=analysis):
            first = self.service.analyze(1, 10)
            second = self.service.analyze(1, 10)
        self.assertIs(first, second)

        with patch("sofascore.webapp.simulation_cache.load_simulation", return_value=None), patch(
            "sofascore.webapp.simulation.simulate_match", return_value=sample_summary()
        ), patch(
            "sofascore.webapp.simulation_cache.save_simulation"
        ), patch(
            "sofascore.webapp.form.analyze_match", return_value=analysis
        ):
            result = self.service.simulate(1, 10, iterations=1000, seed=42)
        self.assertFalse(result["cached"])
        self.assertEqual(result["summary"]["meta"]["match_id"], 1)
        self.assertEqual(self.service.history_predictions()[0]["home_name"], "Real Madrid")

    def test_preview_and_exports(self):
        analysis = sample_analysis()
        self.store.save_prediction(sample_summary(), analysis)
        with patch("sofascore.webapp.form.analyze_match", return_value=analysis):
            preview = self.service.preview_payload(1, 10)
        self.assertIn("Real Madrid", preview["markdown"])
        self.assertIn("<html", preview["html"])
        self.assertIn("Probabilidades simuladas", preview["markdown"])

        body, filename, content_type = self.service.export_analysis(
            1, 10, "json"
        )
        self.assertTrue(body.startswith(b"{"))
        self.assertTrue(filename.endswith(".json"))
        self.assertIn("application/json", content_type)

        body, filename, content_type = self.service.export_history("predictions")
        self.assertTrue(filename.endswith(".csv"))
        self.assertIn("text/csv", content_type)

    def test_jobs(self):
        def work(progress):
            progress(1, 2, "mitad")
            progress(2, 2, "final")
            return {"ok": True}

        job = self.service.jobs.submit("test", work)
        for _ in range(50):
            current = self.service.jobs.get(job["id"])
            if current["status"] == "done":
                break
            import time

            time.sleep(0.02)
        self.assertEqual(current["status"], "done")
        self.assertEqual(current["result"], {"ok": True})


class WebHTTPTests(unittest.TestCase):
    def test_static_and_api(self):
        tmp = Path(tempfile.mkdtemp())
        store = HistoryStore(tmp / "history.db")
        with patch("sofascore.webapp.load_preferences", return_value={}), patch(
            "sofascore.webapp.save_preferences"
        ):
            service = webapp.WebService(
                client=object(), extractor=object(), store=store
            )
            server, base = webapp.start_server(service, port=0)
            try:
                with urllib.request.urlopen(base + "/", timeout=5) as response:
                    html = response.read().decode("utf-8")
                self.assertIn("SofaScore", html)
                self.assertIn("view-matches", html)

                with urllib.request.urlopen(base + "/api/health", timeout=5) as response:
                    health = json.loads(response.read().decode("utf-8"))
                self.assertEqual(health["status"], "ok")
                self.assertEqual(health["version"], webapp.__version__)

                with urllib.request.urlopen(base + "/api/bootstrap", timeout=5) as response:
                    bootstrap = json.loads(response.read().decode("utf-8"))
                self.assertIn("preferences", bootstrap)
                self.assertIn("model", bootstrap)

                request = urllib.request.Request(
                    base + "/api/preferences",
                    data=json.dumps({"dark": True}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["preferences"]["dark"])

                request = urllib.request.Request(
                    base + "/api/favorites",
                    data=json.dumps(
                        {"team_id": 2829, "name": "Real Madrid", "favorite": True}
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["favorite"])

                with urllib.request.urlopen(base + "/api/model", timeout=5) as response:
                    model = json.loads(response.read().decode("utf-8"))
                self.assertIn("targets", model)

                request = urllib.request.Request(
                    base + "/api/history", method="DELETE"
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertTrue(payload["cleared"])
            finally:
                server.shutdown()
                server.server_close()
                shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
