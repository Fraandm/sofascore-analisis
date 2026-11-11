"""Pruebas de la red neuronal de apoyo (sin red)."""

from __future__ import annotations

import copy
import unittest

import numpy as np

from sofascore import neural, simulation
from tests.test_simulation import ANALYSIS

HAS_MODEL = neural.MODEL_PATH.exists()


class NeuralFeatureTests(unittest.TestCase):
    def test_feature_vector_has_expected_size(self):
        rows = copy.deepcopy(ANALYSIS["teams"]["home"]["matches"])
        vector = neural.build_feature_vector(
            rows,
            rows,
            {
                "points_per_game": 1.5,
                "goal_difference_per_game": 0.2,
                "position": 7.0,
                "elo": 1550.0,
                "rest_days": 5.0,
                "matches_played": 10.0,
            },
            {
                "points_per_game": 1.2,
                "goal_difference_per_game": -0.1,
                "position": 11.0,
                "elo": 1490.0,
                "rest_days": 4.0,
                "matches_played": 10.0,
            },
            {"home_wins": 2, "away_wins": 1, "draws": 1, "matches": 4},
        )
        self.assertEqual(vector.shape, (len(neural.FEATURE_NAMES),))
        self.assertTrue(np.all(np.isfinite(vector)))

    @unittest.skipUnless(HAS_MODEL, "modelo neuronal no entrenado")
    def test_model_predicts_rates(self):
        analysis = copy.deepcopy(ANALYSIS)
        analysis["use_neural"] = True
        rates = neural.predict_rates(analysis)
        self.assertIsNotNone(rates)
        self.assertTrue(rates["applied"])
        for key in neural.METRIC_KEYS:
            self.assertIn(key, rates["rates"])
            self.assertGreater(rates["rates"][key]["home"], 0)
            self.assertGreater(rates["rates"][key]["away"], 0)

    @unittest.skipUnless(HAS_MODEL, "modelo neuronal no entrenado")
    def test_simulation_uses_neural_when_available(self):
        analysis = copy.deepcopy(ANALYSIS)
        analysis["use_neural"] = True
        model = simulation.build_model(analysis)
        self.assertTrue(model["neural"]["applied"])
        self.assertIn("rates", model["neural"])


if __name__ == "__main__":
    unittest.main()
