"""Pruebas del motor Monte Carlo (sin red)."""

from __future__ import annotations

import copy
import json
import unittest

import numpy as np

from sofascore import simulation
from sofascore.exceptions import SofaScoreError


def make_rows(team: str, home_values: dict, away_values: dict, count: int = 8):
    rows = []
    for index in range(count):
        at_home = index % 2 == 0
        values = home_values if at_home else away_values
        rows.append(
            {
                "team": team,
                "event_id": 1000 + index,
                "date": f"2026-10-{index + 1:02d}",
                "opponent": f"Rival {index}",
                "venue": "casa" if at_home else "fuera",
                "home": at_home,
                "goals_for": values["goals_for"],
                "goals_against": values["goals_against"],
                "corners": values["corners"],
                "cards": values["cards"],
                "shots": values["shots"],
                "shots_on_target": values["shots_on_target"],
                "fouls": values["fouls"],
                "saves": values["saves"],
                "stats_available": True,
            }
        )
    return rows


HOME_ROWS = make_rows(
    "Local FC",
    {
        "goals_for": 2,
        "goals_against": 1,
        "corners": 7,
        "cards": 2,
        "shots": 15,
        "shots_on_target": 5,
        "fouls": 10,
        "saves": 3,
    },
    {
        "goals_for": 1,
        "goals_against": 2,
        "corners": 4,
        "cards": 3,
        "shots": 10,
        "shots_on_target": 3,
        "fouls": 14,
        "saves": 5,
    },
)

AWAY_ROWS = make_rows(
    "Visitante FC",
    {
        "goals_for": 2,
        "goals_against": 1,
        "corners": 6,
        "cards": 2,
        "shots": 13,
        "shots_on_target": 4,
        "fouls": 12,
        "saves": 4,
    },
    {
        "goals_for": 1,
        "goals_against": 2,
        "corners": 5,
        "cards": 3,
        "shots": 11,
        "shots_on_target": 4,
        "fouls": 13,
        "saves": 4,
    },
)

ANALYSIS = {
    "match": {
        "id": 999,
        "tournament": {"name": "Liga de prueba"},
        "start_time": "2026-11-10T20:00:00+00:00",
        "home_team": {"id": 1, "name": "Local FC"},
        "away_team": {"id": 2, "name": "Visitante FC"},
    },
    "window": 10,
    "season": {"id": 1, "name": "Test 26/27"},
    "use_neural": False,
    "teams": {
        "home": {
            "side": "home",
            "team": {"id": 1, "name": "Local FC"},
            "matches": HOME_ROWS,
            "sample_size": len(HOME_ROWS),
            "stats_sample_size": len(HOME_ROWS),
            "split": {"label": "en casa"},
        },
        "away": {
            "side": "away",
            "team": {"id": 2, "name": "Visitante FC"},
            "matches": AWAY_ROWS,
            "sample_size": len(AWAY_ROWS),
            "stats_sample_size": len(AWAY_ROWS),
            "split": {"label": "fuera"},
        },
    },
}


def make_lineup_side(
    prefix: str,
    expected_goals: float,
    shots: float,
    shots_on_target: float,
    rating: float,
    goals_prevented: float,
    market_value: float = 0.0,
) -> dict:
    positions = ["G"] + ["D"] * 4 + ["M"] * 4 + ["F"] * 2
    players = []
    for index, position in enumerate(positions):
        players.append(
            {
                "id": index + 1,
                "name": f"{prefix} {index + 1}",
                "position": position,
                "substitute": False,
                "avg_rating": rating + (0.05 if index == 10 else 0.0),
                "market_value": market_value,
                "season": {
                    "expected_goals": expected_goals / 11.0,
                    "expected_assists": 0.02,
                    "shots_per_game": shots / 11.0,
                    "shots_on_target_per_game": shots_on_target / 11.0,
                    "defensive_contributions_per_game": 2.0,
                    "goals_prevented": goals_prevented if position == "G" else None,
                    "saves_per_game": 3.0 if position == "G" else None,
                },
            }
        )
    return {
        "formation": "4-3-3",
        "players": players,
        "missing_players": [],
    }


