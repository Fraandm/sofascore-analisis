"""Simulación Monte Carlo de las estadísticas de un partido.

El modelo parte del análisis de forma de :mod:`sofascore.form` y genera
miles de partidos hipotéticos con NumPy. No intenta adivinar un resultado
exacto: estima distribuciones y probabilidades.

Idea del modelo
---------------
* Los goles se generan a partir de los remates: remates totales →
  remates al arco → goles. Así se cumple siempre
  ``goles <= remates al arco <= remates``.
* Las paradas se derivan: las paradas de un equipo son los remates al
  arco del rival que no acabaron en gol.
* Los remates, córners, faltas y tarjetas usan una binomial negativa
  (permite sobredispersión). Un factor latente compartido introduce
  correlación entre métricas del mismo partido.
* Las medias se ponderan por recencia y se contraen hacia una referencia
  común para reducir el ruido de muestras pequeñas.

Todo se calcula en CPU con NumPy vectorizado.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from . import neural, normalize
from .exceptions import SofaScoreError

DEFAULT_ITERATIONS = 50_000
MIN_ITERATIONS = 1_000
MAX_ITERATIONS = 500_000

FALLBACK = {
    "goals": 1.35,
    "shots": 11.5,
    "shots_on_target_p": 0.33,
    "corners": 5.0,
    "cards": 2.2,
    "fouls": 11.5,
}

STAT_KEYS = ("shots", "corners", "cards", "fouls")

EXPECTED_ROWS = (
    ("goals_for", "Goles a favor"),
    ("goals_against", "Goles en contra"),
    ("corners", "Córners"),
    ("cards", "Tarjetas"),
    ("shots", "Remates"),
    ("shots_on_target", "Remates al arco"),
    ("fouls", "Faltas"),
    ("saves", "Paradas"),
)

OVER_UNDER_LINES = {
    "goals": (1.5, 2.5, 3.5),
    "corners": (8.5, 9.5, 10.5),
    "cards": (3.5, 4.5, 5.5),
    "shots": (20.5, 24.5, 28.5),
    "shots_on_target": (7.5, 8.5, 9.5),
    "fouls": (20.5, 24.5, 28.5),
    "saves": (5.5, 7.5, 9.5),
}

TEAM_SAVE_LINES = (1.5, 2.5, 3.5)

OVER_UNDER_LABELS = {
    "goals": "Goles",
    "corners": "Córners",
    "cards": "Tarjetas",
    "shots": "Remates",
    "shots_on_target": "Remates al arco",
    "fouls": "Faltas",
    "saves": "Paradas",
}


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _weights(rows: Sequence[Dict[str, Any]], half_life: float = 6.0) -> List[float]:
    """Pesos exponenciales: el partido más reciente pesa más."""
    return [0.5 ** (index / half_life) for index in range(len(rows))]


def _values_and_weights(
    rows: Sequence[Dict[str, Any]],
    weights: Sequence[float],
    key: str,
    venue: Optional[bool] = None,
) -> Tuple[List[float], List[float]]:
    values: List[float] = []
    used_weights: List[float] = []
    for row, weight in zip(rows, weights):
        value = row.get(key)
        if value is None:
            continue
        if venue is not None and bool(row.get("home")) != venue:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            values.append(number)
            used_weights.append(weight)
    return values, used_weights


def _aggregate(
    rows: Sequence[Dict[str, Any]],
    weights: Sequence[float],
    key: str,
    venue: Optional[bool] = None,
) -> Optional[Dict[str, float]]:
    values, used = _values_and_weights(rows, weights, key, venue=venue)
    if not values:
        return None
    total_weight = sum(used)
    mean = sum(v * w for v, w in zip(values, used)) / total_weight
    variance = sum(w * (v - mean) ** 2 for v, w in zip(values, used)) / total_weight
    return {
        "mean": mean,
        "variance": variance,
        "n": float(len(values)),
        "weight": total_weight,
    }


def _baseline(
    pairs: Sequence[Tuple[Sequence[Dict[str, Any]], Sequence[float]]],
    key: str,
    fallback: float,
) -> float:
    values: List[float] = []
    weights: List[float] = []
    for rows, row_weights in pairs:
        batch_values, batch_weights = _values_and_weights(rows, row_weights, key)
        values.extend(batch_values)
        weights.extend(batch_weights)
    if not values:
        return fallback
    total = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / total


def _venue_mean(
    rows: Sequence[Dict[str, Any]],
    weights: Sequence[float],
    key: str,
    venue: bool,
    minimum: int = 2,
) -> Optional[Dict[str, float]]:
    split = _aggregate(rows, weights, key, venue=venue)
    if split is None or split["n"] < minimum:
        return None
    return split


def _estimate_count(
    rows: Sequence[Dict[str, Any]],
    weights: Sequence[float],
    key: str,
    venue: bool,
    baseline: float,
    prior_matches: float = 2.5,
) -> Tuple[float, Dict[str, float]]:
    overall = _aggregate(rows, weights, key)
    if overall is None:
        return baseline, {"mean": baseline, "variance": baseline, "n": 0.0, "weight": 0.0}
    split = _venue_mean(rows, weights, key, venue)
    if split is not None:
        value = 0.65 * split["mean"] + 0.35 * overall["mean"]
        effective = split["n"] + 0.5 * overall["n"]
        variance = 0.65 * split["variance"] + 0.35 * overall["variance"]
    else:
        value = overall["mean"]
        effective = overall["n"]
        variance = overall["variance"]
    value = (effective * value + prior_matches * baseline) / (effective + prior_matches)
    return _clip(value, 0.05, 60.0), {
        "mean": value,
        "variance": variance,
        "n": overall["n"],
        "weight": overall["weight"],
    }


def _estimate_blended_count(
    rows: Sequence[Dict[str, Any]],
    weights: Sequence[float],
    key: str,
    opponent_rows: Sequence[Dict[str, Any]],
    opponent_weights: Sequence[float],
    opponent_key: str,
    venue: bool,
    baseline: float,
    default_dispersion: float,
    own_weight: float = 0.58,
) -> Tuple[float, float, Dict[str, Any]]:
    """Combina la producción propia con lo que concede el rival.

    Para remates, córners, tarjetas y faltas el rival no solo defiende:
    también marca el ritmo y la agresividad del partido. Se mezcla la tasa
    propia con la tasa concedida por el adversario en su misma condición.
    """
    own_mean, own_meta = _estimate_count(
        rows, weights, key, venue, baseline
    )
    opponent_mean, opponent_meta = _estimate_count(
        opponent_rows,
        opponent_weights,
        opponent_key,
        not venue,
        baseline,
    )
    opponent_n = float(opponent_meta.get("n") or 0.0)
    if opponent_n <= 0:
        dispersion = _dispersion(own_meta, default_dispersion)
        return own_mean, dispersion, {
            "own": round(own_mean, 3),
            "opponent": None,
            "own_n": int(own_meta.get("n") or 0),
            "opponent_n": 0,
        }

    mean = own_weight * own_mean + (1.0 - own_weight) * opponent_mean
    dispersion = 0.5 * _dispersion(own_meta, default_dispersion) + 0.5 * _dispersion(
        opponent_meta, default_dispersion
    )
    return mean, dispersion, {
        "own": round(own_mean, 3),
        "opponent": round(opponent_mean, 3),
        "own_n": int(own_meta.get("n") or 0),
        "opponent_n": int(opponent_n),
    }


def _blend_xg(
    goals_value: Optional[float],
    xg_value: Optional[float],
    xg_weight: float,
    fallback: float,
) -> float:
    """Mezcla goles reales y xG; si falta xG usa los goles."""
    if goals_value is not None and xg_value is not None:
        return xg_weight * xg_value + (1.0 - xg_weight) * goals_value
    if goals_value is not None:
        return goals_value
    if xg_value is not None:
        return xg_value
    return fallback


def _best_mean(
    rows: Sequence[Dict[str, Any]],
    weights: Sequence[float],
    key: str,
    venue: bool,
) -> Tuple[Optional[float], float]:
    split = _venue_mean(rows, weights, key, venue)
    if split is not None:
        return split["mean"], split["n"]
    overall = _aggregate(rows, weights, key)
    if overall is not None:
        return overall["mean"], overall["n"]
    return None, 0.0


def _estimate_goals(
    rows: Sequence[Dict[str, Any]],
    weights: Sequence[float],
    opponent_rows: Sequence[Dict[str, Any]],
    opponent_weights: Sequence[float],
    venue: bool,
    baseline: float,
) -> Tuple[float, Dict[str, Any]]:
    """Goles esperados combinando goles, xG, ataque propio y defensa rival."""
    own_goals, own_goals_n = _best_mean(rows, weights, "goals_for", venue)
    own_xg, own_xg_n = _best_mean(rows, weights, "xg_for", venue)
    opponent_goals, opponent_goals_n = _best_mean(
        opponent_rows, opponent_weights, "goals_against", not venue
    )
    opponent_xg, opponent_xg_n = _best_mean(
        opponent_rows, opponent_weights, "xg_against", not venue
    )

    attack = _blend_xg(own_goals, own_xg, 0.55, baseline)
    defence = _blend_xg(
        opponent_goals, opponent_xg, 0.55, baseline
    )
    value = 0.62 * attack + 0.38 * defence

    effective = 2.0
    effective += max(own_goals_n, own_xg_n)
    effective += max(opponent_goals_n, opponent_xg_n)

    value = (effective * value + 2.0 * baseline) / (effective + 2.0)
    value = _clip(value, 0.15, 5.5)
    return value, {
        "attack": round(attack, 3),
        "attack_goals": (
            round(own_goals, 3) if own_goals is not None else None
        ),
        "attack_xg": round(own_xg, 3) if own_xg is not None else None,
        "opponent_defence": round(defence, 3),
        "opponent_goals_against": (
            round(opponent_goals, 3)
            if opponent_goals is not None
            else None
        ),
        "opponent_xg_against": (
            round(opponent_xg, 3) if opponent_xg is not None else None
        ),
        "n": round(effective, 1),
        "venue": "casa" if venue else "fuera",
        "blend": (
            "xG + goles"
            if own_xg is not None or opponent_xg is not None
            else "goles"
        ),
    }


def _estimate_target_probability(
    rows: Sequence[Dict[str, Any]],
    weights: Sequence[float],
    prior_shots: float = 8.0,
    shots_key: str = "shots",
    target_key: str = "shots_on_target",
    fallback: Optional[float] = FALLBACK["shots_on_target_p"],
) -> Optional[float]:
    shots = 0.0
    on_target = 0.0
    for row, weight in zip(rows, weights):
        shot_value = row.get(shots_key)
        target_value = row.get(target_key)
        if shot_value is None or target_value is None:
            continue
        try:
            shots += float(shot_value) * weight
            on_target += float(target_value) * weight
        except (TypeError, ValueError):
            continue
    if shots <= 0:
        return fallback
    probability = (on_target + FALLBACK["shots_on_target_p"] * prior_shots) / (
        shots + prior_shots
    )
    return _clip(probability, 0.15, 0.65)


def _dispersion(aggregate: Optional[Dict[str, float]], default: float) -> float:
    """Parámetro ``r`` de la binomial negativa (mayor r = más Poisson)."""
    if aggregate is None or aggregate["mean"] <= 0:
        return default
    mean = aggregate["mean"]
    variance = aggregate["variance"]
    n = max(1.0, aggregate["n"])
    if variance <= mean * 1.02:
        raw = 45.0
    else:
        raw = mean * mean / (variance - mean)
    # Contracción hacia un valor razonable para muestras pequeñas.
    shrunk = (raw * n + default * 4.0) / (n + 4.0)
    return _clip(shrunk, 2.0, 60.0)


def _ratio(value: Any, baseline: Any, minimum: float) -> float:
    try:
        number = float(value)
        base = float(baseline)
    except (TypeError, ValueError):
        return 1.0
    if number <= 0 or base <= 0:
        return 1.0
    return number / max(minimum, base)


def _lineup_side_summary(
    lineups: Optional[Dict[str, Any]], side: str
) -> Dict[str, Any]:
    """Agrega la calidad y la producción esperada de los titulares."""
    data = (lineups or {}).get(side) or {}
    starters = normalize.lineup_starters(lineups, side)
    ratings = [
        float(player["avg_rating"])
        for player in starters
        if isinstance(player.get("avg_rating"), (int, float))
    ]
    seasons = [
        player["season"]
        for player in starters
        if isinstance(player.get("season"), dict)
    ]

    def total(key: str) -> Optional[float]:
        if not seasons:
            return None
        values = [
            float(season.get(key) or 0.0)
            for season in seasons
            if season.get(key) is not None
        ]
        return sum(values) if values else None

    goalkeeper = None
    for player in starters:
        position = str(player.get("position") or "").upper()
        if position.startswith("G") and isinstance(player.get("season"), dict):
            goalkeeper = player["season"]
            break

    return {
        "formation": data.get("formation"),
        "starters": len(starters),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "expected_goals": (
            round(total("expected_goals") or 0.0, 3)
            if total("expected_goals") is not None
            else None
        ),
        "shots_per_game": (
            round(total("shots_per_game") or 0.0, 2)
            if total("shots_per_game") is not None
            else None
        ),
        "shots_on_target_per_game": (
            round(total("shots_on_target_per_game") or 0.0, 2)
            if total("shots_on_target_per_game") is not None
            else None
        ),
        "defensive_contributions_per_game": (
            round(total("defensive_contributions_per_game") or 0.0, 2)
            if total("defensive_contributions_per_game") is not None
            else None
        ),
        "goalkeeper_goals_prevented": (
            float(goalkeeper.get("goals_prevented"))
            if goalkeeper and goalkeeper.get("goals_prevented") is not None
            else None
        ),
        "has_season_stats": bool(seasons),
        "missing": data.get("missing_players") or [],
    }


def _apply_lineup_adjustments(
    model: Dict[str, Any], analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Ajusta goles, remates y precisión con la alineación del partido.

    Una alineación confirmada pesa al 100 %; una probable, al 45 %, porque
    todavía puede cambiar. El ajuste se limita para no dominar al modelo
    histórico.
    """
    lineups = (analysis or {}).get("lineups") or {}
    status = normalize.lineup_status(lineups)
    weight = 1.0 if status == "confirmada" else (0.45 if status == "probable" else 0.0)
    info: Dict[str, Any] = {
        "status": status,
        "applied": False,
        "weight": weight,
        "home": {},
        "away": {},
    }
    factors: Dict[str, Dict[str, float]] = {}

    for side in ("home", "away"):
        summary = _lineup_side_summary(lineups, side)
        block = model[side]
        factor = {
            "attack_factor": 1.0,
            "shots_factor": 1.0,
            "target_factor": 1.0,
            "goalkeeper_factor": 1.0,
        }
        if weight > 0 and summary["starters"] > 0:
            if summary["has_season_stats"]:
                goals_ratio = _ratio(
                    summary["expected_goals"], block["goals"], 0.4
                )
                shots_ratio = _ratio(
                    summary["shots_per_game"], block["shots"], 4.0
                )
                target_ratio = _ratio(
                    summary["shots_on_target_per_game"],
                    block["expected_shots_on_target"],
                    1.0,
                )
                combined = (
                    0.60 * goals_ratio
                    + 0.25 * shots_ratio
                    + 0.15 * target_ratio
                )
                attack_base = _clip(1.0 + 0.35 * (combined - 1.0), 0.93, 1.07)
                shots_base = _clip(
                    1.0 + 0.20 * (shots_ratio - 1.0), 0.93, 1.07
                )
                target_base = _clip(
                    1.0 + 0.20 * (target_ratio - 1.0), 0.95, 1.05
                )
            elif summary["avg_rating"] is not None:
                rating_delta = float(summary["avg_rating"]) - 6.8
                attack_base = _clip(1.0 + 0.02 * rating_delta, 0.97, 1.03)
                shots_base = 1.0
                target_base = 1.0
            else:
                attack_base = shots_base = target_base = 1.0

            factor["attack_factor"] = round(
                1.0 + (attack_base - 1.0) * weight, 4
            )
            factor["shots_factor"] = round(
                1.0 + (shots_base - 1.0) * weight, 4
            )
            factor["target_factor"] = round(
                1.0 + (target_base - 1.0) * weight, 4
            )

            if summary["goalkeeper_goals_prevented"] is not None:
                goalkeeper_base = _clip(
                    1.0 - 0.015 * summary["goalkeeper_goals_prevented"],
                    0.97,
                    1.03,
                )
                factor["goalkeeper_factor"] = round(
                    1.0 + (goalkeeper_base - 1.0) * weight, 4
                )

            block["goals"] = float(block["goals"]) * factor["attack_factor"]
            block["shots"] = float(block["shots"]) * factor["shots_factor"]
            block["shots_on_target_p"] = _clip(
                float(block["shots_on_target_p"]) * factor["target_factor"],
                0.15,
                0.65,
            )

        factors[side] = factor
        info[side] = {**summary, **factor}

    # Un portero que evita goles reduce los goles del rival y viceversa.
    model["away"]["goals"] = (
        float(model["away"]["goals"]) * factors["home"]["goalkeeper_factor"]
    )
    model["home"]["goals"] = (
        float(model["home"]["goals"]) * factors["away"]["goalkeeper_factor"]
    )

    for side in ("home", "away"):
        block = model[side]
        block["expected_shots_on_target"] = (
            float(block["shots"]) * float(block["shots_on_target_p"])
        )
        block["conversion"] = _clip(
            float(block["goals"])
            / max(0.05, block["expected_shots_on_target"]),
            0.04,
            0.65,
        )

    info["applied"] = any(
        abs(value - 1.0) > 0.0001
        for factor in factors.values()
        for value in factor.values()
    )
    if status == "probable" and info["applied"]:
        info["note"] = "La alineación es probable; el ajuste se aplica al 45 %."
    elif status == "probable":
        info["note"] = (
            "Alineación probable sin estadísticas suficientes; no se aplicó ajuste."
        )
    elif status == "confirmada" and info["applied"]:
        info["note"] = "Alineación confirmada aplicada al modelo."
    elif status == "confirmada":
        info["note"] = (
            "Alineación confirmada, pero sin estadísticas de temporada para "
            "ajustar el modelo."
        )
    return info


