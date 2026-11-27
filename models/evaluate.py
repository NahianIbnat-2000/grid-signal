"""Evaluation on the hand-labelled F1 set.

- Main task: 3 classes (positive / neutral / negative). Items labelled `mixed`
  or `off_topic` are excluded from the main score and counted separately.
- Uncertainty: cluster bootstrap over RACES (comments from one race are not
  independent), 2,000 resamples, percentile 95% intervals.
- Model comparison: paired cluster bootstrap of the macro-F1 difference.
- Two views: the labelled sample as drawn, and re-weighted to the collected
  population with the sampling weights.
- Subgroups: short vs long, mentions a driver/team, sarcasm, video type.
Outputs contain metrics only, never comment text.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

LABELS = ["negative", "neutral", "positive"]


def point_metrics(gold, pred, weight=None) -> dict:
    p, r, f, n = precision_recall_fscore_support(gold, pred, labels=LABELS, sample_weight=weight,
                                                 zero_division=0)
    return {
        "n": int(len(gold)),
        "accuracy": float(accuracy_score(gold, pred, sample_weight=weight)),
        "macro_f1": float(f1_score(gold, pred, labels=LABELS, average="macro", sample_weight=weight,
                                   zero_division=0)),
        "weighted_f1": float(f1_score(gold, pred, labels=LABELS, average="weighted", sample_weight=weight,
                                      zero_division=0)),
        "per_class": {lab: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i])}
                      for i, lab in enumerate(LABELS)},
        "confusion": {"labels": LABELS,
                      "matrix": confusion_matrix(gold, pred, labels=LABELS).tolist()},
    }


def _cluster_indices(clusters: np.ndarray, rng) -> np.ndarray:
    uniq = np.unique(clusters)
    pick = rng.choice(uniq, size=len(uniq), replace=True)
    by = {c: np.flatnonzero(clusters == c) for c in uniq}
    return np.concatenate([by[c] for c in pick])


def cluster_bootstrap_ci(gold, pred, clusters, weight=None, reps: int = 2000, seed: int = 0) -> tuple:
    gold, pred, clusters = map(np.asarray, (gold, pred, clusters))
    w = None if weight is None else np.asarray(weight)
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(reps):
        ix = _cluster_indices(clusters, rng)
        stats.append(f1_score(gold[ix], pred[ix], labels=LABELS, average="macro",
                              sample_weight=None if w is None else w[ix], zero_division=0))
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def paired_difference(gold, pred_a, pred_b, clusters, reps: int = 2000, seed: int = 0) -> dict:
    """macro-F1(a) - macro-F1(b), paired over the same race resamples."""
    gold, pa, pb, clusters = map(np.asarray, (gold, pred_a, pred_b, clusters))
    rng = np.random.default_rng(seed)
    d = []
    for _ in range(reps):
        ix = _cluster_indices(clusters, rng)
        d.append(f1_score(gold[ix], pa[ix], labels=LABELS, average="macro", zero_division=0)
                 - f1_score(gold[ix], pb[ix], labels=LABELS, average="macro", zero_division=0))
    d = np.asarray(d)
    obs = (f1_score(gold, pa, labels=LABELS, average="macro", zero_division=0)
           - f1_score(gold, pb, labels=LABELS, average="macro", zero_division=0))
    return {"diff": float(obs), "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            "share_resamples_a_better": float(np.mean(d > 0))}


def subgroup_table(df: pd.DataFrame, pred_col: str) -> dict:
    words = df["text_len_words"]
    groups = {
        "short (<8 words)": words < 8,
        "long (>=8 words)": words >= 8,
        "mentions driver/team": df["has_entity"],
        "no driver/team": ~df["has_entity"],
        "sarcasm=yes": df["sarcasm"] == "yes",
        "sarcasm=no": df["sarcasm"] != "yes",
        "annotator unsure": df["unsure"] == "yes",
    }
    for vt in sorted(df["video_type"].unique()):
        groups[f"video: {vt}"] = df["video_type"] == vt
    out = {}
    for name, mask in groups.items():
        sub = df[mask]
        if len(sub) == 0:
            continue
        out[name] = {"n": int(len(sub)),
                     "macro_f1": float(f1_score(sub["overall"], sub[pred_col], labels=LABELS,
                                                average="macro", zero_division=0)),
                     "accuracy": float(accuracy_score(sub["overall"], sub[pred_col]))}
    return out


def expected_calibration_error(gold, proba: np.ndarray, classes: list[str], bins: int = 10) -> float:
    gold = np.asarray(gold)
    conf = proba.max(axis=1)
    pred = np.asarray(classes)[proba.argmax(axis=1)]
    correct = pred == gold
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)
