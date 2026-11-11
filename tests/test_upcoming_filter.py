"""Pruebas de la carga selectiva de competiciones (sin red)."""

from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from sofascore import upcoming
from sofascore.extractor import SofaScoreExtractor
from tests.test_core import EVENT


class FakeClient:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def get_json(self, path, params=None, ttl=None):
        self.paths.append(path)
        if path.startswith("/sport/football/scheduled-tournaments/"):
            return {
                "scheduled": [
                    self._entry(17, "Premier League", 1),
                    self._entry(679, "Europa League", 1465),
                    self._entry(325, "Brasileirão", 13),
                ],
                "hasNextPage": False,
            }
        for tournament_id in (17, 679, 325):
            marker = f"/unique-tournament/{tournament_id}/scheduled-events/"
            if marker in path:
                return {"events": [self._event(tournament_id)]}
        return {}

    @staticmethod
    def _entry(tournament_id: int, name: str, category_id: int):
        category = {"id": category_id, "name": name, "country": {"name": name}}
        unique = {
            "id": tournament_id,
            "name": name,
            "slug": name.lower().replace(" ", "-"),
            "category": category,
        }
        return {
            "tournament": {
                "uniqueTournament": unique,
                "category": category,
                "priority": 90,
            }
        }

    @staticmethod
    def _event(tournament_id: int):
        event = copy.deepcopy(EVENT)
        event["id"] = 1700 + tournament_id
        event["startTimestamp"] = int(
            datetime(2026, 11, 8, 23, 30, tzinfo=timezone.utc).timestamp()
        )
        event["status"] = {
            "code": 100,
            "description": "Ended",
            "type": "finished",
        }
        unique = event["tournament"]["uniqueTournament"]
        unique["id"] = tournament_id
        unique["category"]["id"] = 1 if tournament_id == 17 else 1465
        return event


class TournamentFilterTests(unittest.TestCase):
    def _matches(self, filter_func=None):
        client = FakeClient()
        extractor = SofaScoreExtractor(client, workers=2)
        matches = upcoming.list_upcoming(
            extractor,
            "2026-11-08",
            region="ambas",
            competitions="todas",
            limit=50,
            timezone_name="UTC",
            include_finished=True,
            include_live=True,
            tournament_filter=filter_func,
        )
        return matches, client.paths

    def test_without_filter_loads_all(self):
        matches, paths = self._matches()
        self.assertEqual(len(matches), 3)
        fetched = {
            path.split("/")[2]
            for path in paths
            if path.startswith("/unique-tournament/")
        }
        self.assertEqual(fetched, {"17", "679", "325"})

    def test_filter_loads_only_requested_tournament(self):
        matches, paths = self._matches(
            lambda entry: entry.get("unique_tournament_id") == 17
        )
        self.assertEqual([match["id"] for match in matches], [1717])
        fetched = [
            path
            for path in paths
            if path.startswith("/unique-tournament/")
        ]
        self.assertEqual(fetched, ["/unique-tournament/17/scheduled-events/2026-11-08"])

    def test_filter_is_applied_to_remaining_tournaments(self):
        matches, _ = self._matches(
            lambda entry: entry.get("unique_tournament_id") != 17
        )
        self.assertEqual(
            {match["tournament"]["id"] for match in matches}, {679, 325}
        )


if __name__ == "__main__":
    unittest.main()

