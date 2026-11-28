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
