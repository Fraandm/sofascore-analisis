"""Pruebas del análisis de forma y de la selección de regiones (sin red)."""

from __future__ import annotations

import copy
import unittest

from sofascore import endpoints, form, normalize, regions, upcoming
from sofascore.exceptions import NotFoundError

STATS = {
    "statistics": [
        {
            "period": "ALL",
            "groups": [
                {
                    "groupName": "Match overview",
                    "statisticsItems": [
                        {"key": "cornerKicks", "homeValue": 6, "awayValue": 4},
                        {"key": "yellowCards", "homeValue": 2, "awayValue": 3},
                        {"key": "redCards", "homeValue": 1, "awayValue": 0},
                        {"key": "totalShotsOnGoal", "homeValue": 14, "awayValue": 9},
                        {"key": "shotsOnGoal", "homeValue": 5, "awayValue": 3},
                        {"key": "fouls", "homeValue": 11, "awayValue": 15},
                        {"key": "goalkeeperSaves", "homeValue": 2, "awayValue": 4},
                    ],
                }
            ],
        },
        {
            "period": "1ST",
            "groups": [
                {
                    "groupName": "Match overview",
                    "statisticsItems": [
                        {"key": "cornerKicks", "homeValue": 99, "awayValue": 99},
                    ],
                }
            ],
        },
    ]
}


def make_event(
    event_id: int,
    home_id: int,
    home_name: str,
    away_id: int,
    away_name: str,
    home_score: int,
    away_score: int,
    timestamp: int,
    status: str = "finished",
) -> dict:
    """Evento con la forma cruda que devuelve la API."""
    return {
        "id": event_id,
        "startTimestamp": timestamp,
        "status": {
            "type": status,
            "description": "Ended" if status == "finished" else "Not started",
            "code": 100 if status == "finished" else 0,
        },
        "season": {"id": 10, "name": "Test 26/27", "year": "26/27"},
        "tournament": {
            "id": 8,
            "name": "LaLiga",
            "slug": "laliga",
            "category": {
                "id": 32,
                "name": "Spain",
                "country": {"name": "Spain", "alpha2": "ES"},
            },
            "uniqueTournament": {
                "id": 8,
                "name": "LaLiga",
                "slug": "laliga",
                "category": {
                    "id": 32,
                    "name": "Spain",
                    "country": {"name": "Spain", "alpha2": "ES"},
                },
            },
        },
        "homeTeam": {"id": home_id, "name": home_name},
        "awayTeam": {"id": away_id, "name": away_name},
        "homeScore": {"current": home_score},
        "awayScore": {"current": away_score},
    }


RAW_HOME_EVENT = make_event(100, 1, "Home FC", 2, "Away FC", 2, 1, 1793000000)
RAW_AWAY_EVENT = make_event(101, 3, "Other FC", 1, "Home FC", 0, 1, 1792000000)
RAW_AWAY_TEAM_EVENT = make_event(
    102, 2, "Away FC", 4, "Fourth FC", 3, 0, 1791000000
)
RAW_TARGET_EVENT = make_event(
    999, 1, "Home FC", 2, "Away FC", 0, 0, 1794000000, status="notstarted"
)

HOME_EVENT = normalize.normalize_event(RAW_HOME_EVENT)
AWAY_EVENT = normalize.normalize_event(RAW_AWAY_EVENT)
AWAY_TEAM_EVENT = normalize.normalize_event(RAW_AWAY_TEAM_EVENT)
TARGET_EVENT = normalize.normalize_event(RAW_TARGET_EVENT)

STATS_101 = copy.deepcopy(STATS)
STATS_101["statistics"][0]["groups"][0]["statisticsItems"][0]["awayValue"] = 5


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_json(self, path, params=None, ttl=None):
        self.calls.append(path)
        if path in self.responses:
            return self.responses[path]
        raise NotFoundError(f"404: {path}")


class FakeExtractor:
    def __init__(self, responses):
        self.client = FakeClient(responses)
        self.workers = 1

    def get_match(self, event_id):
        return {"match": TARGET_EVENT}


class SeasonTests(unittest.TestCase):
    def test_season_start_year(self):
        self.assertEqual(form.season_start_year({"year": "26/27"}), 2026)
        self.assertEqual(form.season_start_year({"year": "2026"}), 2026)
        self.assertEqual(form.season_start_year({"year": "2025/2026"}), 2025)
        self.assertEqual(form.season_start_year({"year": "25/26"}), 2025)
        self.assertIsNone(form.season_start_year({}))
        self.assertIsNone(form.season_start_year(None))

    def test_parse_window(self):
        self.assertEqual(form.parse_window(5), 5)
        self.assertEqual(form.parse_window("15"), 15)
        self.assertIsNone(form.parse_window("all"))
        self.assertIsNone(form.parse_window(None))
        with self.assertRaises(Exception):
            form.parse_window("muchos")


