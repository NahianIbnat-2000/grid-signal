"""Corrected sentiment shares (adjusted classify-and-count).

A classifier with known error rates gives biased shares. If M[i, j] is the
probability the model predicts class i when the true class is j (estimated on
labelled comments), the predicted shares q relate to true shares p by q = M p.
We solve for p (constrained to the simplex), following Forman (2008),
"Quantifying counts and costs via classification", Data Min. Knowl. Discov.

Uncertainty: bootstrap that resamples BOTH the labelled set (M) and the
group's comments (q), so the interval reflects classifier error too.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import nnls

LABELS = ["negative", "neutral", "positive"]


def confusion_rates(gold, pred) -> np.ndarray:
    """M[i, j] = P(pred = i | true = j), columns sum to 1."""
    gold, pred = np.asarray(gold), np.asarray(pred)
    M = np.zeros((3, 3))
    for j, t in enumerate(LABELS):
        sel = pred[gold == t]
        if len(sel) == 0:
            M[j, j] = 1.0
            continue
        for i, pl in enumerate(LABELS):
            M[i, j] = np.mean(sel == pl)
    return M


def adjust(q: np.ndarray, M: np.ndarray) -> np.ndarray:
    """Least squares on the simplex: min ||M p - q|| s.t. p >= 0, sum p = 1."""
    A = np.vstack([M, 100 * np.ones((1, 3))])   # heavy row enforces sum to 1
    b = np.concatenate([q, [100.0]])
    p, _ = nnls(A, b)
    return p / p.sum()


def shares(pred) -> np.ndarray:
    pred = np.asarray(pred)
    return np.array([np.mean(pred == l) for l in LABELS]) if len(pred) else np.full(3, np.nan)


def adjusted_shares_ci(group_pred, gold, gold_pred, reps: int = 500, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    group_pred, gold, gold_pred = map(np.asarray, (group_pred, gold, gold_pred))
    point = adjust(shares(group_pred), confusion_rates(gold, gold_pred))
    boot = []
    for _ in range(reps):
        gi = rng.integers(0, len(gold), len(gold))
        qi = rng.integers(0, len(group_pred), len(group_pred))
        boot.append(adjust(shares(group_pred[qi]), confusion_rates(gold[gi], gold_pred[gi])))
    boot = np.asarray(boot)
    out = {"n": int(len(group_pred))}
    for k, lab in enumerate(LABELS):
        out[f"raw_{lab}"] = float(shares(group_pred)[k])
        out[f"adj_{lab}"] = float(point[k])
        out[f"adj_{lab}_lo"] = float(np.percentile(boot[:, k], 2.5))
        out[f"adj_{lab}_hi"] = float(np.percentile(boot[:, k], 97.5))
    return out
