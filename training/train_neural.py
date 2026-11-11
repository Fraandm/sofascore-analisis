"""Entrena la MLP de apoyo al simulador y guarda los pesos.

Uso:
    python training/train_neural.py

Entrada: ``training/data/dataset.jsonl`` generado por collect_dataset.py.
Salida: ``sofascore/models/neural_model.npz`` y ``training/metrics.json``.
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sofascore import neural  # noqa: E402

DATA_PATHS = (
    ROOT / "training" / "data" / "dataset.jsonl",
    ROOT / "training" / "data" / "dataset_extra.jsonl",
)
MODEL_PATH = ROOT / "sofascore" / "models" / "neural_model.npz"
METRICS_PATH = ROOT / "training" / "metrics.json"
LINEUPS_PATH = ROOT / "training" / "data" / "lineups.jsonl"

TARGET_KEYS = (
    "goals_for",
    "goals_for",
    "shots",
    "shots",
    "shots_on_target",
    "shots_on_target",
    "corners",
    "corners",
    "cards",
    "cards",
    "fouls",
    "fouls",
)
TARGET_WEIGHTS = np.asarray(
    [2.0, 2.0, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.5, 0.5, 0.5, 0.5],
    dtype=np.float32,
)
TARGET_WEIGHTS /= TARGET_WEIGHTS.sum()


def _timestamp(record: Dict[str, Any]) -> float:
    value = record.get("timestamp")
    if isinstance(value, (int, float)):
        return float(value)
    text = record.get("date") or ""
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _parse_date(value: Any) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(str(value)[:10]).replace(
            tzinfo=timezone.utc
        ).timestamp()
    except ValueError:
        return 0.0


def _table_context(table: Dict[int, Dict[str, Any]], team_id: int) -> Dict[str, float]:
    stats = table.get(team_id)
    if not stats or stats["matches"] <= 0:
        return {
            "points_per_game": 1.35,
            "goal_difference_per_game": 0.0,
            "position": 10.0,
            "matches_played": 0.0,
        }
    matches = stats["matches"]
    gd = stats["goals_for"] - stats["goals_against"]
    points = stats["points"]
    position = 1
    for other in table.values():
        if other["matches"] <= 0:
            continue
        other_gd = other["goals_for"] - other["goals_against"]
        if (other["points"], other_gd) > (points, gd):
            position += 1
    return {
        "points_per_game": points / matches,
        "goal_difference_per_game": gd / matches,
        "position": float(position),
        "matches_played": float(matches),
    }


def _elo_expected(home: float, away: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((away - home) / 400.0))


def build_samples() -> Tuple[np.ndarray, np.ndarray, List[int], Dict[str, Any]]:
    by_id: Dict[int, Dict[str, Any]] = {}
    for path in DATA_PATHS:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                by_id[int(record["id"])] = record
    records = list(by_id.values())
    records.sort(key=_timestamp)
    print(f"Partidos de entrada: {len(records)}", flush=True)
    lineups: Dict[int, Dict[str, Any]] = {}
    if LINEUPS_PATH.exists():
        with LINEUPS_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if item.get("id") is not None:
                    lineups[int(item["id"])] = item
    print(f"Alineaciones históricas: {len(lineups)}", flush=True)

    team_history: Dict[int, List[Dict[str, Any]]] = {}
    elo: Dict[int, float] = {}
    elo_history: Dict[int, List[List[float]]] = {}
    tables: Dict[Tuple[Any, Any], Dict[int, Dict[str, Any]]] = {}
    h2h: Dict[Tuple[int, int], List[int]] = {}

    features: List[np.ndarray] = []
    targets: List[List[float]] = []
    timestamps: List[int] = []

    for record in records:
        match_ts = _timestamp(record)
        home_id = int(record["home_team_id"])
        away_id = int(record["away_team_id"])
        home_rows = team_history.get(home_id, [])
        away_rows = team_history.get(away_id, [])
        table_key = (record.get("tournament_id"), record.get("season_id"))
        table = tables.setdefault(table_key, {})
        home_table = _table_context(table, home_id)
        away_table = _table_context(table, away_id)
        home_context = {
            **home_table,
            "elo": elo.get(home_id, 1500.0),
            "rest_days": neural.rest_days(home_rows, match_ts),
        }
        away_context = {
            **away_table,
            "elo": elo.get(away_id, 1500.0),
            "rest_days": neural.rest_days(away_rows, match_ts),
        }
        pair = (min(home_id, away_id), max(home_id, away_id))
        duel = h2h.get(pair)
        if duel:
            wins_low, wins_high, draws = duel
            if home_id == pair[0]:
                h2h_context = {
                    "home_wins": wins_low,
                    "away_wins": wins_high,
                    "draws": draws,
                    "matches": wins_low + wins_high + draws,
                }
            else:
                h2h_context = {
                    "home_wins": wins_high,
                    "away_wins": wins_low,
                    "draws": draws,
                    "matches": wins_low + wins_high + draws,
                }
        else:
            h2h_context = {"matches": 0}

        if len(home_rows) >= 3 and len(away_rows) >= 3:
            lineup = lineups.get(int(record["id"])) or {}
            features.append(
                neural.build_feature_vector(
                    home_rows,
                    away_rows,
                    home_context,
                    away_context,
                    h2h_context,
                    lineup.get("home"),
                    lineup.get("away"),
                    record.get("tournament_id"),
                )
            )
            targets.append(
                [
                    float(record["home"]["goals_for"]),
                    float(record["away"]["goals_for"]),
                    float(record["home"]["shots"]),
                    float(record["away"]["shots"]),
                    float(record["home"]["shots_on_target"]),
                    float(record["away"]["shots_on_target"]),
                    float(record["home"]["corners"]),
                    float(record["away"]["corners"]),
                    float(record["home"]["cards"]),
                    float(record["away"]["cards"]),
                    float(record["home"]["fouls"]),
                    float(record["away"]["fouls"]),
                ]
            )
            timestamps.append(int(match_ts))

        # Actualizar historial, Elo, tabla y H2H después de calcular features.
        team_history.setdefault(home_id, []).insert(0, record["home"])
        team_history.setdefault(away_id, []).insert(0, record["away"])

        home_goals = int(record["home_score"] or 0)
        away_goals = int(record["away_score"] or 0)
        score = 1.0 if home_goals > away_goals else (0.0 if home_goals < away_goals else 0.5)
        home_elo = elo.get(home_id, 1500.0)
        away_elo = elo.get(away_id, 1500.0)
        expected = _elo_expected(home_elo, away_elo)
        goal_diff = abs(home_goals - away_goals)
        k_factor = 20.0 * (1.0 if goal_diff <= 1 else 1.5 if goal_diff == 2 else 1.75 if goal_diff == 3 else 2.0)
        change = k_factor * (score - expected)
        new_home = home_elo + change
        new_away = away_elo - change
        elo[home_id] = new_home
        elo[away_id] = new_away
        elo_history.setdefault(home_id, []).append([match_ts, new_home])
        elo_history.setdefault(away_id, []).append([match_ts, new_away])

        for team_id, goals_for, goals_against in (
            (home_id, home_goals, away_goals),
            (away_id, away_goals, home_goals),
        ):
            row = table.setdefault(
                team_id,
                {"matches": 0, "points": 0, "goals_for": 0, "goals_against": 0},
            )
            row["matches"] += 1
            row["goals_for"] += goals_for
            row["goals_against"] += goals_against
            if goals_for > goals_against:
                row["points"] += 3
            elif goals_for == goals_against:
                row["points"] += 1

        if pair not in h2h:
            h2h[pair] = [0, 0, 0]
        if home_id == pair[0]:
            if home_goals > away_goals:
                h2h[pair][0] += 1
            elif home_goals < away_goals:
                h2h[pair][1] += 1
            else:
                h2h[pair][2] += 1
        else:
            if away_goals > home_goals:
                h2h[pair][0] += 1
            elif away_goals < home_goals:
                h2h[pair][1] += 1
            else:
                h2h[pair][2] += 1

    X = np.stack(features).astype(np.float32)
    Y = np.asarray(targets, dtype=np.float32)
    print(f"Muestras utilizables: {len(X)} · features: {X.shape[1]}", flush=True)
    return X, Y, timestamps, {
        "elo_history": {str(key): value for key, value in elo_history.items()},
    }


def init_mlp(dims: Sequence[int], rng: np.random.Generator):
    weights = []
    biases = []
    for lower, upper in zip(dims[:-1], dims[1:]):
        weights.append(
            rng.normal(
                0.0,
                math.sqrt(2.0 / max(1, lower)),
                size=(lower, upper),
            ).astype(np.float32)
        )
        biases.append(np.zeros(upper, dtype=np.float32))
    return weights, biases


def forward(
    x: np.ndarray,
    weights: Sequence[np.ndarray],
    biases: Sequence[np.ndarray],
) -> Tuple[np.ndarray, List[np.ndarray]]:
    activations = [x]
    hidden = x
    for index, (weight, bias) in enumerate(zip(weights, biases)):
        hidden = hidden @ weight + bias
        if index < len(weights) - 1:
            np.maximum(hidden, 0.0, out=hidden)
        activations.append(hidden)
    return hidden, activations


def loss_and_grad(
    x: np.ndarray,
    y: np.ndarray,
    weights: Sequence[np.ndarray],
    biases: Sequence[np.ndarray],
    weight_decay: float,
    sample_weights: Optional[np.ndarray] = None,
):
    logits, activations = forward(x, weights, biases)
    log_rate = np.clip(logits, -6.0, 3.0)
    rate = np.exp(log_rate)
    if sample_weights is None:
        sample_weights = np.ones((len(x), 1), dtype=np.float32)
    loss = float(
        np.mean(
            sample_weights
            * TARGET_WEIGHTS[None, :]
            * (rate - y * log_rate)
        )
    )
    grad = (
        (rate - y)
        * TARGET_WEIGHTS[None, :]
        * sample_weights
        / max(1e-9, float(np.mean(sample_weights)))
    )
    grad_weights = [None] * len(weights)
    grad_biases = [None] * len(weights)
    for layer in range(len(weights) - 1, -1, -1):
        grad_weights[layer] = activations[layer].T @ grad + weight_decay * weights[layer]
        grad_biases[layer] = grad.sum(axis=0)
        if layer > 0:
            grad = grad @ weights[layer].T
            grad = grad * (activations[layer] > 0.0)
    return loss, grad_weights, grad_biases


def train_one(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    hidden: Sequence[int],
    learning_rate: float,
    weight_decay: float,
    epochs: int,
    patience: int,
    seed: int,
    sample_weights: Optional[np.ndarray] = None,
):
    rng = np.random.default_rng(seed)
    dims = [x_train.shape[1], *hidden, y_train.shape[1]]
    weights, biases = init_mlp(dims, rng)
    params = list(weights) + list(biases)
    moment1 = [np.zeros_like(param) for param in params]
    moment2 = [np.zeros_like(param) for param in params]
    beta1, beta2 = 0.9, 0.999
    best_val = float("inf")
    best_weights = [w.copy() for w in weights]
    best_biases = [b.copy() for b in biases]
    stale = 0
    batch_size = 128
    if sample_weights is None:
        sample_weights = np.ones((len(x_train), 1), dtype=np.float32)
    for epoch in range(1, epochs + 1):
        order = rng.permutation(len(x_train))
        for start in range(0, len(order), batch_size):
            batch = order[start : start + batch_size]
            _, grad_w, grad_b = loss_and_grad(
                x_train[batch],
                y_train[batch],
                weights,
                biases,
                weight_decay,
                sample_weights[batch],
            )
            grads = grad_w + grad_b
            for index, (param, grad) in enumerate(zip(params, grads)):
                moment1[index] = beta1 * moment1[index] + (1 - beta1) * grad
                moment2[index] = beta2 * moment2[index] + (1 - beta2) * grad * grad
                m_hat = moment1[index] / (1 - beta1 ** epoch)
                v_hat = moment2[index] / (1 - beta2 ** epoch)
                param -= learning_rate * m_hat / (np.sqrt(v_hat) + 1e-8)
        val_logits, _ = forward(x_val, weights, biases)
        val_log_rate = np.clip(val_logits, -6.0, 3.0)
        val_loss = float(
            np.mean(
                TARGET_WEIGHTS[None, :]
                * (np.exp(val_log_rate) - y_val * val_log_rate)
            )
        )
        if val_loss < best_val - 1e-5:
            best_val = val_loss
            best_weights = [w.copy() for w in weights]
            best_biases = [b.copy() for b in biases]
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                break
    return best_weights, best_biases, best_val, epoch


def ensemble_rates(
    x: np.ndarray,
    models: Sequence[Tuple[Sequence[np.ndarray], Sequence[np.ndarray]]],
) -> np.ndarray:
    logits = []
    for weights, biases in models:
        output, _ = forward(x, weights, biases)
        logits.append(output)
    combined = np.mean(np.stack(logits, axis=0), axis=0)
    return np.exp(np.clip(combined, -6.0, 3.0))


def mae(prediction: np.ndarray, target: np.ndarray) -> List[float]:
    return np.mean(np.abs(prediction - target), axis=0).round(4).tolist()


def main() -> int:
    started = time.perf_counter()
    X, Y, timestamps, metadata = build_samples()
    ts = np.asarray(timestamps, dtype=np.int64)
    train_mask = ts < _parse_date("2026-07-01")
    val_mask = (ts >= _parse_date("2026-07-01")) & (ts < _parse_date("2026-10-01"))
    test_mask = ts >= _parse_date("2026-10-01")
    print(
        f"Split: train={int(train_mask.sum())} val={int(val_mask.sum())} "
        f"test={int(test_mask.sum())}",
        flush=True,
    )
    if min(train_mask.sum(), val_mask.sum(), test_mask.sum()) == 0:
        raise SystemExit("Split temporal vacío")

    mean = X[train_mask].mean(axis=0)
    std = X[train_mask].std(axis=0)
    std[std < 1e-6] = 1.0
    Xn = (X - mean) / std
    x_train, y_train = Xn[train_mask], Y[train_mask]
    x_val, y_val = Xn[val_mask], Y[val_mask]
    x_test, y_test = Xn[test_mask], Y[test_mask]
    train_ts = ts[train_mask].astype(np.float64)
    age_days = (train_ts.max() - train_ts) / 86400.0
    train_weights = (0.5 ** (age_days / 730.0)).astype(np.float32)
    train_weights /= max(1e-9, float(train_weights.mean()))
    train_weights = train_weights[:, None]

    feature_index = {name: index for index, name in enumerate(neural.FEATURE_NAMES)}
    target_index = {name: index for index, name in enumerate(neural.TARGET_NAMES)}
    baseline_test = np.zeros_like(y_test)
    baseline_val = np.zeros_like(y_val)
    for target, key in zip(neural.TARGET_NAMES, TARGET_KEYS):
        side = "home" if target.startswith("home_") else "away"
        feature = f"{side}_last10_{key}"
        index = feature_index[feature]
        baseline_test[:, target_index[target]] = np.maximum(0.05, X[test_mask][:, index])
        baseline_val[:, target_index[target]] = np.maximum(0.05, X[val_mask][:, index])

    configs = (
        ((64, 64), 1e-3),
        ((96, 96), 1e-3),
        ((128, 128), 8e-4),
        ((64, 128, 64), 8e-4),
    )
    best = None
    for hidden, learning_rate in configs:
        weights, biases, val_loss, epochs = train_one(
            x_train,
            y_train,
            x_val,
            y_val,
            hidden,
            learning_rate,
            1e-4,
            500,
            35,
            seed=42,
            sample_weights=train_weights,
        )
        print(
            f"config {hidden} lr={learning_rate}: val={val_loss:.5f} "
            f"epochs={epochs}",
            flush=True,
        )
        if best is None or val_loss < best[2]:
            best = (hidden, learning_rate, val_loss, weights, biases)

    hidden, learning_rate, _, _, _ = best
    print(f"Mejor config: {hidden} lr={learning_rate}", flush=True)
    models = []
    for seed in range(5):
        weights, biases, val_loss, epochs = train_one(
            x_train,
            y_train,
            x_val,
            y_val,
            hidden,
            learning_rate,
            1e-4,
            500,
            35,
            seed=100 + seed,
            sample_weights=train_weights,
        )
        models.append((weights, biases))
        print(f"ensemble {seed + 1}/5 val={val_loss:.5f} epochs={epochs}", flush=True)

    val_rates = ensemble_rates(x_val, models)
    test_rates = ensemble_rates(x_test, models)

    blend_weights = np.zeros(len(neural.TARGET_NAMES), dtype=np.float32)
    for index, target in enumerate(neural.TARGET_NAMES):
        baseline_error = float(
            np.mean(np.abs(baseline_val[:, index] - y_val[:, index]))
        )
        neural_error = float(
            np.mean(np.abs(val_rates[:, index] - y_val[:, index]))
        )
        if neural_error >= baseline_error:
            blend_weights[index] = 0.0
            continue
        options = np.linspace(0.0, 0.35, 8)
        errors = [
            np.mean(
                np.abs(
                    (1 - weight) * baseline_val[:, index]
                    + weight * val_rates[:, index]
                    - y_val[:, index]
                )
            )
            for weight in options
        ]
        blend_weights[index] = float(options[int(np.argmin(errors))])

    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train": int(train_mask.sum()),
        "validation": int(val_mask.sum()),
        "test": int(test_mask.sum()),
        "hidden": list(hidden),
        "learning_rate": learning_rate,
        "ensemble": 5,
        "test_mae_neural": mae(test_rates, y_test),
        "test_mae_baseline": mae(baseline_test, y_test),
        "blend_weights": {
            name: round(float(value), 3)
            for name, value in zip(neural.TARGET_NAMES, blend_weights)
        },
    }
    print("MAE test neural:", metrics["test_mae_neural"], flush=True)
    print("MAE test baseline:", metrics["test_mae_baseline"], flush=True)

    context_defaults = np.asarray(
        [mean[feature_index[f"home_{key}"]] for key in neural.SIDE_CONTEXT],
        dtype=np.float32,
    )
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    arrays: Dict[str, Any] = {
        "feature_mean": mean.astype(np.float32),
        "feature_std": std.astype(np.float32),
        "feature_names": np.asarray(neural.FEATURE_NAMES),
        "target_names": np.asarray(neural.TARGET_NAMES),
        "context_defaults": context_defaults,
        "elo_history_json": json.dumps(metadata["elo_history"], separators=(",", ":")),
        "blend_weights": blend_weights,
        "ensemble": len(models),
        "n_layers": len(models[0][0]),
        "version": "1.0",
        "metrics_json": json.dumps(metrics, ensure_ascii=False),
    }
    for model_index, (weights, biases) in enumerate(models):
        for layer, (weight, bias) in enumerate(zip(weights, biases)):
            arrays[f"w_{model_index}_{layer}"] = weight
            arrays[f"b_{model_index}_{layer}"] = bias
    np.savez_compressed(MODEL_PATH, **arrays)
    METRICS_PATH.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Modelo guardado en {MODEL_PATH}", flush=True)
    print(f"Tiempo total: {time.perf_counter() - started:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