def _apply_referee_adjustments(
    model: Dict[str, Any], analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Ajusta tarjetas y faltas con las tendencias del árbitro."""
    referee = (analysis or {}).get("referee") or {}
    info: Dict[str, Any] = {
        "id": referee.get("id"),
        "name": referee.get("name"),
        "cards_per_match": referee.get("cards_per_match"),
        "fouls_per_match": referee.get("fouls_per_match"),
        "sample_matches": (referee.get("sample") or {}).get("matches"),
        "source": referee.get("source"),
        "cards_factor": 1.0,
        "fouls_factor": 1.0,
        "applied": False,
    }
    if not referee:
        return info

    base_cards = float(model["home"]["cards"]) + float(model["away"]["cards"])
    base_fouls = float(model["home"]["fouls"]) + float(model["away"]["fouls"])
    cards_per_match = referee.get("cards_per_match")
    fouls_per_match = referee.get("fouls_per_match")

    if cards_per_match is not None and base_cards > 0:
        factor = _clip(float(cards_per_match) / base_cards, 0.85, 1.25)
        info["cards_factor"] = round(factor, 4)
        model["home"]["cards"] = float(model["home"]["cards"]) * factor
        model["away"]["cards"] = float(model["away"]["cards"]) * factor

    if fouls_per_match is not None and base_fouls > 0:
        factor = _clip(float(fouls_per_match) / base_fouls, 0.85, 1.20)
        info["fouls_factor"] = round(factor, 4)
        model["home"]["fouls"] = float(model["home"]["fouls"]) * factor
        model["away"]["fouls"] = float(model["away"]["fouls"]) * factor

    info["applied"] = (
        abs(info["cards_factor"] - 1.0) > 0.0001
        or abs(info["fouls_factor"] - 1.0) > 0.0001
    )
    return info


def _apply_context_adjustments(
    model: Dict[str, Any], analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Ajusta el partido con fuerza de plantilla, clasificación y H2H.

    Es un prior contextual, no una sustitución del modelo de forma. El
    valor de mercado de los titulares captura la diferencia de calidad;
    la clasificación aporta el rendimiento en la competición y el H2H
    corrige rivalidades históricas. Los factores están limitados para que
    el contexto no produzca resultados extremos.
    """
    lineups = (analysis or {}).get("lineups")
    status = normalize.lineup_status(lineups)
    lineup_confidence = 1.0 if status == "confirmada" else (0.8 if status == "probable" else 0.0)

    def side_values(side: str) -> Dict[str, Optional[float]]:
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
        minimum = max(5, int(len(starters) * 0.6))
        return {
            "market": sum(market) if len(market) >= minimum else None,
            "rating": (
                sum(ratings) / len(ratings)
                if len(ratings) >= minimum
                else None
            ),
        }

    home_values = side_values("home")
    away_values = side_values("away")
    components: Dict[str, Dict[str, float]] = {}

    if (
        home_values["market"] is not None
        and away_values["market"] is not None
        and lineup_confidence > 0
    ):
        market_diff = _clip(
            math.log(home_values["market"] / away_values["market"]),
            -3.0,
            3.0,
        )
        components["market"] = {
            "value": market_diff,
            "weight": 0.60,
            "confidence": lineup_confidence,
        }

    if (
        home_values["rating"] is not None
        and away_values["rating"] is not None
        and lineup_confidence > 0
    ):
        components["rating"] = {
            "value": _clip(
                home_values["rating"] - away_values["rating"], -1.0, 1.0
            ),
            "weight": 0.05,
            "confidence": lineup_confidence,
        }

    standings = (analysis or {}).get("standings") or {}
    h2h = (analysis or {}).get("h2h") or {}
    neural_applied = bool((model.get("neural") or {}).get("applied"))
    if not neural_applied:
        home_standing = standings.get("home") or {}
        away_standing = standings.get("away") or {}
        home_ppg = home_standing.get("points_per_game")
        away_ppg = away_standing.get("points_per_game")
        home_gdpg = home_standing.get("goal_difference_per_game")
        away_gdpg = away_standing.get("goal_difference_per_game")
        if home_ppg is not None and away_ppg is not None:
            ppg_diff = (float(home_ppg) - float(away_ppg)) / max(
                0.75, (float(home_ppg) + float(away_ppg)) / 2.0
            )
            gd_diff = (
                (float(home_gdpg) - float(away_gdpg)) / 2.0
                if home_gdpg is not None and away_gdpg is not None
                else 0.0
            )
            matches = min(
                int(home_standing.get("matches") or 0),
                int(away_standing.get("matches") or 0),
            )
            components["standings"] = {
                "value": 0.6 * _clip(ppg_diff, -2.0, 2.0)
                + 0.4 * _clip(gd_diff, -2.0, 2.0),
                "weight": 0.25,
                "confidence": min(1.0, matches / 5.0) if matches else 0.0,
            }

        total_h2h = int(h2h.get("matches") or 0)
        if total_h2h > 0:
            home_wins = int(h2h.get("home_wins") or 0)
            away_wins = int(h2h.get("away_wins") or 0)
            draws = int(h2h.get("draws") or 0)
            home_share = (home_wins + 0.5 * draws) / total_h2h
            away_share = (away_wins + 0.5 * draws) / total_h2h
            components["h2h"] = {
                "value": (home_share - away_share) * 2.0,
                "weight": 0.10,
                "confidence": min(1.0, total_h2h / 6.0),
            }

    total_weight = sum(
        item["weight"] * item["confidence"] for item in components.values()
    )
    if total_weight <= 0:
        return {
            "applied": False,
            "context_diff": 0.0,
            "goal_factor_home": 1.0,
            "goal_factor_away": 1.0,
            "shots_factor_home": 1.0,
            "shots_factor_away": 1.0,
            "components": {},
        }

    context_diff = sum(
        item["value"] * item["weight"] * item["confidence"]
        for item in components.values()
    ) / total_weight
    context_diff = _clip(context_diff, -2.5, 2.5)

    goal_home = _clip(math.exp(0.22 * context_diff), 0.70, 1.30)
    goal_away = _clip(math.exp(-0.22 * context_diff), 0.70, 1.30)
    shots_home = _clip(math.exp(0.10 * context_diff), 0.88, 1.12)
    shots_away = _clip(math.exp(-0.10 * context_diff), 0.88, 1.12)

    model["home"]["goals"] = float(model["home"]["goals"]) * goal_home
    model["away"]["goals"] = float(model["away"]["goals"]) * goal_away
    model["home"]["shots"] = float(model["home"]["shots"]) * shots_home
    model["away"]["shots"] = float(model["away"]["shots"]) * shots_away
    model["home"]["corners"] = float(model["home"]["corners"]) * shots_home
    model["away"]["corners"] = float(model["away"]["corners"]) * shots_away

    for side in ("home", "away"):
        block = model[side]
        block["expected_shots_on_target"] = (
            float(block["shots"]) * float(block["shots_on_target_p"])
        )
        block["conversion"] = _clip(
            float(block["goals"])
            / max(0.05, block["expected_shots_on_target"]),
            0.04,
            0.65,
        )

    return {
        "applied": True,
        "context_diff": round(context_diff, 3),
        "goal_factor_home": round(goal_home, 3),
        "goal_factor_away": round(goal_away, 3),
        "shots_factor_home": round(shots_home, 3),
        "shots_factor_away": round(shots_away, 3),
        "components": {
            name: {
                "value": round(item["value"], 3),
                "weight": item["weight"],
                "confidence": round(item["confidence"], 3),
            }
            for name, item in components.items()
        },
        "market_value_home": home_values["market"],
        "market_value_away": away_values["market"],
        "rating_home": home_values["rating"],
        "rating_away": away_values["rating"],
        "standings": standings or None,
        "h2h": h2h or None,
    }


def build_model(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Estima los parámetros del partido a partir del análisis de forma."""
    teams = (analysis or {}).get("teams") or {}
    home_block = teams.get("home") or {}
    away_block = teams.get("away") or {}
    home_rows = list(home_block.get("matches") or [])
    away_rows = list(away_block.get("matches") or [])
    if not home_rows or not away_rows:
        raise SofaScoreError(
            "No hay partidos suficientes para simular. Analiza primero el partido."
        )

    home_weights = _weights(home_rows)
    away_weights = _weights(away_rows)
    pairs = ((home_rows, home_weights), (away_rows, away_weights))

    baselines = {
        key: _baseline(pairs, key, fallback)
        for key, fallback in (
            ("goals_for", FALLBACK["goals"]),
            ("corners", FALLBACK["corners"]),
            ("cards", FALLBACK["cards"]),
            ("shots", FALLBACK["shots"]),
            ("fouls", FALLBACK["fouls"]),
        )
    }

    home_goals, home_goals_meta = _estimate_goals(
        home_rows, home_weights, away_rows, away_weights, True, baselines["goals_for"]
    )
    away_goals, away_goals_meta = _estimate_goals(
        away_rows, away_weights, home_rows, home_weights, False, baselines["goals_for"]
    )

    model: Dict[str, Any] = {
        "home": {
            "name": (home_block.get("team") or {}).get("name") or "Local",
            "sample_size": len(home_rows),
            "stats_sample_size": home_block.get("stats_sample_size", 0),
            "goals": home_goals,
            "goals_meta": home_goals_meta,
        },
        "away": {
            "name": (away_block.get("team") or {}).get("name") or "Visitante",
            "sample_size": len(away_rows),
            "stats_sample_size": away_block.get("stats_sample_size", 0),
            "goals": away_goals,
            "goals_meta": away_goals_meta,
        },
        "baselines": {key: round(value, 3) for key, value in baselines.items()},
        "warnings": [],
    }

    for side, rows, weights, venue in (
        ("home", home_rows, home_weights, True),
        ("away", away_rows, away_weights, False),
    ):
        block = model[side]
        block["blend"] = {}
        opponent_rows = away_rows if side == "home" else home_rows
        opponent_weights = away_weights if side == "home" else home_weights
        for key, opponent_key, default_dispersion in (
            ("shots", "shots_against", 12.0),
            ("corners", "corners_against", 8.0),
            ("cards", "cards_against", 5.0),
            ("fouls", "fouls_against", 10.0),
        ):
            mean, dispersion, blend = _estimate_blended_count(
                rows,
                weights,
                key,
                opponent_rows,
                opponent_weights,
                opponent_key,
                venue,
                baselines[key],
                default_dispersion,
            )
            block[key] = mean
            block.setdefault("dispersion", {})[key] = dispersion
            block["blend"][key] = blend
            if blend["own_n"] < 3:
                model["warnings"].append(
                    f"{block['name']}: solo {blend['own_n']} partido(s) con "
                    f"datos de {key}; la estimación se apoya en la referencia."
                )

        own_target_p = _estimate_target_probability(rows, weights)
        opponent_target_p = _estimate_target_probability(
            opponent_rows,
            opponent_weights,
            shots_key="shots_against",
            target_key="shots_on_target_against",
            fallback=None,
        )
        if opponent_target_p is None:
            target_p = own_target_p
        else:
            target_p = 0.65 * own_target_p + 0.35 * opponent_target_p
        block["shots_on_target_p"] = _clip(target_p, 0.15, 0.65)
        block["blend"]["shots_on_target_p"] = {
            "own": round(own_target_p, 4),
            "opponent": (
                round(opponent_target_p, 4)
                if opponent_target_p is not None
                else None
            ),
        }
        expected_targets = block["shots"] * block["shots_on_target_p"]
        block["conversion"] = _clip(
            block["goals"] / expected_targets if expected_targets > 0 else 0.3,
            0.04,
            0.65,
        )
        block["expected_shots_on_target"] = expected_targets

    neural_info = neural.predict_rates(analysis)
    if neural_info:
        for side in ("home", "away"):
            block = model[side]
            rates = neural_info["rates"]
            weights = neural_info["blend_weights"]
            for key in ("goals", "shots", "corners", "cards", "fouls"):
                weight = float(weights[key][side])
                block[key] = (
                    (1.0 - weight) * float(block[key])
                    + weight * float(rates[key][side])
                )
            target_weight = float(weights["shots_on_target"][side])
            predicted_probability = _clip(
                float(rates["shots_on_target"][side])
                / max(0.1, float(rates["shots"][side])),
                0.15,
                0.65,
            )
            block["shots_on_target_p"] = _clip(
                (1.0 - target_weight) * float(block["shots_on_target_p"])
                + target_weight * predicted_probability,
                0.15,
                0.65,
            )
            block["expected_shots_on_target"] = (
                float(block["shots"]) * float(block["shots_on_target_p"])
            )
            block["conversion"] = _clip(
                float(block["goals"])
                / max(0.05, block["expected_shots_on_target"]),
                0.04,
                0.65,
            )
        model["neural"] = neural_info
    else:
        model["neural"] = {"applied": False}

    lineup_info = _apply_lineup_adjustments(model, analysis)
    referee_info = _apply_referee_adjustments(model, analysis)
    context_info = _apply_context_adjustments(model, analysis)
    model["lineups"] = lineup_info
    model["referee"] = referee_info
    model["context"] = context_info
    if lineup_info.get("status") == "probable":
        model["warnings"].append(
            "La alineación es probable; el ajuste por alineación se aplica al 45 %."
        )
    if (
        referee_info.get("applied")
        and (referee_info.get("sample_matches") or 0) < 3
    ):
        model["warnings"].append(
            "Árbitro: muestra pequeña de partidos; el ajuste de tarjetas y "
            "faltas es orientativo."
        )

    # Las paradas se derivan del rival: remates al arco que no son gol.
    model["home"]["expected_saves"] = max(
        0.0, model["away"]["expected_shots_on_target"] - model["away"]["goals"]
    )
    model["away"]["expected_saves"] = max(
        0.0, model["home"]["expected_shots_on_target"] - model["home"]["goals"]
    )
    model["home"]["expected_goals_against"] = model["away"]["goals"]
    model["away"]["expected_goals_against"] = model["home"]["goals"]

    for side in ("home", "away"):
        for key in ("goals", "shots", "corners", "cards", "fouls"):
            model[side][key] = round(float(model[side][key]), 3)
        model[side]["shots_on_target_p"] = round(
            float(model[side]["shots_on_target_p"]), 3
        )
        model[side]["conversion"] = round(float(model[side]["conversion"]), 3)
        model[side]["expected_shots_on_target"] = round(
            float(model[side]["expected_shots_on_target"]), 2
        )
        model[side]["expected_saves"] = round(
            float(model[side]["expected_saves"]), 2
        )
        model[side]["expected_goals_against"] = round(
            float(model[side]["expected_goals_against"]), 2
        )

    return model


def _negative_binomial(
    rng: np.random.Generator,
    mean: float,
    dispersion: float,
    factor: np.ndarray,
) -> np.ndarray:
    mu = np.maximum(mean * factor, 1e-6)
    probability = dispersion / (dispersion + mu)
    return rng.negative_binomial(dispersion, probability)


def _beta_binomial(
    rng: np.random.Generator,
    trials: np.ndarray,
    probability: float,
    concentration: float,
) -> np.ndarray:
    p = _clip(probability, 0.01, 0.99)
    alpha = max(0.2, p * concentration)
    beta = max(0.2, (1.0 - p) * concentration)
    draw = rng.beta(alpha, beta, size=trials.shape[0])
    return rng.binomial(trials, draw)


@dataclass
class SimulationResult:
    """Muestras y metadatos de una simulación Monte Carlo."""

    analysis: Dict[str, Any]
    model: Dict[str, Any]
    iterations: int
    seed: Optional[int]
    elapsed_seconds: float
    samples: Dict[str, np.ndarray] = field(default_factory=dict)

    def summary(self) -> Dict[str, Any]:
        return _summarize(self)


def run_simulation(
    analysis: Dict[str, Any],
    iterations: int = DEFAULT_ITERATIONS,
    seed: Optional[int] = 42,
) -> SimulationResult:
    """Ejecuta la simulación y devuelve las muestras completas."""
    try:
        count = int(iterations)
    except (TypeError, ValueError) as exc:
        raise SofaScoreError("El número de simulaciones no es válido.") from exc
    if count < MIN_ITERATIONS:
        raise SofaScoreError(
            f"Usa al menos {MIN_ITERATIONS:,} simulaciones.".replace(",", ".")
        )
    if count > MAX_ITERATIONS:
        raise SofaScoreError(
            f"El máximo es {MAX_ITERATIONS:,} simulaciones.".replace(",", ".")
        )
    if seed is not None:
        try:
            seed = int(seed)
        except (TypeError, ValueError) as exc:
            raise SofaScoreError("La semilla debe ser un número entero.") from exc

    model = build_model(analysis)
    rng = np.random.default_rng(seed)
    started = time.perf_counter()

    # Factores latentes: un partido abierto genera más remates/córners y
    # un partido intenso genera más faltas/tarjetas.
    match_tempo = rng.gamma(8.0, 1.0 / 8.0, count)
    home_tempo = rng.gamma(8.0, 1.0 / 8.0, count)
    away_tempo = rng.gamma(8.0, 1.0 / 8.0, count)
    match_intensity = rng.gamma(10.0, 1.0 / 10.0, count)
    home_intensity = rng.gamma(10.0, 1.0 / 10.0, count)
    away_intensity = rng.gamma(10.0, 1.0 / 10.0, count)

    samples: Dict[str, np.ndarray] = {}

    for side, tempo, intensity in (
        ("home", home_tempo, home_intensity),
        ("away", away_tempo, away_intensity),
    ):
        block = model[side]
        shot_factor = match_tempo * tempo
        shots = _negative_binomial(
            rng,
            block["shots"],
            block["dispersion"]["shots"],
            shot_factor,
        )
        on_target = _beta_binomial(
            rng, shots, block["shots_on_target_p"], concentration=22.0
        )
        goals = _beta_binomial(
            rng, on_target, block["conversion"], concentration=35.0
        )
        corner_factor = (match_tempo ** 0.7) * (tempo ** 0.7)
        corners = _negative_binomial(
            rng,
            block["corners"],
            block["dispersion"]["corners"],
            corner_factor,
        )
        card_factor = (match_intensity ** 0.8) * (intensity ** 0.8)
        cards = _negative_binomial(
            rng,
            block["cards"],
            block["dispersion"]["cards"],
            card_factor,
        )
        foul_factor = match_intensity * intensity
        fouls = _negative_binomial(
            rng,
            block["fouls"],
            block["dispersion"]["fouls"],
            foul_factor,
        )

        samples[f"{side}_shots"] = shots.astype(np.int32)
        samples[f"{side}_shots_on_target"] = on_target.astype(np.int32)
        samples[f"{side}_goals"] = goals.astype(np.int32)
        samples[f"{side}_corners"] = corners.astype(np.int32)
        samples[f"{side}_cards"] = cards.astype(np.int32)
        samples[f"{side}_fouls"] = fouls.astype(np.int32)

    # Coherencia: las paradas son remates al arco del rival no convertidos.
    samples["home_saves"] = np.maximum(
        samples["away_shots_on_target"] - samples["away_goals"], 0
    ).astype(np.int32)
    samples["away_saves"] = np.maximum(
        samples["home_shots_on_target"] - samples["home_goals"], 0
    ).astype(np.int32)

    samples["total_goals"] = samples["home_goals"] + samples["away_goals"]
    samples["total_shots"] = samples["home_shots"] + samples["away_shots"]
    samples["total_shots_on_target"] = (
        samples["home_shots_on_target"] + samples["away_shots_on_target"]
    )
    samples["total_corners"] = samples["home_corners"] + samples["away_corners"]
    samples["total_cards"] = samples["home_cards"] + samples["away_cards"]
    samples["total_fouls"] = samples["home_fouls"] + samples["away_fouls"]
    samples["total_saves"] = samples["home_saves"] + samples["away_saves"]

    elapsed = time.perf_counter() - started
    return SimulationResult(
        analysis=analysis,
        model=model,
        iterations=count,
        seed=seed,
        elapsed_seconds=elapsed,
        samples=samples,
    )


def _histogram_limit(
    values: np.ndarray,
    minimum: int,
    maximum: int,
    step: int = 1,
) -> int:
    """Rango del histograma basado en el percentil 99,5.

    Evita que una última barra tipo «18+» absorba una cola enorme y
    parezca un pico artificial. El mínimo mantiene una escala legible
    incluso en partidos con pocos eventos.
    """
    array = np.asarray(values)
    if array.size == 0:
        return minimum
    limit = max(float(minimum), math.ceil(float(np.percentile(array, 99.5))))
    if step > 1:
        limit = math.ceil(limit / step) * step
    return int(min(maximum, limit))


def _histogram(
    values: np.ndarray,
    max_value: int,
    step: int = 1,
) -> Dict[str, Any]:
    array = np.asarray(values, dtype=np.int64)
    clipped = np.clip(array, 0, max_value)
    bins = max_value // step + 1
    indices = np.minimum((clipped // step).astype(np.int64), bins - 1)
    counts = np.bincount(indices, minlength=bins)[:bins]
    labels: List[str] = []
    for index in range(bins):
        low = index * step
        if index == bins - 1:
            labels.append(f"{low}+")
        elif step == 1:
            labels.append(str(low))
        else:
            labels.append(f"{low}-{low + step - 1}")
    total = max(1, len(array))
    overflow_percent = round(float(counts[-1]) / total * 100.0, 2) if counts.size else 0.0
    return {
        "labels": labels,
        "counts": [int(value) for value in counts],
        "percent": [round(float(value) / total * 100.0, 2) for value in counts],
        "step": step,
        "max_value": max_value,
        "overflow_label": labels[-1] if labels else "",
        "overflow_percent": overflow_percent,
    }


def _percentiles(values: np.ndarray) -> Dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        "p10": round(float(np.percentile(array, 10)), 2),
        "p25": round(float(np.percentile(array, 25)), 2),
        "median": round(float(np.median(array)), 2),
        "p75": round(float(np.percentile(array, 75)), 2),
        "p90": round(float(np.percentile(array, 90)), 2),
        "p99": round(float(np.percentile(array, 99)), 2),
        "mean": round(float(np.mean(array)), 2),
    }


def _over_under(values: np.ndarray, lines: Iterable[float]) -> Dict[str, Any]:
    array = np.asarray(values)
    result: Dict[str, Any] = {}
    for line in lines:
        over = float(np.mean(array > line))
        result[f"{line}"] = {
            "over": round(over, 4),
            "under": round(1.0 - over, 4),
            "line": line,
        }
    return result


def _score_matrix(home_goals: np.ndarray, away_goals: np.ndarray) -> Dict[str, Any]:
    limit = 6
    home = np.clip(home_goals, 0, limit).astype(np.int64)
    away = np.clip(away_goals, 0, limit).astype(np.int64)
    matrix = np.zeros((limit + 1, limit + 1), dtype=np.int64)
    np.add.at(matrix, (home, away), 1)
    total = max(1, len(home_goals))
    return {
        "labels": [str(index) for index in range(limit)] + [f"{limit}+"],
        "probabilities": [
            [round(float(value) / total, 5) for value in row] for row in matrix
        ],
        "max_goals": limit,
    }


def _top_scorelines(
    home_goals: np.ndarray, away_goals: np.ndarray, limit: int = 8
) -> List[Dict[str, Any]]:
    pairs = np.stack([home_goals, away_goals], axis=1)
    unique, counts = np.unique(pairs, axis=0, return_counts=True)
    order = np.argsort(-counts)[:limit]
    total = max(1, len(home_goals))
    rows = []
    for index in order:
        home = int(unique[index][0])
        away = int(unique[index][1])
        rows.append(
            {
                "score": f"{home}-{away}",
                "home": home,
                "away": away,
                "probability": round(float(counts[index]) / total, 5),
            }
        )
    return rows


def _summarize(result: SimulationResult) -> Dict[str, Any]:
    samples = result.samples
    match = (result.analysis or {}).get("match") or {}
    home_model = result.model["home"]
    away_model = result.model["away"]

    def team_expected(prefix: str, opponent_prefix: str) -> Dict[str, Any]:
        return {
            "goals_for": round(float(np.mean(samples[f"{prefix}_goals"])), 2),
            "goals_against": round(float(np.mean(samples[f"{opponent_prefix}_goals"])), 2),
            "corners": round(float(np.mean(samples[f"{prefix}_corners"])), 2),
            "cards": round(float(np.mean(samples[f"{prefix}_cards"])), 2),
            "shots": round(float(np.mean(samples[f"{prefix}_shots"])), 2),
            "shots_on_target": round(
                float(np.mean(samples[f"{prefix}_shots_on_target"])), 2
            ),
            "fouls": round(float(np.mean(samples[f"{prefix}_fouls"])), 2),
            "saves": round(float(np.mean(samples[f"{prefix}_saves"])), 2),
        }

    expected_home = team_expected("home", "away")
    expected_away = team_expected("away", "home")

    totals_mean = {
        "goals": round(float(np.mean(samples["total_goals"])), 2),
        "corners": round(float(np.mean(samples["total_corners"])), 2),
        "cards": round(float(np.mean(samples["total_cards"])), 2),
        "shots": round(float(np.mean(samples["total_shots"])), 2),
        "shots_on_target": round(
            float(np.mean(samples["total_shots_on_target"])), 2
        ),
        "fouls": round(float(np.mean(samples["total_fouls"])), 2),
        "saves": round(float(np.mean(samples["total_saves"])), 2),
    }

    totals_percentiles = {
        key: _percentiles(samples[f"total_{key}"])
        for key in (
            "goals",
            "corners",
            "cards",
            "shots",
            "shots_on_target",
            "fouls",
            "saves",
        )
    }

    winner = {
        "home": round(float(np.mean(samples["home_goals"] > samples["away_goals"])), 4),
        "draw": round(float(np.mean(samples["home_goals"] == samples["away_goals"])), 4),
        "away": round(float(np.mean(samples["home_goals"] < samples["away_goals"])), 4),
    }
    btts = round(
        float(
            np.mean(
                (samples["home_goals"] > 0) & (samples["away_goals"] > 0)
            )
        ),
        4,
    )
    clean_sheets = {
        "home": round(float(np.mean(samples["away_goals"] == 0)), 4),
        "away": round(float(np.mean(samples["home_goals"] == 0)), 4),
    }

    over_under = {
        key: _over_under(samples[f"total_{key}"], lines)
        for key, lines in OVER_UNDER_LINES.items()
    }

    histograms = {
        "goals": _histogram(
            samples["total_goals"],
            _histogram_limit(samples["total_goals"], 8, 16),
        ),
        "goals_home": _histogram(
            samples["home_goals"],
            _histogram_limit(samples["home_goals"], 6, 12),
        ),
        "goals_away": _histogram(
            samples["away_goals"],
            _histogram_limit(samples["away_goals"], 6, 12),
        ),
        "corners": _histogram(
            samples["total_corners"],
            _histogram_limit(samples["total_corners"], 20, 60),
        ),
        "cards": _histogram(
            samples["total_cards"],
            _histogram_limit(samples["total_cards"], 10, 30),
        ),
        "shots": _histogram(
            samples["total_shots"],
            _histogram_limit(samples["total_shots"], 34, 80, step=2),
            step=2,
        ),
        "shots_on_target": _histogram(
            samples["total_shots_on_target"],
            _histogram_limit(
                samples["total_shots_on_target"], 16, 40, step=2
            ),
            step=2,
        ),
        "fouls": _histogram(
            samples["total_fouls"],
            _histogram_limit(samples["total_fouls"], 30, 80, step=2),
            step=2,
        ),
        "saves": _histogram(
            samples["total_saves"],
            _histogram_limit(samples["total_saves"], 12, 30),
        ),
    }

    expected_team = {
        "home": {
            "name": home_model["name"],
            "expected": expected_home,
            "over_under": {
                "saves": _over_under(
                    samples["home_saves"], TEAM_SAVE_LINES
                )
            },
            "percentiles": {
                key: _percentiles(samples[f"home_{key}"])
                for key in (
                    "goals",
                    "corners",
                    "cards",
                    "shots",
                    "shots_on_target",
                    "fouls",
                    "saves",
                )
            },
        },
        "away": {
            "name": away_model["name"],
            "expected": expected_away,
            "over_under": {
                "saves": _over_under(
                    samples["away_saves"], TEAM_SAVE_LINES
                )
            },
            "percentiles": {
                key: _percentiles(samples[f"away_{key}"])
                for key in (
                    "goals",
                    "corners",
                    "cards",
                    "shots",
                    "shots_on_target",
                    "fouls",
                    "saves",
                )
            },
        },
    }

    summary = {
        "meta": {
            "match_id": match.get("id"),
            "home_team": home_model["name"],
            "away_team": away_model["name"],
            "tournament": (match.get("tournament") or {}).get("name"),
            "start_time": match.get("start_time"),
            "window": (result.analysis or {}).get("window"),
            "season": (result.analysis or {}).get("season"),
            "iterations": result.iterations,
            "seed": result.seed,
            "elapsed_seconds": round(result.elapsed_seconds, 3),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "SofaScore · simulación Monte Carlo con NumPy",
        },
        "model": result.model,
        "teams": expected_team,
        "totals": {
            "mean": totals_mean,
            "percentiles": totals_percentiles,
        },
        "probabilities": {
            "winner": winner,
            "btts": btts,
            "clean_sheets": clean_sheets,
            "over_under": over_under,
        },
        "scorelines": _top_scorelines(
            samples["home_goals"], samples["away_goals"]
        ),
        "score_matrix": _score_matrix(
            samples["home_goals"], samples["away_goals"]
        ),
        "histograms": histograms,
    }
    actual = (result.analysis or {}).get("actual")
    if actual is not None:
        summary["actual"] = actual
    return summary


def simulate_match(
    analysis: Dict[str, Any],
    iterations: int = DEFAULT_ITERATIONS,
    seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """Atajo que devuelve directamente un resumen serializable."""
    return run_simulation(analysis, iterations=iterations, seed=seed).summary()


def summary_rows(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filas para exportar la simulación a CSV."""
    rows: List[Dict[str, Any]] = []
    teams = summary.get("teams") or {}
    home_name = (teams.get("home") or {}).get("name") or "Local"
    away_name = (teams.get("away") or {}).get("name") or "Visitante"
    home_expected = (teams.get("home") or {}).get("expected") or {}
    away_expected = (teams.get("away") or {}).get("expected") or {}
    totals = (summary.get("totals") or {}).get("mean") or {}

    for key, label in EXPECTED_ROWS:
        rows.append(
            {
                "seccion": "Esperado",
                "metrica": label,
                "local": home_expected.get(key),
                "visitante": away_expected.get(key),
                "total": None,
                "probabilidad": None,
            }
        )
    for key, value in totals.items():
        label = OVER_UNDER_LABELS.get(key, key)
        rows.append(
            {
                "seccion": "Total esperado",
                "metrica": label,
                "local": None,
                "visitante": None,
                "total": value,
                "probabilidad": None,
            }
        )

    winner = (summary.get("probabilities") or {}).get("winner") or {}
    for side, name in (("home", home_name), ("draw", "Empate"), ("away", away_name)):
        probability = winner.get(side)
        rows.append(
            {
                "seccion": "Resultado",
                "metrica": f"Gana {name}" if side != "draw" else "Empate",
                "local": None,
                "visitante": None,
                "total": None,
                "probabilidad": (
                    round(float(probability) * 100.0, 2)
                    if probability is not None
                    else None
                ),
            }
        )

    probabilities = summary.get("probabilities") or {}
    btts = probabilities.get("btts")
    rows.append(
        {
            "seccion": "Resultado",
            "metrica": "Ambos equipos marcan",
            "local": None,
            "visitante": None,
            "total": None,
            "probabilidad": round(float(btts) * 100.0, 2) if btts is not None else None,
        }
    )

    over_under = probabilities.get("over_under") or {}
    for key, lines in over_under.items():
        label = OVER_UNDER_LABELS.get(key, key)
        for line, values in lines.items():
            rows.append(
                {
                    "seccion": "Over/Under",
                    "metrica": f"{label} más de {line}",
                    "local": None,
                    "visitante": None,
                    "total": line,
                    "probabilidad": round(float(values["over"]) * 100.0, 2),
                }
            )
            rows.append(
                {
                    "seccion": "Over/Under",
                    "metrica": f"{label} menos de {line}",
                    "local": None,
                    "visitante": None,
                    "total": line,
                    "probabilidad": round(float(values["under"]) * 100.0, 2),
                }
            )

    for side, name in (("home", home_name), ("away", away_name)):
        team_lines = (
            ((teams.get(side) or {}).get("over_under") or {}).get("saves") or {}
        )
        for line, values in team_lines.items():
            rows.append(
                {
                    "seccion": "Over/Under arquero",
                    "metrica": f"Paradas {name} más de {line}",
                    "local": None,
                    "visitante": None,
                    "total": line,
                    "probabilidad": round(float(values["over"]) * 100.0, 2),
                }
            )
            rows.append(
                {
                    "seccion": "Over/Under arquero",
                    "metrica": f"Paradas {name} menos de {line}",
                    "local": None,
                    "visitante": None,
                    "total": line,
                    "probabilidad": round(float(values["under"]) * 100.0, 2),
                }
            )

    actual = summary.get("actual") or {}
    if actual:
        actual_home = actual.get("home") or {}
        actual_away = actual.get("away") or {}
        rows.append(
            {
                "seccion": "Real",
                "metrica": "Resultado",
                "local": actual_home.get("goals_for"),
                "visitante": actual_away.get("goals_for"),
                "total": None,
                "probabilidad": None,
            }
        )
        for key, label in EXPECTED_ROWS:
            rows.append(
                {
                    "seccion": "Real",
                    "metrica": label,
                    "local": actual_home.get(key),
                    "visitante": actual_away.get(key),
                    "total": None,
                    "probabilidad": None,
                }
            )

    for item in summary.get("scorelines") or []:
        rows.append(
            {
                "seccion": "Marcador",
                "metrica": item.get("score"),
                "local": item.get("home"),
                "visitante": item.get("away"),
                "total": None,
                "probabilidad": round(float(item.get("probability", 0)) * 100.0, 2),
            }
        )
    return rows