def context_analysis(confirmed: bool = True) -> dict:
    analysis = copy.deepcopy(ANALYSIS)
    analysis["lineups"] = {
        "confirmed": confirmed,
        "home": make_lineup_side("Local", 0.3, 4.0, 1.5, 6.4, -5.0),
        "away": make_lineup_side("Visitante", 3.5, 20.0, 8.0, 7.4, 3.0),
    }
    analysis["referee"] = {
        "id": 99,
        "name": "Árbitro de prueba",
        "cards_per_match": 6.0,
        "fouls_per_match": 28.0,
        "sample": {"matches": 5},
        "source": "prueba",
    }
    return analysis


def enriched_rows(rows, values):
    enriched = copy.deepcopy(rows)
    for row in enriched:
        row.update(values)
    return enriched


class FeatureModelTests(unittest.TestCase):
    def test_xg_and_opponent_adjusted_rates_are_used(self):
        analysis = copy.deepcopy(ANALYSIS)
        analysis["teams"]["home"]["matches"] = enriched_rows(
            HOME_ROWS,
            {
                "xg_for": 2.5,
                "xg_against": 0.6,
                "big_chances_for": 3.0,
                "big_chances_against": 0.5,
                "shots_inside_box": 9.0,
                "shots_against": 8.0,
                "shots_on_target_against": 2.0,
                "corners_against": 3.0,
                "cards_against": 2.0,
                "fouls_against": 9.0,
            },
        )
        analysis["teams"]["away"]["matches"] = enriched_rows(
            AWAY_ROWS,
            {
                "xg_for": 0.6,
                "xg_against": 2.0,
                "big_chances_for": 0.5,
                "big_chances_against": 2.5,
                "shots_inside_box": 3.0,
                "shots_against": 14.0,
                "shots_on_target_against": 6.0,
                "corners_against": 7.0,
                "cards_against": 3.0,
                "fouls_against": 13.0,
            },
        )
        base = simulation.build_model(ANALYSIS)
        model = simulation.build_model(analysis)
        self.assertEqual(model["home"]["goals_meta"]["blend"], "xG + goles")
        self.assertIsNotNone(model["home"]["goals_meta"]["attack_xg"])
        self.assertIsNotNone(model["home"]["blend"]["shots"]["opponent"])
        self.assertLess(
            model["home"]["blend"]["shots"]["opponent"],
            model["home"]["blend"]["shots"]["own"],
        )
        self.assertGreater(model["home"]["goals"], base["home"]["goals"])
        self.assertLess(model["away"]["goals"], base["away"]["goals"])
        result = simulation.run_simulation(analysis, iterations=2000, seed=5)
        for side in ("home", "away"):
            self.assertTrue(
                np.all(
                    result.samples[f"{side}_goals"]
                    <= result.samples[f"{side}_shots_on_target"]
                )
            )


class ModelTests(unittest.TestCase):
    def test_model_estimates_are_coherent(self):
        model = simulation.build_model(ANALYSIS)
        for side in ("home", "away"):
            block = model[side]
            self.assertGreater(block["goals"], 0)
            self.assertGreater(block["shots"], block["expected_shots_on_target"])
            self.assertGreaterEqual(block["conversion"], 0.04)
            self.assertLessEqual(block["conversion"], 0.65)
            self.assertGreaterEqual(block["expected_saves"], 0)
            self.assertIn("dispersion", block)
            for key in ("shots", "corners", "cards", "fouls"):
                self.assertGreater(block["dispersion"][key], 0)
        self.assertAlmostEqual(
            model["home"]["expected_goals_against"], model["away"]["goals"], delta=0.01
        )

    def test_requires_matches(self):
        with self.assertRaises(SofaScoreError):
            simulation.build_model({"teams": {"home": {}, "away": {}}})