class RegionTests(unittest.TestCase):
    def test_region_for_category(self):
        self.assertEqual(regions.region_for_category(32), "Europa")
        self.assertEqual(regions.region_for_category(1465), "Europa")
        self.assertEqual(regions.region_for_category(13), "Sudamérica")
        self.assertEqual(regions.region_for_category(1470), "Sudamérica")
        self.assertIsNone(regions.region_for_category(1468))
        self.assertIsNone(regions.region_for_category(None))

    def test_match_in_region(self):
        match = {"tournament": {"category_id": 13}}
        self.assertTrue(regions.match_in_region(match, "ambas"))
        self.assertTrue(regions.match_in_region(match, "sudamerica"))
        self.assertFalse(regions.match_in_region(match, "europa"))
        self.assertFalse(
            regions.match_in_region({"tournament": {"category_id": 1468}}, "ambas")
        )

    def test_national_tournament_region(self):
        self.assertEqual(regions.region_for_tournament(10783, 1465), "Selecciones")
        self.assertEqual(regions.region_for_tournament(851, 1468), "Selecciones")
        self.assertEqual(regions.normalize_region("selecciones"), "selecciones")
        self.assertEqual(regions.normalize_region("Selecciones absolutas"), "selecciones")
        match = {
            "tournament": {"id": 10783, "category_id": 1465},
            "home_team": {"id": 4700, "national": True},
            "away_team": {"id": 4717, "national": True},
        }
        self.assertTrue(regions.is_national_match(match))
        self.assertEqual(regions.region_for_match(match), "Selecciones")
        self.assertTrue(regions.match_in_region(match, "selecciones"))
        self.assertTrue(regions.match_in_region(match, "ambas"))
        self.assertFalse(regions.match_in_region(match, "europa"))

    def test_national_history_uses_previous_seasons(self):
        older = make_event(201, 4700, "Türkiye", 4717, "Belgium", 1, 0, 1730000000)
        recent = make_event(202, 4700, "Türkiye", 4717, "Belgium", 2, 2, 1740000000)
        for event, season_year in ((older, "2024"), (recent, "2025")):
            event["season"] = {"id": 1, "name": f"Test {season_year}", "year": season_year}
            event["tournament"] = {
                "id": 10783,
                "name": "UEFA Nations League",
                "uniqueTournament": {
                    "id": 10783,
                    "name": "UEFA Nations League",
                    "category": {"id": 1465, "name": "Europe"},
                },
                "category": {"id": 1465, "name": "Europe"},
            }
            event["homeTeam"]["national"] = True
            event["awayTeam"]["national"] = True
        extractor = FakeExtractor(
            {endpoints.team_events(4700, "last", 0): {"events": [older, recent]}}
        )
        rows = form.matches_for_team(
            extractor,
            4700,
            {"year": "26/27"},
            before_timestamp=1800000000,
            limit=10,
            national=True,
        )
        self.assertEqual([row["id"] for row in rows], [202, 201])


