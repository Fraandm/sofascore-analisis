"""Pruebas de la red neuronal de apoyo (sin red)."""

from __future__ import annotations

import copy
import unittest

import numpy as np

from sofascore import gbm, neural, simulation
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

    def test_national_feature_for_friendlies(self):
        rows = copy.deepcopy(ANALYSIS["teams"]["home"]["matches"])
        vector = neural.build_feature_vector(
            rows,
            rows,
            {},
            {},
            {},
            None,
            None,
            851,
        )
        index = neural.FEATURE_NAMES.index(neural.NATIONAL_FEATURE)
        self.assertEqual(float(vector[index]), 1.0)

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
    def test_gbm_ensemble_is_available(self):
        model = neural._load_model()
        self.assertIsNotNone(model)
        if model.get("gbm_weight"):
            self.assertGreater(model["gbm_weight"], 0)
            self.assertIn("gbm_home", model)
            self.assertIn("gbm_away", model)
            features = neural.features_from_analysis(ANALYSIS, model)
            home = float(gbm.predict_rates(features[None, :], model["gbm_home"])[0])
            away = float(gbm.predict_rates(features[None, :], model["gbm_away"])[0])
            self.assertTrue(np.isfinite(home) and home > 0)
            self.assertTrue(np.isfinite(away) and away > 0)

    @unittest.skipUnless(HAS_MODEL, "modelo neuronal no entrenado")
    def test_simulation_uses_neural_when_available(self):
        analysis = copy.deepcopy(ANALYSIS)
        analysis["use_neural"] = True
        model = simulation.build_model(analysis)
        self.assertTrue(model["neural"]["applied"])
        self.assertIn("rates", model["neural"])


if __name__ == "__main__":
    unittest.main()