class ContextTests(unittest.TestCase):
    def test_lineup_and_referee_adjustments(self):
        baseline = simulation.build_model(ANALYSIS)
        model = simulation.build_model(context_analysis(confirmed=True))

        self.assertEqual(model["lineups"]["status"], "confirmada")
        self.assertTrue(model["lineups"]["applied"])
        self.assertLess(
            model["lineups"]["home"]["attack_factor"],
            1.0,
        )
        self.assertGreater(
            model["lineups"]["away"]["attack_factor"],
            1.0,
        )
        self.assertTrue(model["referee"]["applied"])
        self.assertGreater(model["referee"]["cards_factor"], 1.0)
        self.assertGreater(model["referee"]["fouls_factor"], 1.0)
        self.assertGreater(
            model["home"]["cards"] + model["away"]["cards"],
            baseline["home"]["cards"] + baseline["away"]["cards"],
        )
        self.assertGreater(
            model["home"]["fouls"] + model["away"]["fouls"],
            baseline["home"]["fouls"] + baseline["away"]["fouls"],
        )

    def test_probable_lineups_apply_less_weight(self):
        confirmed = simulation.build_model(context_analysis(confirmed=True))
        probable = simulation.build_model(context_analysis(confirmed=False))
        self.assertEqual(probable["lineups"]["status"], "probable")
        self.assertLess(
            abs(probable["lineups"]["home"]["attack_factor"] - 1.0),
            abs(confirmed["lineups"]["home"]["attack_factor"] - 1.0),
        )

    def test_context_strength_favours_stronger_away_side(self):
        analysis = copy.deepcopy(ANALYSIS)
        analysis["lineups"] = {
            "confirmed": True,
            "home": make_lineup_side(
                "Local", 2.0, 14.0, 5.0, 6.8, 0.0, market_value=5_000_000
            ),
            "away": make_lineup_side(
                "Visitante",
                2.0,
                14.0,
                5.0,
                7.2,
                0.0,
                market_value=60_000_000,
            ),
        }
        analysis["standings"] = {
            "home": {
                "matches": 6,
                "points": 3,
                "points_per_game": 0.5,
                "goal_difference_per_game": -1.2,
            },
            "away": {
                "matches": 6,
                "points": 15,
                "points_per_game": 2.5,
                "goal_difference_per_game": 1.5,
            },
        }
        analysis["h2h"] = {
            "home_wins": 0,
            "away_wins": 3,
            "draws": 1,
            "matches": 4,
        }
        model = simulation.build_model(analysis)
        self.assertTrue(model["context"]["applied"])
        self.assertLess(model["context"]["goal_factor_home"], 1.0)
        self.assertGreater(model["context"]["goal_factor_away"], 1.0)
        summary = simulation.simulate_match(analysis, iterations=5000, seed=42)
        self.assertGreater(
            summary["probabilities"]["winner"]["away"],
            summary["probabilities"]["winner"]["home"],
        )

    def test_without_context_nothing_is_applied(self):
        model = simulation.build_model(ANALYSIS)
        self.assertEqual(model["lineups"]["status"], "sin datos")
        self.assertFalse(model["lineups"]["applied"])
        self.assertFalse(model["referee"]["applied"])

    def test_context_simulation_is_coherent(self):
        result = simulation.run_simulation(
            context_analysis(), iterations=2000, seed=3
        )
        samples = result.samples
        for side in ("home", "away"):
            self.assertTrue(
                np.all(samples[f"{side}_goals"] <= samples[f"{side}_shots_on_target"])
            )
            self.assertTrue(
                np.all(
                    samples[f"{side}_shots_on_target"] <= samples[f"{side}_shots"]
                )
            )


