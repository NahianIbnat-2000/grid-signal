"""Discussion topics with NMF on TF-IDF (no paid models, runs on a laptop).

  python -m analysis.topics.nmf_topics --k 12

Steps
1. Fit TF-IDF + NMF on a random sample (default 60k comments) for speed.
2. Assign every comment to its strongest topic; weak assignments (top weight
   below a threshold) are reported as 'unassigned' instead of forced.
3. Stability: refit with 3 more seeds and match topics by cosine similarity
   of their word vectors. Mean best-match similarity near 1 = stable topics.
4. Outputs topic top-words, prevalence by race x video type, and stability to
   research/results/topics.json. NO comment text is exported.

Topic names are NOT generated. Write them by hand in
data/manifests/topic_labels.yaml after reading the top words, so every label
is a human (or clearly disclosed) judgement.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from annotation.workbook import CORE_TYPES
from pipelines import store
from pipelines.schemas import utcnow

LABEL_FILE = Path("data/manifests/topic_labels.yaml")
F1_STOP = ["f1", "formula", "race", "lol", "like", "just", "im", "dont", "hes", "thats", "really", "got",
           "get", "one", "would", "even", "know", "think", "see", "go", "going", "time", "still", "also"]


def fit(texts: list[str], k: int, seed: int, min_df: int | None = None):
    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
    if min_df is None:
        min_df = 20 if len(texts) > 5000 else 2
    vec = TfidfVectorizer(stop_words=list(ENGLISH_STOP_WORDS.union(F1_STOP)), min_df=min_df, max_df=0.4,
                          ngram_range=(1, 2), max_features=20000, sublinear_tf=True,
                          token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b")
    X = vec.fit_transform(texts)
    nmf = NMF(n_components=k, init="nndsvda", random_state=seed, max_iter=400)
    nmf.fit(X)
    return vec, nmf


def top_words(vec, nmf, n=12) -> list[list[str]]:
    vocab = np.array(vec.get_feature_names_out())
    return [vocab[np.argsort(row)[::-1][:n]].tolist() for row in nmf.components_]


def stability(base_vec, base_nmf, texts, k, seeds=(1, 2, 3)) -> dict:
    """Match each base topic to its most similar topic in refits (same vocabulary space)."""
    vocab = list(base_vec.get_feature_names_out())
    B = base_nmf.components_ / np.linalg.norm(base_nmf.components_, axis=1, keepdims=True)
    per_topic = []
    for s in seeds:
        v2, n2 = fit(texts, k, s)
        idx = {w: i for i, w in enumerate(v2.get_feature_names_out())}
        C = np.zeros((k, len(vocab)))
        common = [(j, idx[w]) for j, w in enumerate(vocab) if w in idx]
        jj, ii = zip(*common)
        C[:, list(jj)] = n2.components_[:, list(ii)]
        C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-12
        per_topic.append((B @ C.T).max(axis=1))
    sims = np.mean(per_topic, axis=0)
    return {"per_topic": sims.round(3).tolist(), "mean": float(sims.mean()), "seeds": list(seeds)}


def assign(vec, nmf, texts: list[str], min_weight: float) -> np.ndarray:
    W = nmf.transform(vec.transform(texts))
    top = W.argmax(axis=1)
    return np.where(W.max(axis=1) < min_weight, -1, top)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--sample", type=int, default=60000)
    ap.add_argument("--min-weight", type=float, default=0.02)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    txt = store.load("texts")
    src = store.load("sources")[["video_id", "video_type", "gp_key"]]
    df = txt[txt["text"].notna()].merge(src, on="video_id")
    df = df[df["video_type"].isin(CORE_TYPES)].reset_index(drop=True)
    fit_df = df.sample(n=min(a.sample, len(df)), random_state=a.seed)
    vec, nmf = fit(fit_df["text"].tolist(), a.k, a.seed)
    words = top_words(vec, nmf)
    stab = stability(vec, nmf, fit_df["text"].tolist(), a.k)

    df["topic"] = assign(vec, nmf, df["text"].tolist(), a.min_weight)
    names = yaml.safe_load(LABEL_FILE.read_text()) if LABEL_FILE.exists() else {}
    prev = (df.groupby(["gp_key", "video_type"])["topic"].value_counts(normalize=True)
            .rename("share").reset_index())
    overall = df["topic"].value_counts(normalize=True).sort_index()

    topics = [{"id": i, "name": names.get(i, f"Topic {i} (unlabelled)"), "top_words": w,
               "overall_share": float(overall.get(i, 0.0)), "stability": stab["per_topic"][i]}
              for i, w in enumerate(words)]
    payload = {"generated_at": utcnow().isoformat(), "method": f"TF-IDF + NMF, k={a.k}, fit on "
               f"{len(fit_df)} comments, seed {a.seed}", "unassigned_share": float(overall.get(-1, 0.0)),
               "min_weight": a.min_weight, "stability": stab, "topics": topics,
               "labels_by": "manual (data/manifests/topic_labels.yaml)" if names else "none yet",
               "prevalence": json.loads(prev.to_json(orient="records"))}
    out = Path("research/results/topics.json")
    out.write_text(json.dumps(payload, indent=2))
    print(f"k={a.k} | unassigned {payload['unassigned_share']:.1%} | stability mean {stab['mean']:.2f}")
    for t in topics:
        print(f"[{t['id']:2d}] {t['overall_share']:5.1%} stab {t['stability']:.2f} | {', '.join(t['top_words'][:10])}")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
