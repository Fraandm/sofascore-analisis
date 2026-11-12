"""Red neuronal ligera para complementar el modelo Monte Carlo.

El modelo es una MLP multi-salida implementada con NumPy: no añade PyTorch
al ejecutable. Predice las medias de goles, remates, remates al arco,
córners, tarjetas y faltas a partir de la forma previa, Elo, clasificación,
descanso y H2H. Incluye competiciones de clubes y selecciones; los amistosos
internacionales no forman parte del entrenamiento. El entrenamiento se hace
offline con ``training/train_neural.py``.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import normalize, regions

MODEL_PATH = Path(__file__).with_name("models") / "neural_model.npz"

SIDE_METRICS_10 = (
    "goals_for",
    "goals_against",
    "xg_for",
    "xg_against",
    "xg_on_target_for",
    "xg_on_target_against",
    "big_chances_for",
    "big_chances_against",
    "shots",
    "shots_against",
    "shots_on_target",
    "shots_on_target_against",
    "shots_inside_box",
    "shots_inside_box_against",
    "corners",
    "corners_against",
    "cards",
    "cards_against",
    "fouls",
    "fouls_against",
    "saves",
    "saves_against",
)
SIDE_METRICS_5 = (
    "goals_for",
    "goals_against",
    "xg_for",
    "xg_against",
    "xg_on_target_for",
    "xg_on_target_against",
    "big_chances_for",
    "big_chances_against",
)
SIDE_CONTEXT = (
    "points_per_game",
    "goal_difference_per_game",
    "position",
    "elo",
    "rest_days",
    "matches_played",
)
H2H_FEATURES = (
    "h2h_home_share",
    "h2h_draw_share",
    "h2h_away_share",
    "h2h_matches",
)
DIFF_FEATURES = (
    "elo_diff",
    "ppg_diff",
    "gdpg_diff",
    "last10_goals_diff",
    "last10_xg_diff",
)
LINEUP_FEATURES = (
    "home_lineup_market_log",
    "away_lineup_market_log",
    "home_lineup_rating",
    "away_lineup_rating",
    "home_lineup_missing",
    "away_lineup_missing",
    "home_lineup_missing_value_log",
    "away_lineup_missing_value_log",
    "home_lineup_starters",
    "away_lineup_starters",
    "home_lineup_confidence",
    "away_lineup_confidence",
    "lineup_market_diff",
    "lineup_rating_diff",
)
COMPETITION_IDS = (
    17,
    8,
    23,
    35,
    34,
    7,
    325,
    155,
    11539,
    240,
    406,
    11653,
    30743,
    11541,
    16736,
    231,
    16940,
    480,
    # Selecciones oficiales. Los amistosos (851/852) quedan fuera del
    # entrenamiento y, por tanto, tampoco tienen columna propia.
    *sorted(regions.NATIONAL_TOURNAMENT_IDS - regions.FRIENDLY_TOURNAMENT_IDS),
)
COMPETITION_FEATURES = tuple(f"competition_{value}" for value in COMPETITION_IDS)
NATIONAL_FEATURE = "is_national_match"

FEATURE_NAMES: Tuple[str, ...] = tuple(
    [f"home_last10_{key}" for key in SIDE_METRICS_10]
    + [f"home_last5_{key}" for key in SIDE_METRICS_5]
    + [f"home_venue5_{key}" for key in SIDE_METRICS_5]
    + [f"home_{key}" for key in SIDE_CONTEXT]
    + [f"away_last10_{key}" for key in SIDE_METRICS_10]
    + [f"away_last5_{key}" for key in SIDE_METRICS_5]
    + [f"away_venue5_{key}" for key in SIDE_METRICS_5]
    + [f"away_{key}" for key in SIDE_CONTEXT]
    + list(H2H_FEATURES)
    + list(DIFF_FEATURES)
    + list(LINEUP_FEATURES)
    + list(COMPETITION_FEATURES)
    + [NATIONAL_FEATURE]
)

TARGET_NAMES: Tuple[str, ...] = (
    "home_goals",
    "away_goals",
    "home_shots",
    "away_shots",
    "home_shots_on_target",
    "away_shots_on_target",
    "home_corners",
    "away_corners",
    "home_cards",
    "away_cards",
    "home_fouls",
    "away_fouls",
)

METRIC_KEYS = ("goals", "shots", "shots_on_target", "corners", "cards", "fouls")
DEFAULT_CONTEXT = (1.35, 0.0, 10.0, 1500.0, 7.0, 10.0)

_MODEL_CACHE: Dict[str, Any] = {"mtime": None, "model": None}


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _recent_values(
    rows: Sequence[Dict[str, Any]],
    key: str,
    limit: int,
    venue: Optional[bool] = None,
) -> List[float]:
    values: List[float] = []
    for row in rows:
        if venue is not None and bool(row.get("home")) != venue:
            continue
        number = _number(row.get(key))
        if number is None:
            continue
        values.append(number)
        if len(values) >= limit:
            break
    return values


def _mean(
    rows: Sequence[Dict[str, Any]],
    key: str,
    limit: int,
    venue: Optional[bool] = None,
    default: float = 0.0,
) -> float:
    values = _recent_values(rows, key, limit, venue=venue)
    return sum(values) / len(values) if values else default


def _parse_timestamp(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10]).timestamp()
        except ValueError:
            return None


def rest_days(
    rows: Sequence[Dict[str, Any]],
    match_timestamp: Optional[float],
    default: float = 7.0,
) -> float:
    if not rows or match_timestamp is None:
        return default
    last = _parse_timestamp(
        rows[0].get("start_time") or rows[0].get("date")
    )
    if last is None:
        return default
    return max(0.0, min(30.0, (float(match_timestamp) - last) / 86400.0))


def _side_features(
    rows: Sequence[Dict[str, Any]],
    venue: bool,
    context: Dict[str, float],
) -> List[float]:
    features: List[float] = []
    features.extend(_mean(rows, key, 10) for key in SIDE_METRICS_10)
    features.extend(_mean(rows, key, 5) for key in SIDE_METRICS_5)
    features.extend(
        _mean(rows, key, 5, venue=venue) for key in SIDE_METRICS_5
    )
    features.extend(float(context.get(key, 0.0)) for key in SIDE_CONTEXT)
    return features


def build_feature_vector(
    home_rows: Sequence[Dict[str, Any]],
    away_rows: Sequence[Dict[str, Any]],
    home_context: Dict[str, float],
    away_context: Dict[str, float],
    h2h: Optional[Dict[str, Any]] = None,
    home_lineup: Optional[Dict[str, Any]] = None,
    away_lineup: Optional[Dict[str, Any]] = None,
    competition_id: Optional[int] = None,
) -> np.ndarray:
    features: List[float] = []
    features.extend(_side_features(home_rows, True, home_context))
    features.extend(_side_features(away_rows, False, away_context))
    h2h = h2h or {}
    matches = float(h2h.get("matches") or 0)
    if matches > 0:
        home_share = (
            float(h2h.get("home_wins") or 0) + 0.5 * float(h2h.get("draws") or 0)
        ) / matches
        away_share = (
            float(h2h.get("away_wins") or 0) + 0.5 * float(h2h.get("draws") or 0)
        ) / matches
        draw_share = float(h2h.get("draws") or 0) / matches
        matches_norm = min(1.0, matches / 10.0)
    else:
        home_share = away_share = draw_share = matches_norm = 0.0
    features.extend([home_share, draw_share, away_share, matches_norm])
    features.extend(
        [
            (float(home_context.get("elo", 1500.0)) - float(away_context.get("elo", 1500.0)))
            / 400.0,
            float(home_context.get("points_per_game", 0.0))
            - float(away_context.get("points_per_game", 0.0)),
            float(home_context.get("goal_difference_per_game", 0.0))
            - float(away_context.get("goal_difference_per_game", 0.0)),
            _mean(home_rows, "goals_for", 10)
            - _mean(away_rows, "goals_for", 10),
            _mean(home_rows, "xg_for", 10)
            - _mean(away_rows, "xg_for", 10),
        ]
    )
    home_lineup = home_lineup or {}
    away_lineup = away_lineup or {}
    home_market = float(home_lineup.get("market_value") or 0.0)
    away_market = float(away_lineup.get("market_value") or 0.0)
    home_rating = float(home_lineup.get("avg_rating") or 0.0)
    away_rating = float(away_lineup.get("avg_rating") or 0.0)
    features.extend(
        [
            math.log1p(max(0.0, home_market)),
            math.log1p(max(0.0, away_market)),
            home_rating,
            away_rating,
            float(home_lineup.get("missing_count") or 0.0),
            float(away_lineup.get("missing_count") or 0.0),
            math.log1p(max(0.0, float(home_lineup.get("missing_market_value") or 0.0))),
            math.log1p(max(0.0, float(away_lineup.get("missing_market_value") or 0.0))),
            float(home_lineup.get("starters") or 0.0),
            float(away_lineup.get("starters") or 0.0),
            float(home_lineup.get("confidence") or 0.0),
            float(away_lineup.get("confidence") or 0.0),
            math.log1p(max(0.0, home_market))
            - math.log1p(max(0.0, away_market)),
            home_rating - away_rating,
        ]
    )
    competition = int(competition_id) if competition_id is not None else -1
    features.extend(1.0 if competition == value else 0.0 for value in COMPETITION_IDS)
    features.append(
        1.0 if competition in regions.NATIONAL_TOURNAMENT_IDS else 0.0
    )
    return np.asarray(features, dtype=np.float32)


def _load_model() -> Optional[Dict[str, Any]]:
    if not MODEL_PATH.exists():
        return None
    try:
        mtime = MODEL_PATH.stat().st_mtime
    except OSError:
        return None
    if _MODEL_CACHE["mtime"] == mtime and _MODEL_CACHE["model"] is not None:
        return _MODEL_CACHE["model"]
    try:
        payload = np.load(MODEL_PATH, allow_pickle=True)
        model: Dict[str, Any] = {
            "feature_mean": np.asarray(payload["feature_mean"], dtype=np.float32),
            "feature_std": np.asarray(payload["feature_std"], dtype=np.float32),
            "feature_names": tuple(str(value) for value in payload["feature_names"]),
            "target_names": tuple(str(value) for value in payload["target_names"]),
            "context_defaults": np.asarray(
                payload["context_defaults"], dtype=np.float32
            ),
            "elo_history": json.loads(str(payload["elo_history_json"])),
            "blend_weights": np.asarray(
                payload["blend_weights"], dtype=np.float32
            ),
            "ensemble": int(payload["ensemble"]),
            "n_layers": int(payload["n_layers"]),
            "version": str(payload["version"]),
            "metrics": json.loads(str(payload["metrics_json"])),
            "weights": [],
            "biases": [],
        }
        for index in range(model["ensemble"]):
            weights = []
            biases = []
            for layer in range(model["n_layers"]):
                weights.append(
                    np.asarray(
                        payload[f"w_{index}_{layer}"], dtype=np.float32
                    )
                )
                biases.append(
                    np.asarray(
                        payload[f"b_{index}_{layer}"], dtype=np.float32
                    )
                )
            model["weights"].append(weights)
            model["biases"].append(biases)
    except (OSError, KeyError, ValueError):
        return None
    _MODEL_CACHE["mtime"] = mtime
    _MODEL_CACHE["model"] = model
    return model


def model_version() -> str:
    model = _load_model()
    if model is None:
        return "none"
    return f"{model['version']}:{int(_MODEL_CACHE['mtime'] or 0)}"


def elo_at(
    model: Dict[str, Any], team_id: Any, timestamp: Optional[float]
) -> float:
    history = model["elo_history"].get(str(team_id))
    if not history:
        return 1500.0
    reference = float(timestamp) if timestamp is not None else float("inf")
    rating = 1500.0
    for moment, value in history:
        if float(moment) < reference:
            rating = float(value)
        else:
            break
    return rating


def _context_from_analysis(
    analysis: Dict[str, Any],
    side: str,
    model: Dict[str, Any],
) -> Dict[str, float]:
    defaults = model["context_defaults"]
    default_map = dict(zip(SIDE_CONTEXT, defaults))
    match = (analysis or {}).get("match") or {}
    timestamp = _parse_timestamp(match.get("start_timestamp"))
    standings = (analysis or {}).get("standings") or {}
    standing = standings.get(side) or {}
    rows = (
        ((analysis or {}).get("teams") or {}).get(side) or {}
    ).get("matches") or []
    team_id = ((match.get(f"{side}_team") or {}).get("id"))
    return {
        "points_per_game": float(
            standing.get("points_per_game", default_map["points_per_game"])
        ),
        "goal_difference_per_game": float(
            standing.get(
                "goal_difference_per_game",
                default_map["goal_difference_per_game"],
            )
        ),
        "position": float(
            standing.get("position", default_map["position"])
        ),
        "elo": elo_at(model, team_id, timestamp),
        "rest_days": rest_days(rows, timestamp, default_map["rest_days"]),
        "matches_played": float(
            standing.get("matches", len(rows))
            if standing
            else len(rows)
        ),
    }


def _lineup_summary_from_analysis(
    analysis: Dict[str, Any], side: str
) -> Dict[str, Any]:
    lineups = (analysis or {}).get("lineups")
    starters = normalize.lineup_starters(lineups, side)
    market = []
    ratings = []
    for player in starters:
        value = player.get("market_value")
        if isinstance(value, (int, float)) and value > 0:
            market.append(float(value))
        rating = player.get("avg_rating")
        if isinstance(rating, (int, float)):
            ratings.append(float(rating))
    missing = ((lineups or {}).get(side) or {}).get("missing_players") or []
    missing_values = [
        float(item["market_value"])
        for item in missing
        if isinstance(item.get("market_value"), (int, float))
    ]
    status = normalize.lineup_status(lineups)
    confidence = 1.0 if status == "confirmada" else (0.8 if status == "probable" else 0.0)
    minimum = max(5, int(len(starters) * 0.6))
    return {
        "starters": len(starters),
        "market_value": sum(market) if len(market) >= minimum else 0.0,
        "avg_rating": (
            sum(ratings) / len(ratings)
            if len(ratings) >= minimum
            else 0.0
        ),
        "missing_count": len(missing),
        "missing_market_value": sum(missing_values) if missing_values else 0.0,
        "confidence": confidence,
    }


def features_from_analysis(
    analysis: Dict[str, Any], model: Dict[str, Any]
) -> np.ndarray:
    teams = (analysis or {}).get("teams") or {}
    home_rows = (teams.get("home") or {}).get("matches") or []
    away_rows = (teams.get("away") or {}).get("matches") or []
    match = (analysis or {}).get("match") or {}
    return build_feature_vector(
        home_rows,
        away_rows,
        _context_from_analysis(analysis, "home", model),
        _context_from_analysis(analysis, "away", model),
        (analysis or {}).get("h2h"),
        _lineup_summary_from_analysis(analysis, "home"),
        _lineup_summary_from_analysis(analysis, "away"),
        (match.get("tournament") or {}).get("id"),
    )


def _forward(
    features: np.ndarray,
    weights: Sequence[np.ndarray],
    biases: Sequence[np.ndarray],
) -> np.ndarray:
    hidden = features
    for index, (weight, bias) in enumerate(zip(weights, biases)):
        hidden = hidden @ weight + bias
        if index < len(weights) - 1:
            np.maximum(hidden, 0.0, out=hidden)
    return hidden


def predict_rates(analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Predice las medias del partido. Devuelve ``None`` si no hay modelo."""
    if not (analysis or {}).get("use_neural", True):
        return None
    model = _load_model()
    if model is None:
        return None
    features = features_from_analysis(analysis, model)
    mean = model["feature_mean"]
    std = model["feature_std"]
    normalized = (features - mean) / np.maximum(std, 1e-6)
    logits = []
    for weights, biases in zip(model["weights"], model["biases"]):
        logits.append(_forward(normalized, weights, biases))
    combined = np.mean(np.stack(logits, axis=0), axis=0)
    rates = np.exp(np.clip(combined, -6.0, 3.0))
    target_index = {
        name: index for index, name in enumerate(model["target_names"])
    }

    def value(name: str) -> float:
        return float(rates[target_index[name]])

    totals: Dict[str, Dict[str, float]] = {}
    for key in METRIC_KEYS:
        totals[key] = {
            "home": value(f"home_{key}"),
            "away": value(f"away_{key}"),
        }
    # Los límites evitan que una predicción aislada domine al modelo.
    limits = {
        "goals": (0.10, 5.0),
        "shots": (2.0, 35.0),
        "shots_on_target": (0.5, 15.0),
        "corners": (0.0, 20.0),
        "cards": (0.0, 10.0),
        "fouls": (2.0, 30.0),
    }
    for key, (low, high) in limits.items():
        for side in ("home", "away"):
            totals[key][side] = max(low, min(high, totals[key][side]))

    blend_weights = {
        key: {
            "home": float(
                model["blend_weights"][target_index[f"home_{key}"]]
            ),
            "away": float(
                model["blend_weights"][target_index[f"away_{key}"]]
            ),
        }
        for key in METRIC_KEYS
    }
    return {
        "applied": True,
        "model_version": model["version"],
        "rates": totals,
        "blend_weights": blend_weights,
        "metrics": model["metrics"],
    }
