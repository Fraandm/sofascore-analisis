"""Inferencia NumPy de un bosque de árboles de gradient boosting (Poisson).

Los árboles se entrenan offline con scikit-learn (``training/train_gbm.py``)
y se serializan como arrays planos para evaluarlos en tiempo de ejecución sin
añadir scikit-learn al ejecutable. Cada nodo guarda su feature, umbral,
hijos, valor de hoja y banderas de hoja/valores ausentes.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np


def _forest_raw(
    features: np.ndarray, forest: Dict[str, Any]
) -> np.ndarray:
    """Devuelve la predicción cruda (log-tasa) de un bosque para un batch."""
    x = np.asarray(features, dtype=np.float64)
    n = x.shape[0]
    out = np.full(n, float(forest["baseline"]), dtype=np.float64)
    offsets = forest["offsets"].astype(np.int64)
    feat = forest["feat"].astype(np.int64)
    thr = forest["thr"].astype(np.float64)
    left = forest["left"].astype(np.int64)
    right = forest["right"].astype(np.int64)
    missing_left = forest["missing_left"].astype(bool)
    leaf = forest["leaf"].astype(bool)
    value = forest["value"].astype(np.float64)

    for tree_index in range(int(forest["n_trees"])):
        start = int(offsets[tree_index])
        end = int(offsets[tree_index + 1])
        ftr = feat[start:end]
        thrr = thr[start:end]
        lft = left[start:end]
        rgt = right[start:end]
        msl = missing_left[start:end]
        lf = leaf[start:end]
        val = value[start:end]

        index = np.zeros(n, dtype=np.int64)
        active = np.ones(n, dtype=bool)
        while active.any():
            is_leaf = lf[index]
            out += np.where(active & is_leaf, val[index], 0.0)
            active = active & ~is_leaf
            if not active.any():
                break
            columns = ftr[index]
            xval = x[np.arange(n), columns]
            go_left = np.where(
                np.isnan(xval), msl[index], xval <= thrr[index]
            )
            index = np.where(active, np.where(go_left, lft[index], rgt[index]), index)
    return out


def predict_rates(features: np.ndarray, forest: Dict[str, Any]) -> np.ndarray:
    """Tasas (media) predichas por el bosque para un batch de features."""
    raw = _forest_raw(features, forest)
    return np.exp(np.clip(raw, -6.0, 3.0)).astype(np.float32)
