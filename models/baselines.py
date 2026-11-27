"""Baseline sentiment models.

Model A  VADER (lexicon, MIT licence). No training. Thresholds on the compound
         score: default +/-0.05 (Hutto & Gilbert 2014); optionally tuned on the
         DEV labels only.
Model B  TF-IDF + Logistic Regression and TF-IDF + Linear SVM, trained on
         DynaSent Round 2 (CC BY 4.0, crowdworker-written sentences). Never
         trained on YouTube comments.

All models output one of: positive / neutral / negative.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

LABELS = ["negative", "neutral", "positive"]
DYNASENT_DIR = Path("data/external/dynasent")


# ------------------------------------------------------------------ data
def load_dynasent(split: str = "train", rounds: tuple[int, ...] = (2,), root: Path = DYNASENT_DIR) -> pd.DataFrame:
    names = {1: "round01-yelp", 2: "round02-dynabench"}
    frames = []
    for r in rounds:
        p = root / f"dynasent-v1.1-{names[r]}-{split}.jsonl"
        if not p.exists():
            raise SystemExit(f"missing {p}. Download dynasent-v1.1.zip from github.com/cgpotts/dynasent "
                             f"and unzip the .jsonl files into {root}/")
        with p.open(encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh]
        df = pd.DataFrame(rows)[["sentence", "gold_label"]]
        df["round"] = r
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    # gold_label is None when fewer than 3 of 5 workers agreed; 'mixed' is outside our 3 classes
    return df[df["gold_label"].isin(LABELS)].reset_index(drop=True)


# ------------------------------------------------------------------ VADER
@dataclass
class Vader:
    pos: float = 0.05
    neg: float = -0.05
    name: str = "vader"
    _an: object = field(default=None, repr=False)

    def _analyzer(self):
        if self._an is None:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._an = SentimentIntensityAnalyzer()
        return self._an

    def scores(self, texts) -> np.ndarray:
        an = self._analyzer()
        return np.array([an.polarity_scores(t)["compound"] for t in texts])

    def label(self, compound: np.ndarray) -> np.ndarray:
        return np.where(compound >= self.pos, "positive", np.where(compound <= self.neg, "negative", "neutral"))

    def predict(self, texts) -> np.ndarray:
        return self.label(self.scores(texts))

    def tune(self, texts, gold, grid=np.round(np.arange(0.05, 0.75, 0.05), 2)) -> "Vader":
        """Pick symmetric threshold t (pos=t, neg=-t) maximizing macro-F1 on DEV labels."""
        from sklearn.metrics import f1_score
        c = self.scores(texts)
        best = max(grid, key=lambda t: f1_score(
            gold, np.where(c >= t, "positive", np.where(c <= -t, "negative", "neutral")),
            labels=LABELS, average="macro", zero_division=0))
        return Vader(pos=float(best), neg=-float(best), name="vader_tuned", _an=self._an)


# ------------------------------------------------------------------ TF-IDF models
def tfidf_model(kind: str = "logreg", seed: int = 0):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline
    from sklearn.svm import LinearSVC

    feats = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, lowercase=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True)),
    ])
    clf = (LogisticRegression(max_iter=2000, C=2.0, class_weight="balanced", random_state=seed)
           if kind == "logreg" else LinearSVC(C=0.5, class_weight="balanced", random_state=seed))
    return Pipeline([("tfidf", feats), ("clf", clf)])


def train_tfidf(kind: str, train: pd.DataFrame, seed: int = 0):
    m = tfidf_model(kind, seed)
    m.fit(train["sentence"], train["gold_label"])
    return m