class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = simulation.run_simulation(
            ANALYSIS, iterations=5000, seed=7
        )
        cls.summary = cls.result.summary()

    def test_reproducible_with_seed(self):
        again = simulation.run_simulation(ANALYSIS, iterations=5000, seed=7)
        for key, values in self.result.samples.items():
            np.testing.assert_array_equal(values, again.samples[key])

    def test_different_seed_changes_samples(self):
        other = simulation.run_simulation(ANALYSIS, iterations=5000, seed=8)
        self.assertFalse(
            np.array_equal(
                self.result.samples["total_goals"],
                other.samples["total_goals"],
            )
        )

    def test_samples_are_coherent(self):
        samples = self.result.samples
        for side in ("home", "away"):
            self.assertTrue(
                np.all(samples[f"{side}_goals"] <= samples[f"{side}_shots_on_target"])
            )
            self.assertTrue(
                np.all(
                    samples[f"{side}_shots_on_target"] <= samples[f"{side}_shots"]
                )
            )
        np.testing.assert_array_equal(
            samples["home_saves"],
            np.maximum(samples["away_shots_on_target"] - samples["away_goals"], 0),
        )
        np.testing.assert_array_equal(
            samples["total_goals"],
            samples["home_goals"] + samples["away_goals"],
        )

    def test_summary_is_serializable(self):
        encoded = json.dumps(self.summary, ensure_ascii=False)
        self.assertIn("probabilities", encoded)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["meta"]["iterations"], 5000)
        self.assertEqual(decoded["meta"]["seed"], 7)

    def test_probabilities(self):
        probabilities = self.summary["probabilities"]
        winner = probabilities["winner"]
        self.assertAlmostEqual(winner["home"] + winner["draw"] + winner["away"], 1.0, places=6)
        self.assertGreaterEqual(probabilities["btts"], 0.0)
        self.assertLessEqual(probabilities["btts"], 1.0)
        for key, lines in probabilities["over_under"].items():
            self.assertTrue(lines, key)
            for values in lines.values():
                self.assertAlmostEqual(
                    values["over"] + values["under"], 1.0, places=6
                )
        for side in ("home", "away"):
            saves = self.summary["teams"][side]["over_under"]["saves"]
            self.assertTrue(saves)
            for values in saves.values():
                self.assertAlmostEqual(
                    values["over"] + values["under"], 1.0, places=6
                )

    def test_totals_match_home_plus_away(self):
        totals = self.summary["totals"]["mean"]
        home = self.summary["teams"]["home"]["expected"]
        away = self.summary["teams"]["away"]["expected"]
        for key in ("corners", "cards", "shots", "shots_on_target", "fouls", "saves"):
            self.assertAlmostEqual(
                totals[key], home[key] + away[key], delta=0.03
            )
        self.assertAlmostEqual(
            totals["goals"], home["goals_for"] + away["goals_for"], delta=0.03
        )

    def test_histograms_and_scorelines(self):
        for key, histogram in self.summary["histograms"].items():
            self.assertTrue(histogram["labels"], key)
            self.assertEqual(len(histogram["labels"]), len(histogram["percent"]))
            self.assertAlmostEqual(sum(histogram["percent"]), 100.0, places=1)
        corners = self.summary["histograms"]["corners"]
        self.assertGreaterEqual(corners["max_value"], 20)
        self.assertTrue(corners["overflow_label"].endswith("+"))
        self.assertLess(corners["overflow_percent"], 3.0)
        self.assertEqual(len(self.summary["scorelines"]), 8)
        matrix = self.summary["score_matrix"]
        self.assertEqual(len(matrix["probabilities"]), len(matrix["labels"]))
        self.assertAlmostEqual(
            sum(sum(row) for row in matrix["probabilities"]), 1.0, places=4
        )

    def test_summary_rows_for_csv(self):
        rows = simulation.summary_rows(self.summary)
        self.assertTrue(rows)
        self.assertTrue(all("seccion" in row for row in rows))
        sections = {row["seccion"] for row in rows}
        self.assertIn("Esperado", sections)
        self.assertIn("Over/Under", sections)
        self.assertIn("Marcador", sections)

    def test_actual_result_is_included(self):
        analysis = copy.deepcopy(ANALYSIS)
        analysis["actual"] = {
            "score": "2-3",
            "stats_available": True,
            "home": {"goals_for": 2},
            "away": {"goals_for": 3},
            "totals": {"goals_for": 5},
        }
        summary = simulation.simulate_match(analysis, iterations=1000, seed=42)
        self.assertEqual(summary["actual"]["score"], "2-3")
        rows = simulation.summary_rows(summary)
        self.assertIn("Real", {row["seccion"] for row in rows})


class ValidationTests(unittest.TestCase):
    def test_iteration_limits(self):
        with self.assertRaises(SofaScoreError):
            simulation.run_simulation(ANALYSIS, iterations=10)
        with self.assertRaises(SofaScoreError):
            simulation.run_simulation(
                ANALYSIS, iterations=simulation.MAX_ITERATIONS + 1
            )

    def test_invalid_seed(self):
        with self.assertRaises(SofaScoreError):
            simulation.run_simulation(ANALYSIS, iterations=1000, seed="abc")


if __name__ == "__main__":
    unittest.main()
