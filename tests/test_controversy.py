import numpy as np
import pytest

from analysis.polarization.controversy import bipolarity, race_draws

LAB = ["negative", "neutral", "positive"]


@pytest.mark.parametrize("p,expected", [
    ([1, 0, 0], 0.0),          # unanimous criticism: no disagreement
    ([0, 0, 1], 0.0),          # unanimous praise
    ([0, 1, 0], 0.0),          # all neutral
    ([0.5, 0, 0.5], 1.0),      # perfect split
    ([0.8, 0.2, 0.0], 0.16),   # heavily criticised: high negativity, low disagreement
])
def test_bipolarity_controlled_examples(p, expected):
    assert bipolarity(np.array(p, dtype=float)) == pytest.approx(expected)


def test_split_race_beats_criticised_race():
    assert bipolarity(np.array([0.45, 0.1, 0.45])) > bipolarity(np.array([0.85, 0.1, 0.05]))


def test_race_draws_perfect_classifier_equal_weighting():
    gold = np.array(LAB * 50)
    groups = {"a": np.array(["negative"] * 90 + ["positive"] * 10),   # big video, 90% neg
              "b": np.array(["positive"] * 10)}                        # small video, all pos
    point, draws = race_draws(groups, gold, gold, np.ones(len(gold)), reps=50)
    # equal weighting: mean of (0.9 neg) and (0 neg) = 0.45, not volume-weighted 0.82
    assert point[0] == pytest.approx(0.45)
    assert draws.shape == (50, 3)


def test_per_type_error_rates_are_used():
    rng = np.random.default_rng(1)
    # type A: perfect model; type B: model calls every negative "neutral"
    gA = rng.choice(LAB, 300); pA = gA.copy()
    gB = rng.choice(LAB, 300); pB = np.where(gB == "negative", "neutral", gB)
    gold = np.concatenate([gA, gB]); pred = np.concatenate([pA, pB])
    types = np.array(["A"] * 300 + ["B"] * 300)
    # observed in B: 0% negative, 60% neutral -> truth with per-type rates: ~50% negative
    groupB = np.array(["neutral"] * 60 + ["positive"] * 40)
    point, _ = race_draws({"B": groupB}, gold, pred, np.ones(600), reps=20, cal_type=types)
    assert point[0] > 0.35