class MatchStatsTests(unittest.TestCase):
    def test_home_row(self):
        row = form.extract_team_match_stats(HOME_EVENT, STATS, team_id=1)
        self.assertEqual(row["team"], "Home FC")
        self.assertEqual(row["opponent"], "Away FC")
        self.assertTrue(row["home"])
        self.assertEqual(row["venue"], "casa")
        self.assertEqual(row["score"], "2-1")
        self.assertEqual(row["outcome"], "G")
        self.assertEqual(row["goals_for"], 2)
        self.assertEqual(row["goals_against"], 1)
        self.assertEqual(row["corners"], 6)
        self.assertEqual(row["yellow_cards"], 2)
        self.assertEqual(row["red_cards"], 1)
        self.assertEqual(row["cards"], 3)
        self.assertEqual(row["shots"], 14)
        self.assertEqual(row["shots_on_target"], 5)
        self.assertEqual(row["fouls"], 11)
        self.assertEqual(row["saves"], 2)
        self.assertTrue(row["stats_available"])

    def test_away_row(self):
        row = form.extract_team_match_stats(HOME_EVENT, STATS, team_id=2)
        self.assertEqual(row["team"], "Away FC")
        self.assertEqual(row["opponent"], "Home FC")
        self.assertFalse(row["home"])
        self.assertEqual(row["venue"], "fuera")
        self.assertEqual(row["outcome"], "P")
        self.assertEqual(row["corners"], 4)
        self.assertEqual(row["yellow_cards"], 3)
        self.assertEqual(row["red_cards"], 0)
        self.assertEqual(row["cards"], 3)
        self.assertEqual(row["shots"], 9)
        self.assertEqual(row["shots_on_target"], 3)
        self.assertEqual(row["fouls"], 15)
        self.assertEqual(row["saves"], 4)

    def test_missing_statistics(self):
        row = form.extract_team_match_stats(HOME_EVENT, None, team_id=1)
        self.assertFalse(row["stats_available"])
        self.assertIsNone(row["corners"])
        self.assertIsNone(row["cards"])
        self.assertEqual(row["goals_for"], 2)
        self.assertEqual(row["outcome"], "G")

    def test_cards_default_to_zero(self):
        payload = {
            "statistics": [
                {
                    "period": "ALL",
                    "groups": [
                        {
                            "groupName": "Match overview",
                            "statisticsItems": [
                                {"key": "cornerKicks", "homeValue": 3, "awayValue": 2}
                            ],
                        }
                    ],
                }
            ]
        }
        row = form.extract_team_match_stats(HOME_EVENT, payload, team_id=1)
        self.assertEqual(row["cards"], 0)
        self.assertEqual(row["yellow_cards"], 0)
        self.assertEqual(row["red_cards"], 0)
        self.assertEqual(row["corners"], 3)

    def test_only_all_period_is_used(self):
        row = form.extract_team_match_stats(HOME_EVENT, STATS, team_id=1)
        self.assertEqual(row["corners"], 6)

    def test_actual_block_for_finished_match(self):
        actual = form.build_actual_block(HOME_EVENT, STATS)
        self.assertEqual(actual["score"], "2-1")
        self.assertEqual(actual["home"]["goals_for"], 2)
        self.assertEqual(actual["away"]["goals_for"], 1)
        self.assertEqual(actual["totals"]["goals_for"], 3)
        self.assertEqual(actual["totals"]["corners"], 10)
        self.assertEqual(actual["totals"]["cards"], 6)
        self.assertEqual(actual["totals"]["shots"], 23)
        self.assertEqual(actual["totals"]["shots_on_target"], 8)
        self.assertEqual(actual["totals"]["fouls"], 26)
        self.assertEqual(actual["totals"]["saves"], 6)
        self.assertTrue(actual["stats_available"])

    def test_advanced_stats_and_opponent_values(self):
        payload = {
            "statistics": [
                {
                    "period": "ALL",
                    "groups": [
                        {
                            "groupName": "Match overview",
                            "statisticsItems": [
                                {"key": "expectedGoals", "homeValue": 1.4, "awayValue": 0.8},
                                {
                                    "key": "expectedGoalsOnTarget",
                                    "homeValue": 1.0,
                                    "awayValue": 0.5,
                                },
                                {"key": "bigChanceCreated", "homeValue": 3, "awayValue": 1},
                                {"key": "totalShotsInsideBox", "homeValue": 8, "awayValue": 3},
                                {"key": "totalShotsOnGoal", "homeValue": 14, "awayValue": 7},
                                {"key": "shotsOnGoal", "homeValue": 5, "awayValue": 2},
                                {"key": "cornerKicks", "homeValue": 6, "awayValue": 4},
                                {"key": "fouls", "homeValue": 10, "awayValue": 12},
                                {"key": "yellowCards", "homeValue": 2, "awayValue": 3},
                                {"key": "redCards", "homeValue": 0, "awayValue": 1},
                                {"key": "goalkeeperSaves", "homeValue": 2, "awayValue": 5},
                            ],
                        }
                    ],
                }
            ]
        }
        row = form.extract_team_match_stats(HOME_EVENT, payload, team_id=1)
        self.assertEqual(row["xg_for"], 1.4)
        self.assertEqual(row["xg_against"], 0.8)
        self.assertEqual(row["xg_on_target_for"], 1.0)
        self.assertEqual(row["xg_on_target_against"], 0.5)
        self.assertEqual(row["big_chances_for"], 3)
        self.assertEqual(row["big_chances_against"], 1)
        self.assertEqual(row["shots_inside_box"], 8)
        self.assertEqual(row["shots_inside_box_against"], 3)
        self.assertEqual(row["shots_against"], 7)
        self.assertEqual(row["shots_on_target_against"], 2)
        self.assertEqual(row["corners_against"], 4)
        self.assertEqual(row["fouls_against"], 12)
        self.assertEqual(row["cards_against"], 4)
        self.assertEqual(row["saves_against"], 5)


