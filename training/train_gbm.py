"""Entrena un gradient boosting (Poisson) y lo ensambla con la red neuronal.

Opcional y solo para entrenamiento: usa scikit-learn para ajustar dos bosques
de árboles (goles local y visitante) y después serializa los árboles como
arrays para que la inferencia en la app siga siendo NumPy puro.

Uso:
    python training/train_gbm.py

Salida: ``training/data/gbm_trees.npz`` y el modelo ``neural_model.npz`` con
los árboles incrustados (versión 1.3).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "training"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TRAINING) not in sys.path:
    sys.path.insert(0, str(TRAINING))

try:
    from sklearn.ensemble import HistGradientBoostingRegressor
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Se necesita scikit-learn para entrenar el gradient boosting. "
        "Instálalo con: pip install scikit-learn"
    ) from exc

import train_neural as trainer  # noqa: E402

MODEL_PATH = ROOT / "sofascore" / "models" / "neural_model.npz"
METRICS_PATH = TRAINING / "metrics.json"
OUTPUT = TRAINING / "data" / "gbm_trees.npz"
WEIGHT_STEPS = 21


def _mae(home: np.ndarray, away: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    return (
        float(np.mean(np.abs(y[:, 0] - home))),
        float(np.mean(np.abs(y[:, 1] - away))),
    )


def _pack(trees: List[Dict[str, np.ndarray]]) -> Dict[str, Any]:
    counts = np.array([len(t["feat"]) for t in trees], dtype=np.int32)
    offsets = np.concatenate([[0], np.cumsum(counts)]).astype(np.int32)
    return {
        "n_trees": np.int32(len(trees)),
        "offsets": offsets,
        "feat": np.concatenate([t["feat"] for t in trees]).astype(np.int32),
        "thr": np.concatenate([t["thr"] for t in trees]).astype(np.float32),
        "left": np.concatenate([t["left"] for t in trees]).astype(np.int32),
        "right": np.concatenate([t["right"] for t in trees]).astype(np.int32),
        "missing_left": np.concatenate([t["missing_left"] for t in trees]).astype(np.int8),
        "leaf": np.concatenate([t["leaf"] for t in trees]).astype(np.int8),
        "value": np.concatenate([t["value"] for t in trees]).astype(np.float32),
    }


def _export(model: Any) -> Tuple[float, List[Dict[str, np.ndarray]]]:
    baseline = float(np.asarray(model._baseline_prediction).ravel()[0])
    trees: List[Dict[str, np.ndarray]] = []
    for predictor_list in model._predictors:
        for tree in predictor_list:
            nodes = tree.nodes
            trees.append(
                {
                    "feat": nodes["feature_idx"].astype(np.int32),
                    "thr": nodes["num_threshold"].astype(np.float32),
                    "left": nodes["left"].astype(np.int32),
                    "right": nodes["right"].astype(np.int32),
                    "missing_left": nodes["missing_go_to_left"].astype(np.int8),
                    "leaf": nodes["is_leaf"].astype(np.int8),
                    "value": nodes["value"].astype(np.float32),
                }
            )
    return baseline, trees


def main() -> int:
    X, Y, timestamps, metadata = trainer.build_samples()
    ts = np.asarray(timestamps, dtype=np.int64)
    train_mask = ts < trainer._parse_date("2026-07-01")
    val_mask = (ts >= trainer._parse_date("2026-07-01")) & (ts < trainer._parse_date("2026-10-01"))
    Xtr, Ytr = X[train_mask], Y[train_mask]
    Xva, Yva = X[val_mask], Y[val_mask]

    def fit(y: np.ndarray) -> Any:
        return HistGradientBoostingRegressor(
            loss="poisson", max_iter=250, max_leaf_nodes=31,
            learning_rate=0.08, l2_regularization=1.0, random_state=0,
        ).fit(Xtr, y)

    print("Entrenando gradient boosting…", flush=True)
    model_home = fit(Ytr[:, 0])
    model_away = fit(Ytr[:, 1])

    # Peso del ensamble con la red neuronal (goles).
    neural = trainer.neural
    model_nn = neural._load_model()
    mlp_logits = np.mean(
        [
            neural._forward(
                (Xva - model_nn["feature_mean"])
                / np.maximum(model_nn["feature_std"], 1e-6),
                weights,
                biases,
            )
            for weights, biases in zip(model_nn["weights"], model_nn["biases"])
        ],
        axis=0,
    )
    mlp_rates = np.exp(np.clip(mlp_logits, -6.0, 3.0))
    mlp_home = mlp_rates[:, 0]
    mlp_away = mlp_rates[:, 1]
    gbm_home = model_home.predict(Xva)
    gbm_away = model_away.predict(Xva)

    best = None
    for index in range(WEIGHT_STEPS):
        weight = index / (WEIGHT_STEPS - 1)
        home = (1.0 - weight) * mlp_home + weight * gbm_home
        away = (1.0 - weight) * mlp_away + weight * gbm_away
        home_mae, away_mae = _mae(home, away, Yva)
        if best is None or home_mae + away_mae < best[0]:
            best = (home_mae + away_mae, weight, home_mae, away_mae)
    _, weight, _, _ = best
    print(f"Peso del ensamble: {weight:.2f}", flush=True)

    baseline_home, trees_home = _export(model_home)
    baseline_away, trees_away = _export(model_away)
    packed_home = _pack(trees_home)
    packed_away = _pack(trees_away)

    arrays: Dict[str, Any] = {
        "gbm_weight": np.float32(weight),
        "gbm_home_baseline": np.float32(baseline_home),
        "gbm_away_baseline": np.float32(baseline_away),
    }
    for prefix, packed in (("gbm_home", packed_home), ("gbm_away", packed_away)):
        for key, value in packed.items():
            arrays[f"{prefix}_{key}"] = value

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUTPUT, **arrays)

    payload = np.load(MODEL_PATH, allow_pickle=True)
    merged = {key: payload[key] for key in payload.files}
    merged.update(arrays)
    merged["version"] = np.asarray("1.3")
    metrics = json.loads(str(payload["metrics_json"]))
    metrics["gbm_weight"] = round(weight, 3)
    metrics["model_version"] = "1.3"
    merged["metrics_json"] = np.asarray(json.dumps(metrics, ensure_ascii=False))
    np.savez_compressed(MODEL_PATH, **merged)
    METRICS_PATH.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Modelo actualizado a 1.3 en {MODEL_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
