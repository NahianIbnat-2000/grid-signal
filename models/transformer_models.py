"""Transformer sentiment models: pretrained inference (no training on F1 data).

T1  cardiffnlp/twitter-roberta-base-sentiment-latest  (CC BY 4.0)
    RoBERTa-base, further pretrained on ~124M tweets, fine-tuned on TweetEval.
    Native 3 classes. Closest domain to YouTube comments.
T2  distilbert/distilbert-base-uncased-finetuned-sst-2-english  (Apache-2.0)
    BINARY (positive/negative). A neutral class is created when the model's
    top probability is below a band tuned on DEV labels. Report this as an
    adaptation, not a native 3-class model.
T3  (optional) any local folder produced by models/finetune_dynasent.py:
    DistilBERT fine-tuned on DynaSent Round 2 (general domain, CC BY 4.0).

Install the extra packages first:  pip install -r requirements-dl.txt
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

LABELS = ["negative", "neutral", "positive"]
_USER = re.compile(r"@\w+")
_URL = re.compile(r"https?://\S+|<url>")


def cardiff_preprocess(text: str) -> str:
    """Preprocessing recommended on the CardiffNLP model card."""
    return _URL.sub("http", _USER.sub("@user", text))


def normalize_label(raw: str) -> str:
    r = raw.lower()
    for lab in LABELS:
        if lab.startswith(r[:3]) or r == lab:
            return lab
    if r in {"label_0", "0"}:
        return "negative"
    if r in {"label_1", "1"}:
        return "neutral"
    if r in {"label_2", "2"}:
        return "positive"
    raise ValueError(f"unknown label {raw!r}")


def binary_to_three(p_pos: np.ndarray, band: float) -> np.ndarray:
    """Binary positive-probability -> 3 classes. |p_pos - 0.5| < band -> neutral."""
    return np.where(np.abs(p_pos - 0.5) < band, "neutral", np.where(p_pos >= 0.5, "positive", "negative"))


@dataclass
class HFSentiment:
    name: str
    model_id: str
    binary: bool = False
    band: float = 0.0                     # only used when binary
    preprocess: Callable[[str], str] = staticmethod(lambda t: t)
    max_length: int = 128
    batch_size: int = 32
    revision: Optional[str] = None
    _proba_fn: Optional[Callable] = field(default=None, repr=False)   # injectable for tests
    meta: dict = field(default_factory=dict)

    def _load(self):
        if self._proba_fn is not None:
            return
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
        model = AutoModelForSequenceClassification.from_pretrained(self.model_id, revision=self.revision)
        model.eval()
        id2label = {int(k): normalize_label(v) for k, v in model.config.id2label.items()}
        self.meta = {"model_id": self.model_id,
                     "revision": getattr(model.config, "_commit_hash", None) or self.revision,
                     "n_params": int(sum(p.numel() for p in model.parameters())),
                     "max_length": self.max_length}

        def proba(texts: list[str]) -> tuple[np.ndarray, list[str]]:
            outs = []
            with torch.no_grad():
                for i in range(0, len(texts), self.batch_size):
                    enc = tok(texts[i:i + self.batch_size], padding=True, truncation=True,
                              max_length=self.max_length, return_tensors="pt")
                    outs.append(torch.softmax(model(**enc).logits, dim=-1).cpu().numpy())
            return np.vstack(outs), [id2label[i] for i in range(len(id2label))]

        self._proba_fn = proba

    def predict_proba(self, texts) -> tuple[np.ndarray, list[str]]:
        self._load()
        return self._proba_fn([self.preprocess(t) for t in texts])

    def predict(self, texts) -> np.ndarray:
        p, cls = self.predict_proba(texts)
        if self.binary:
            return binary_to_three(p[:, cls.index("positive")], self.band)
        return np.asarray(cls)[p.argmax(axis=1)]

    def tune_band(self, texts, gold, grid=np.round(np.arange(0.0, 0.46, 0.025), 3)) -> "HFSentiment":
        """Binary models only: choose the neutral band on DEV labels (macro-F1)."""
        from sklearn.metrics import f1_score
        p, cls = self.predict_proba(texts)
        pp = p[:, cls.index("positive")]
        best = max(grid, key=lambda b: f1_score(gold, binary_to_three(pp, b), labels=LABELS,
                                                average="macro", zero_division=0))
        self.band = float(best)
        return self


def default_models(finetuned_dir: Optional[str] = None) -> list[HFSentiment]:
    ms = [
        HFSentiment("roberta_twitter", "cardiffnlp/twitter-roberta-base-sentiment-latest",
                    preprocess=cardiff_preprocess),
        HFSentiment("distilbert_sst2", "distilbert/distilbert-base-uncased-finetuned-sst-2-english",
                    binary=True),
    ]
    if finetuned_dir:
        ms.append(HFSentiment("distilbert_dynasent_ft", finetuned_dir))
    return ms


MODEL_INFO = {
    "roberta_twitter": {"family": "transformer", "training": "pretrained inference only (TweetEval)",
                        "licence": "CC BY 4.0", "native_classes": 3},
    "distilbert_sst2": {"family": "transformer", "training": "pretrained inference only (SST-2); "
                        "neutral = low-confidence band tuned on DEV", "licence": "Apache-2.0", "native_classes": 2},
    "distilbert_dynasent_ft": {"family": "transformer", "training": "fine-tuned by GRID SIGNAL on DynaSent R2 "
                               "(general domain, not F1)", "licence": "Apache-2.0 base + CC BY 4.0 data",
                               "native_classes": 3},
}


def time_per_comment(model: HFSentiment, texts) -> tuple[np.ndarray, float]:
    model._load()
    t0 = time.perf_counter()
    pred = model.predict(texts)
    return pred, (time.perf_counter() - t0) / max(len(texts), 1) * 1000