class SummaryTests(unittest.TestCase):
    def test_summarize_ignores_missing_values(self):
        rows = [
            form.extract_team_match_stats(HOME_EVENT, STATS, team_id=1),
            form.extract_team_match_stats(AWAY_EVENT, None, team_id=1),
        ]
        summary = form.summarize_rows(rows)
        self.assertEqual(summary["matches"], 2)
        self.assertEqual(summary["matches_with_stats"], 1)
        self.assertEqual(summary["totals"]["corners"], 6)
        self.assertEqual(summary["averages"]["corners"], 6)
        self.assertEqual(summary["totals"]["goals_for"], 3)
        self.assertEqual(summary["averages"]["goals_for"], 1.5)
        self.assertEqual(summary["averages"]["saves"], 2)

    def test_recent_form(self):
        rows = [
            form.extract_team_match_stats(HOME_EVENT, STATS, team_id=1),
            form.extract_team_match_stats(AWAY_EVENT, STATS, team_id=1),
        ]
        self.assertEqual(form.recent_form(rows), "G G")


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        responses = {
            endpoints.team_events(1, "last", 0): {
                "events": [RAW_HOME_EVENT, RAW_AWAY_EVENT]
            },
            endpoints.team_events(2, "last", 0): {
                "events": [RAW_HOME_EVENT, RAW_AWAY_TEAM_EVENT]
            },
            endpoints.event_statistics(100): STATS,
            endpoints.event_statistics(101): STATS_101,
            endpoints.event_statistics(102): STATS,
        }
        self.extractor = FakeExtractor(responses)

    def test_analyze_match(self):
        analysis = form.analyze_match(
            self.extractor, TARGET_EVENT, window=5
        )
        self.assertEqual(analysis["window"], 5)
        self.assertEqual(analysis["teams"]["home"]["sample_size"], 2)
        self.assertEqual(analysis["teams"]["away"]["sample_size"], 2)
        self.assertEqual(
            analysis["teams"]["home"]["team"]["name"], "Home FC"
        )
        self.assertEqual(analysis["teams"]["home"]["form"], "G G")
        self.assertEqual(analysis["teams"]["home"]["totals"]["corners"], 11)
        self.assertEqual(analysis["teams"]["home"]["averages"]["corners"], 5.5)

        comparison = {row["stat"]: row for row in analysis["comparison"]}
        self.assertAlmostEqual(comparison["corners"]["home"], 5.5)
        self.assertAlmostEqual(comparison["corners"]["away"], 5.0)
        self.assertAlmostEqual(comparison["corners"]["difference"], 0.5)
        self.assertEqual(comparison["goals_for"]["label"], "Goles a favor")
        self.assertIsNotNone(analysis["generated_at"])

    def test_analyze_all_matches(self):
        analysis = form.analyze_match(self.extractor, TARGET_EVENT, window="all")
        self.assertEqual(analysis["window"], "all")
        self.assertEqual(analysis["teams"]["home"]["sample_size"], 2)

    def test_analyze_requests_statistics_once_per_event(self):
        form.analyze_match(self.extractor, TARGET_EVENT, window=5)
        stats_calls = [
            path for path in self.extractor.client.calls if "/statistics" in path
        ]
        self.assertEqual(len(stats_calls), len(set(stats_calls)))

    def test_warns_when_not_enough_matches(self):
        analysis = form.analyze_match(self.extractor, TARGET_EVENT, window=10)
        self.assertTrue(
            any("solo hay" in warning for warning in analysis["warnings"])
        )


class UpcomingTests(unittest.TestCase):
    def test_is_upcoming(self):
        match = {"status_type": "notstarted", "start_timestamp": 1000}
        self.assertTrue(upcoming.is_upcoming(match, now=900))
        self.assertFalse(upcoming.is_upcoming(match, now=2000))
        self.assertFalse(
            upcoming.is_upcoming(
                {"status_type": "finished", "start_timestamp": 1000}, now=900
            )
        )
        self.assertFalse(
            upcoming.is_upcoming(
                {"status_type": "notstarted", "start_timestamp": None}, now=900
            )
        )

    def test_include_match_excludes_live_and_includes_finished(self):
        finished = {"status_type": "finished", "start_timestamp": 1000}
        upcoming_match = {"status_type": "notstarted", "start_timestamp": 1000}
        live = {"status_type": "inprogress", "start_timestamp": 1000}
        self.assertTrue(
            upcoming.include_match(finished, include_finished=True, now=900)
        )
        self.assertFalse(
            upcoming.include_match(finished, include_finished=False, now=900)
        )
        self.assertTrue(
            upcoming.include_match(upcoming_match, include_finished=True, now=900)
        )
        self.assertTrue(upcoming.include_match(live, include_live=True, now=900))
        self.assertFalse(upcoming.include_match(live, include_live=False, now=900))

    def test_live_minute_from_status_time(self):
        match = {
            "status_type": "inprogress",
            "start_timestamp": 1000,
            "status_time": {"initial": 2700, "timestamp": 4000},
        }
        self.assertEqual(form.match_minute(match, now=4600), 55.0)
        self.assertEqual(
            form.match_minute({"status_type": "finished"}), 90.0
        )
        self.assertEqual(
            form.match_minute({"status_type": "notstarted"}), 0.0
        )


if __name__ == "__main__":
    unittest.main()
