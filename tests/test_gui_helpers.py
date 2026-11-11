"""Pruebas de la agrupación visual de partidos (sin abrir Tk)."""

from __future__ import annotations

import unittest

from sofascore.gui import group_matches, match_section, top_league_index


def game(mid, tournament_id, name, region="Europa", status="notstarted", ts=0):
    return {
        "id": mid,
        "status_type": status,
        "start_timestamp": ts,
        "region": region,
        "tournament": {"id": tournament_id, "name": name},
    }


class TopLeagueTests(unittest.TestCase):
    def test_top_five_by_id_and_order(self):
        expected = {
            17: 0,
            8: 1,
            23: 2,
            35: 3,
            34: 4,
        }
        for tournament_id, index in expected.items():
            self.assertEqual(
                top_league_index(game(1, tournament_id, "Liga")), index
            )

    def test_top_five_by_name_fallback(self):
        self.assertEqual(top_league_index(game(1, 0, "LaLiga")), 1)
        self.assertEqual(top_league_index(game(1, 0, "Ligue 1")), 4)
        self.assertIsNone(top_league_index(game(1, 0, "Serie A Women")))

    def test_sections(self):
        self.assertEqual(match_section(game(1, 17, "Premier League")), "top")
        self.assertEqual(match_section(game(1, 679, "Europa League")), "other")
        self.assertEqual(
            match_section(game(1, 325, "Brasileirão", "Sudamérica")), "south"
        )


class GroupMatchesTests(unittest.TestCase):
    def test_top_five_come_first_and_are_sorted(self):
        matches = [
            game(1, 34, "Ligue 1", ts=10),
            game(2, 679, "Europa League", ts=20),
            game(3, 17, "Premier League", ts=30),
            game(4, 325, "Brasileirão", "Sudamérica", ts=40),
            game(5, 8, "LaLiga", ts=50),
        ]
        grouped = group_matches(matches)
        self.assertEqual([key for key, _ in grouped], ["top", "other", "south"])
        self.assertEqual([item["id"] for item in grouped[0][1]], [3, 5, 1])
        self.assertEqual([item["id"] for item in grouped[1][1]], [2])
        self.assertEqual([item["id"] for item in grouped[2][1]], [4])

    def test_live_goes_before_upcoming_inside_section(self):
        matches = [
            game(1, 679, "Europa League", ts=10),
            game(2, 679, "Europa League", status="live", ts=20),
            game(3, 679, "Europa League", status="finished", ts=30),
        ]
        grouped = group_matches(matches)
        self.assertEqual([item["id"] for item in grouped[0][1]], [2, 1, 3])

    def test_live_top_league_goes_before_finished_top_league(self):
        matches = [
            game(1, 17, "Premier League", status="finished", ts=10),
            game(2, 8, "LaLiga", status="live", ts=20),
        ]
        grouped = group_matches(matches)
        self.assertEqual([item["id"] for item in grouped[0][1]], [2, 1])

    def test_empty_and_only_south(self):
        self.assertEqual(group_matches([]), [])
        grouped = group_matches(
            [game(1, 325, "Brasileirão", "Sudamérica")]
        )
        self.assertEqual([key for key, _ in grouped], ["south"])


if __name__ == "__main__":
    unittest.main()
