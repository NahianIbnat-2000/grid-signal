import numpy as np
import pytest

from analysis.sentiment.quantify import LABELS, adjust, adjusted_shares_ci, confusion_rates, shares


def test_perfect_classifier_needs_no_correction():
    g = ["negative"] * 5 + ["neutral"] * 5 + ["positive"] * 5
    M = confusion_rates(g, g)
    assert np.allclose(M, np.eye(3))
    assert np.allclose(adjust(np.array([0.2, 0.3, 0.5]), M), [0.2, 0.3, 0.5])


def test_recovers_true_shares_when_negatives_leak_to_neutral():
    # model calls half of the negatives "neutral" (the pattern seen on dev)
    M = np.array([[0.5, 0.0, 0.0], [0.5, 1.0, 0.0], [0.0, 0.0, 1.0]])
    true_p = np.array([0.4, 0.2, 0.4])
    q = M @ true_p                      # observed: 0.2 neg, 0.4 neu, 0.4 pos
    assert np.allclose(adjust(q, M), true_p, atol=1e-6)


def test_ci_covers_truth_in_simulation():
    rng = np.random.default_rng(3)
    M = np.array([[0.5, 0.1, 0.1], [0.4, 0.8, 0.2], [0.1, 0.1, 0.7]])
    def simulate(true_lab):
        idx = [LABELS.index(t) for t in true_lab]
        return np.array([LABELS[rng.choice(3, p=M[:, j])] for j in idx])
    gold = rng.choice(LABELS, 600, p=[0.4, 0.2, 0.4])
    gold_pred = simulate(gold)
    grp_true = rng.choice(LABELS, 3000, p=[0.5, 0.2, 0.3])
    r = adjusted_shares_ci(simulate(grp_true), gold, gold_pred, reps=200)
    assert r["raw_negative"] < 0.35                       # raw count badly understates
    assert r["adj_negative_lo"] <= 0.5 <= r["adj_negative_hi"]
    assert abs(r["adj_negative"] - 0.5) < 0.06
