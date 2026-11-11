"""Pruebas de normalización, fechas y exportación (sin red)."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta, timezone
from pathlib import Path

from sofascore import export, normalize
from sofascore.extractor import SofaScoreExtractor, parse_day, resolve_timezone

EVENT = {
    "id": 12345,
    "slug": "home-away",
    "customId": "AbCdEf",
    "startTimestamp": 1793814300,
    "status": {"code": 100, "description": "Ended", "type": "finished"},
    "tournament": {
        "id": 99,
        "name": "Test League",
        "slug": "test-league",
        "priority": 10,
        "category": {
            "id": 32,
            "name": "Spain",
            "country": {"name": "Spain", "alpha2": "ES"},
        },
        "uniqueTournament": {
            "id": 5,
            "name": "Test League",
            "slug": "test-league",
            "category": {
                "id": 32,
                "name": "Spain",
                "country": {"name": "Spain", "alpha2": "ES"},
            },
        },
    },
    "season": {"id": 100, "name": "26/27", "year": "26/27"},
    "roundInfo": {"round": 4},
    "homeTeam": {
        "id": 1,
        "name": "Home FC",
        "shortName": "Home",
        "nameCode": "HOM",
        "slug": "home-fc",
        "country": {"name": "Spain"},
    },
    "awayTeam": {
        "id": 2,
        "name": "Away FC",
        "shortName": "Away",
        "nameCode": "AWY",
        "slug": "away-fc",
        "country": {"name": "Spain"},
    },
    "homeScore": {"current": 2, "display": 2},
    "awayScore": {"current": 1, "display": 1},
    "winnerCode": 1,
    "venue": {
        "name": "Test Stadium",
        "city": {"name": "Madrid"},
        "country": {"name": "Spain"},
        "capacity": 50000,
    },
    "hasXg": True,
    "hasEventPlayerStatistics": True,
}

STATISTICS = {
    "statistics": [
        {
            "period": "ALL",
            "groups": [
                {
                    "groupName": "Shots",
                    "statisticsItems": [
                        {
                            "name": "Total shots",
                            "home": "13",
                            "away": "9",
                            "homeValue": 13,
                            "awayValue": 9,
                            "compareCode": 1,
                            "statisticsType": "positive",
                            "key": "totalShots",
                        },
                        {
                            "name": "Ball possession",
                            "home": "52%",
                            "away": "48%",
                            "compareCode": 1,
                            "statisticsType": "positive",
                            "key": "ballPossession",
                        },
                    ],
                }
            ],
        },
        {
            "period": "1ST",
            "groups": [
                {
                    "groupName": "Shots",
                    "statisticsItems": [
                        {"name": "Total shots", "home": "7", "away": "4"}
                    ],
                }
            ],
        },
    ]
}

INCIDENTS = {
    "incidents": [
        {
            "incidentType": "goal",
            "incidentClass": "regular",
            "time": 23,
            "isHome": True,
            "player": {"name": "Player One"},
            "assist1": {"name": "Player Two"},
            "homeScore": 1,
            "awayScore": 0,
        },
        {
            "incidentType": "card",
            "incidentClass": "yellow",
            "time": 40,
            "isHome": False,
            "player": {"name": "Player Three"},
        },
        {
            "incidentType": "substitution",
            "time": 60,
            "isHome": True,
            "playerIn": {"name": "Sub In"},
            "playerOut": {"name": "Sub Out"},
        },
        {
            "incidentType": "period",
            "text": "FT",
            "time": 90,
            "homeScore": 2,
            "awayScore": 1,
        },
    ]
}

LINEUPS = {
    "confirmed": True,
    "home": {
        "formation": "4-3-3",
        "players": [
            {
                "player": {
                    "id": 10,
                    "name": "Keeper",
                    "shortName": "Keeper",
                    "jerseyNumber": "1",
                    "position": "G",
                    "country": {"name": "Spain"},
                },
                "shirtNumber": 1,
                "position": "G",
                "substitute": False,
                "avgRating": "7.1",
                "seasonRatingBreakdown": {
                    "shot": {
                        "expectedGoals": 0,
                        "totalShotsPerGame": 0.1,
                        "shotsOnTargetPerGame": 0,
                    },
                    "defending": {"defensiveContributionsPerGame": 1.2},
                    "goalkeeping": {
                        "goalsPrevented": 1.5,
                        "savesPerGame": 3.2,
                    },
                },
                "statistics": {"rating": "8.2", "saves": 4},
            }
        ],
        "missingPlayers": [
            {
                "player": {"id": 11, "name": "Injured", "position": "M"},
                "description": "Hamstring Injury",
                "type": "missing",
                "expectedEndDate": "2026-12-10T00:00:00+00:00",
            }
        ],
    },
    "away": {
        "formation": "4-4-2",
        "players": [
            {
                "player": {
                    "id": 20,
                    "name": "Striker",
                    "shortName": "Striker",
                    "jerseyNumber": "9",
                    "position": "F",
                },
                "shirtNumber": 9,
                "position": "F",
                "substitute": True,
                "statistics": {"rating": 6.9},
            }
        ],
        "missingPlayers": [],
    },
}

SEARCH = {
    "results": [
        {
            "type": "team",
            "entity": {
                "id": 1,
                "name": "Real Madrid",
                "slug": "real-madrid",
                "sport": {"slug": "football"},
                "country": {"name": "Spain"},
                "userCount": 100,
            },
        },
        {
            "type": "team",
            "entity": {
                "id": 2,
                "name": "Real Madrid Baloncesto",
                "slug": "real-madrid-baloncesto",
                "sport": {"slug": "basketball"},
                "country": {"name": "Spain"},
            },
        },
        {
            "type": "player",
            "entity": {
                "id": 3,
                "name": "Kylian Mbappé",
                "slug": "kylian-mbappe",
                "country": {"name": "France"},
                "team": {"id": 1, "name": "Real Madrid", "sport": {"slug": "football"}},
                "position": "F",
                "jerseyNumber": "10",
            },
        },
        {
            "type": "uniqueTournament",
            "entity": {
                "id": 5,
                "name": "Test League",
                "slug": "test-league",
                "category": {
                    "name": "Spain",
                    "id": 32,
                    "sport": {"slug": "football"},
                },
            },
        },
    ]
}

STANDINGS = {
    "standings": [
        {
            "name": "Group A",
            "rows": [
                {
                    "team": {"id": 1, "name": "Home FC", "slug": "home-fc"},
                    "position": 1,
                    "matches": 4,
                    "wins": 3,
                    "draws": 1,
                    "losses": 0,
                    "scoresFor": 10,
                    "scoresAgainst": 3,
                    "points": 10,
                    "promotion": {"text": "Playoffs"},
                    "form": "WWWD",
                }
            ],
        }
    ]
}


class NormalizeTests(unittest.TestCase):
    def test_normalize_text(self):
        self.assertEqual(normalize.normalize_text("España"), "espana")
        self.assertEqual(normalize.normalize_text("Türkiye"), "turkiye")
        self.assertEqual(normalize.normalize_text("  Real  Madrid! "), "real madrid")

    def test_score_value(self):
        self.assertEqual(normalize.score_value({"current": 2, "display": 2}), 2)
        self.assertEqual(normalize.score_value("3"), 3)
        self.assertIsNone(normalize.score_value(None))

    def test_normalize_event(self):
        match = normalize.normalize_event(EVENT)
        self.assertEqual(match["id"], 12345)
        self.assertEqual(match["home_score"], 2)
        self.assertEqual(match["away_score"], 1)
        self.assertEqual(match["winner"], "home")
        self.assertEqual(match["status_type"], "finished")
        self.assertEqual(match["tournament"]["id"], 5)
        self.assertEqual(match["tournament"]["country"], "Spain")
        self.assertEqual(match["home_team"]["name"], "Home FC")
        self.assertEqual(match["venue"]["city"], "Madrid")
        self.assertEqual(match["round"], 4)
        self.assertTrue(match["start_time"].startswith("2026-11-04T"))

    def test_normalize_statistics(self):
        rows = normalize.normalize_statistics(STATISTICS)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["period"], "ALL")
        self.assertEqual(rows[0]["group"], "Shots")
        self.assertEqual(rows[0]["home_value"], 13)
        self.assertEqual(rows[1]["home_value"], 52)

        first_period = normalize.normalize_statistics(STATISTICS, period="1ST")
        self.assertEqual(len(first_period), 1)
        self.assertEqual(first_period[0]["home"], "7")

    def test_normalize_incidents(self):
        rows = normalize.normalize_incidents(INCIDENTS)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["type"], "goal")
        self.assertEqual(rows[0]["side"], "home")
        self.assertEqual(rows[0]["assist"], "Player Two")
        self.assertEqual(rows[1]["side"], "away")
        self.assertEqual(rows[2]["player_in"], "Sub In")
        self.assertEqual(rows[3]["text"], "FT")

    def test_normalize_lineups(self):
        lineups = normalize.normalize_lineups(LINEUPS)
        self.assertTrue(lineups["confirmed"])
        self.assertEqual(lineups["home"]["formation"], "4-3-3")
        self.assertEqual(lineups["home"]["players"][0]["rating"], 8.2)
        self.assertEqual(lineups["home"]["players"][0]["avg_rating"], 7.1)
        self.assertAlmostEqual(
            lineups["home"]["players"][0]["season"]["saves_per_game"], 3.2
        )
        self.assertEqual(
            lineups["home"]["missing_players"][0]["name"], "Injured"
        )
        self.assertEqual(normalize.lineup_status(lineups), "confirmada")
        self.assertEqual(len(normalize.lineup_starters(lineups, "home")), 1)
        self.assertNotIn("statistics", lineups["home"]["players"][0])

        full = normalize.normalize_lineups(LINEUPS, include_stats=True)
        self.assertEqual(full["home"]["players"][0]["statistics"]["saves"], 4)

        players = normalize.lineup_players(lineups)
        self.assertEqual(len(players), 2)
        self.assertEqual(players[1]["side"], "away")

    def test_search_filters(self):
        football = normalize.normalize_search_results(SEARCH, sport="football")
        self.assertEqual([row["name"] for row in football], [
            "Real Madrid",
            "Kylian Mbappé",
            "Test League",
        ])

        players = normalize.normalize_search_results(
            SEARCH, type_filter="player", sport="football"
        )
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["team"], "Real Madrid")

        tournaments = normalize.normalize_search_results(
            SEARCH, type_filter="tournament", sport="football"
        )
        self.assertEqual(tournaments[0]["unique_tournament_id"], 5)

        limited = normalize.normalize_search_results(SEARCH, limit=1)
        self.assertEqual(len(limited), 1)

    def test_normalize_standings(self):
        rows = normalize.normalize_standings(STANDINGS)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["goal_difference"], 7)
        self.assertEqual(rows[0]["group"], "Group A")
        self.assertEqual(rows[0]["promotion"], "Playoffs")


class ExtractorHelpersTests(unittest.TestCase):
    def test_parse_day(self):
        self.assertEqual(parse_day("2026-11-04"), "2026-11-04")
        self.assertEqual(parse_day("04/11/2026"), "2026-11-04")
        self.assertEqual(parse_day("hoy"), date.today().isoformat())
        self.assertEqual(
            parse_day("ayer"), (date.today() - timedelta(days=1)).isoformat()
        )
        with self.assertRaises(Exception):
            parse_day("no-es-una-fecha")

    def test_resolve_timezone(self):
        self.assertEqual(resolve_timezone("UTC"), timezone.utc)
        offset = resolve_timezone("+02:00")
        self.assertEqual(offset.utcoffset(None), timedelta(hours=2))
        self.assertIsNotNone(resolve_timezone("local"))

    def test_api_days(self):
        utc = timezone.utc
        self.assertEqual(
            SofaScoreExtractor._api_days("2026-11-04", utc), ["2026-11-04"]
        )
        plus14 = timezone(timedelta(hours=14))
        self.assertEqual(
            SofaScoreExtractor._api_days("2026-11-04", plus14),
            ["2026-11-03", "2026-11-04"],
        )

    def test_filter_by_local_date(self):
        tz = timezone(timedelta(hours=1))
        match = normalize.normalize_event(EVENT)
        kept = SofaScoreExtractor._filter_by_local_date(
            [match], "2026-11-04", tz
        )
        self.assertEqual(len(kept), 1)
        self.assertIn("start_time_local", kept[0])
        dropped = SofaScoreExtractor._filter_by_local_date(
            [match], "2026-11-03", tz
        )
        self.assertEqual(dropped, [])


class ExportTests(unittest.TestCase):
    def test_flatten_record(self):
        flat = export.flatten_record(
            {"id": 1, "team": {"name": "Home"}, "tags": ["a"], "_raw": {"x": 1}}
        )
        self.assertEqual(flat["id"], 1)
        self.assertEqual(flat["team.name"], "Home")
        self.assertEqual(flat["tags"], '["a"]')
        self.assertNotIn("_raw", flat)

    def test_extract_rows(self):
        match = normalize.normalize_event(EVENT)
        self.assertEqual(export.extract_rows({"match": match, "statistics": []}), [match])
        self.assertEqual(
            export.extract_rows({"matches": [match], "team": {}}), [match]
        )
        self.assertEqual(export.extract_rows([match]), [match])

    def test_write_csv(self):
        match = normalize.normalize_event(EVENT)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "matches.csv"
            count = export.write_csv([match], path)
            self.assertEqual(count, 1)
            content = path.read_text(encoding="utf-8-sig")
            self.assertIn("home_team.name", content)
            self.assertIn("Home FC", content)
            self.assertIn("tournament.country", content)

    def test_write_json_and_jsonl(self):
        match = normalize.normalize_event(EVENT)
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "match.json"
            export.write_output(match, "json", json_path)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["id"], 12345)

            jsonl_path = Path(tmp) / "matches.jsonl"
            count = export.write_output([match, match], "jsonl", jsonl_path)
            self.assertEqual(count, 2)
            lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)

    def test_format_from_path(self):
        self.assertEqual(export.format_from_path("x.csv"), "csv")
        self.assertEqual(export.format_from_path("x.jsonl"), "jsonl")
        self.assertEqual(export.format_from_path("x.txt"), "json")
        self.assertEqual(export.format_from_path(None), "json")


class FakeRefereeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_json(self, path, params=None, ttl=None):
        self.calls.append(path)
        if path not in self.responses:
            raise AssertionError(f"Petición inesperada: {path}")
        return self.responses[path]


def referee_match_payload(fouls_home, fouls_away, yellow_home, yellow_away, red_home=0, red_away=0):
    return {
        "statistics": [
            {
                "period": "ALL",
                "groups": [
                    {
                        "groupName": "Match overview",
                        "statisticsItems": [
                            {"key": "fouls", "homeValue": fouls_home, "awayValue": fouls_away},
                            {"key": "yellowCards", "homeValue": yellow_home, "awayValue": yellow_away},
                            {"key": "redCards", "homeValue": red_home, "awayValue": red_away},
                        ],
                    }
                ],
            }
        ]
    }


class RefereeProfileTests(unittest.TestCase):
    def test_profile_uses_recent_same_season_matches(self):
        responses = {
            "/referee/99": {
                "referee": {
                    "id": 99,
                    "name": "Test Referee",
                    "games": 10,
                    "yellowCards": 50,
                    "redCards": 2,
                    "yellowRedCards": 1,
                    "country": {"name": "Spain"},
                }
            },
            "/referee/99/statistics": {
                "statistics": [
                    {
                        "uniqueTournament": {"id": 8, "name": "Liga"},
                        "appearances": 5,
                        "yellowCards": 25,
                        "redCards": 1,
                        "yellowRedCards": 0,
                        "penalty": 2,
                    }
                ]
            },
            "/referee/99/events/last/0": {
                "events": [
                    {
                        "id": 1001,
                        "startTimestamp": 1000,
                        "status": {"type": "finished"},
                        "season": {"id": 1},
                        "tournament": {"uniqueTournament": {"id": 8}},
                    },
                    {
                        "id": 1002,
                        "startTimestamp": 2000,
                        "status": {"type": "finished"},
                        "season": {"id": 1},
                        "tournament": {"uniqueTournament": {"id": 8}},
                    },
                    {
                        "id": 1003,
                        "startTimestamp": 4000,
                        "status": {"type": "finished"},
                        "season": {"id": 1},
                        "tournament": {"uniqueTournament": {"id": 8}},
                    },
                    {
                        "id": 1004,
                        "startTimestamp": 1500,
                        "status": {"type": "finished"},
                        "season": {"id": 2},
                        "tournament": {"uniqueTournament": {"id": 8}},
                    },
                    {
                        "id": 1005,
                        "startTimestamp": 500,
                        "status": {"type": "notstarted"},
                        "season": {"id": 1},
                        "tournament": {"uniqueTournament": {"id": 8}},
                    },
                ]
            },
            "/event/1001/statistics": referee_match_payload(10, 11, 2, 1),
            "/event/1002/statistics": referee_match_payload(13, 14, 3, 2, 1, 0),
        }
        client = FakeRefereeClient(responses)
        extractor = SofaScoreExtractor(client, workers=2)
        profile = extractor.get_referee_profile(
            99,
            tournament_id=8,
            season_id=1,
            before_timestamp=3000,
            max_matches=5,
        )
        self.assertEqual(profile["name"], "Test Referee")
        self.assertEqual(profile["sample"]["matches"], 2)
        self.assertEqual(set(profile["sample"]["event_ids"]), {1001, 1002})
        self.assertAlmostEqual(profile["cards_per_match"], 4.5)
        self.assertAlmostEqual(profile["fouls_per_match"], 24.0)
        self.assertEqual(profile["competition"]["cards_per_match"], 5.2)
        self.assertIn("muestra reciente", profile["source"])


if __name__ == "__main__":
    unittest.main()
