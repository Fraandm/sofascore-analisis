"""Pruebas del entrenamiento y de la exclusión de amistosos."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import training.train_neural as training


def match_record(
    match_id: int,
    timestamp: int,
    tournament_id: int,
    home_score: int = 1,
    away_score: int = 0,
) -> dict:
    def stats(goals_for: int, goals_against: int) -> dict:
        return {
            "goals_for": goals_for,
            "goals_against": goals_against,
            "xg_for": 1.2,
            "xg_against": 0.8,
            "shots": 12,
            "shots_on_target": 5,
            "corners": 5,
            "cards": 2,
            "fouls": 11,
            "saves": 3,
            "stats_available": True,
        }

    return {
        "id": match_id,
        "timestamp": timestamp,
        "date": "2026-01-01T00:00:00+00:00",
        "tournament_id": tournament_id,
        "season_id": 1,
        "home_team_id": 1,
        "away_team_id": 2,
        "home_score": home_score,
        "away_score": away_score,
        "home": stats(home_score, away_score),
        "away": stats(away_score, home_score),
    }


class TrainingDataTests(unittest.TestCase):
    def _build(self, records):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.jsonl"
            path.write_text(
                "\n".join(json.dumps(record) for record in records) + "\n",
                encoding="utf-8",
            )
            with patch.object(training, "DATA_PATHS", (path,)), patch.object(
                training, "LINEUPS_PATH", Path(directory) / "missing.jsonl"
            ):
                return training.build_samples()

    def test_friendlies_are_not_used_as_history(self):
        records = [
            match_record(1, 1000, 10783),
            match_record(2, 2000, 851),
            match_record(3, 3000, 10783),
        ]
        X, _, _, metadata = self._build(records)
        self.assertEqual(X.shape[0], 0)
        self.assertEqual(metadata["national"], [])

    def test_national_matches_get_samples_with_two_prior_games(self):
        records = [
            match_record(1, 1000, 10783),
            match_record(2, 2000, 10783),
            match_record(3, 3000, 10783),
        ]
        X, Y, _, metadata = self._build(records)
        self.assertEqual(X.shape[0], 1)
        self.assertEqual(Y.shape[0], 1)
        self.assertEqual(metadata["national"], [True])


if __name__ == "__main__":
    unittest.main()
