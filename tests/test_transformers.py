"""Logic tests with a fake probability function (no model download)."""
import numpy as np
import pytest

from models.transformer_models import (HFSentiment, binary_to_three, cardiff_preprocess,
                                       normalize_label)


def test_label_normalization():
    assert normalize_label("NEGATIVE") == "negative"
    assert normalize_label("Neutral") == "neutral"
    assert normalize_label("positive") == "positive"
    assert normalize_label("LABEL_2") == "positive"
    with pytest.raises(ValueError):
        normalize_label("joy")


def test_cardiff_preprocess():
    assert cardiff_preprocess("@max great https://x.co/1") == "@user great http"


def test_binary_to_three_band():
    p = np.array([0.95, 0.55, 0.45, 0.05])
    assert list(binary_to_three(p, 0.1)) == ["positive", "neutral", "neutral", "negative"]
    assert list(binary_to_three(p, 0.0)) == ["positive", "positive", "negative", "negative"]


def _fake(probs_by_text, classes):
    return lambda texts: (np.array([probs_by_text[t] for t in texts]), classes)


def test_three_class_model_argmax():
    m = HFSentiment("t", "x", _proba_fn=_fake({"a": [0.7, 0.2, 0.1], "b": [0.1, 0.2, 0.7]},
                                               ["negative", "neutral", "positive"]))
    assert list(m.predict(["a", "b"])) == ["negative", "positive"]


def test_binary_model_band_tuning_creates_neutral():
    probs = {"good": [0.02, 0.98], "bad": [0.97, 0.03], "meh": [0.45, 0.55], "eh": [0.55, 0.45]}
    m = HFSentiment("t", "x", binary=True, _proba_fn=_fake(probs, ["negative", "positive"]))
    m.tune_band(list(probs), ["positive", "negative", "neutral", "neutral"])
    assert 0.05 < m.band < 0.45
    assert list(m.predict(list(probs))) == ["positive", "negative", "neutral", "neutral"]
