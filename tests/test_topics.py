import numpy as np

from analysis.topics.nmf_topics import assign, fit, stability, top_words

DOCS = (["penalty stewards decision unfair penalty stewards"] * 60
        + ["tyre strategy pit stop undercut tyre strategy"] * 60
        + ["rain wet crash safety car rain wet"] * 60)


def test_recovers_planted_topics_and_is_stable():
    docs = [f"{d} filler{i % 7}" for i, d in enumerate(DOCS)]
    vec, nmf = fit(docs, 3, 0)
    words = [set(w[:3]) for w in top_words(vec, nmf)]
    planted = [{"penalty", "stewards", "decision"}, {"tyre", "strategy", "pit"}, {"rain", "wet", "crash"}]
    for p in planted:
        assert any(len(p & w) >= 2 for w in words)
    s = stability(vec, nmf, docs, 3, seeds=(1, 2))
    assert s["mean"] > 0.9


def test_weak_assignments_become_unassigned():
    docs = [f"{d} filler{i % 7}" for i, d in enumerate(DOCS)]
    vec, nmf = fit(docs, 3, 0)
    lab = assign(vec, nmf, ["penalty stewards unfair", "zzz qqq"], min_weight=0.02)
    assert lab[0] >= 0 and lab[1] == -1


def test_entity_names_are_removed_from_topics():
    docs = ([f"verstappen max penalty stewards unfair" for i in range(80)]
            + [f"norris lando tyre strategy pit" for i in range(80)]
            + [f"leclerc rain wet crash" for i in range(80)])
    vec, nmf = fit(docs, 3, 0)
    vocab = set(vec.get_feature_names_out())
    assert not {"verstappen", "max", "norris", "lando"} & vocab
    assert {"penalty", "strategy"} <= vocab


def test_stability_detects_noise_topics():
    rng = np.random.default_rng(0)
    import itertools
    words = ["".join(p) for p in itertools.product("bcdfghk", "aeiou", "lmnrs")][:400]
    noise = [" ".join(rng.choice(words, 6)) for _ in range(400)]   # no real structure
    vec, nmf = fit(noise, 6, 0)
    assert stability(vec, nmf, noise, 6, seeds=(1, 2))["mean"] < 0.8
