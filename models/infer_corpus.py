"""Score every collected comment with the production model, resumably.

  python -m models.infer_corpus                 # RoBERTa-Twitter, all comments
  python -m models.infer_corpus --limit 2000    # quick trial

Writes data/restricted/analysis.parquet (record_id, model, label, p_neg, p_neu,
p_pos). Progress is saved every chunk, so Ctrl+C and re-running continues where
it stopped. Comments whose text has expired (30-day rule) are skipped.
"""
from __future__ import annotations

import argparse
import time

import pandas as pd

from pipelines import store
from pipelines.schemas import utcnow

from .transformer_models import default_models

PRODUCTION = "roberta_twitter"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=PRODUCTION)
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()

    m = next(x for x in default_models() if x.name == a.model)
    texts = store.load("texts")
    texts = texts[texts["text"].notna()]
    done = store.load("analysis")
    if not done.empty:
        done = done[done["model"] == a.model]
        texts = texts[~texts["record_id"].isin(done["record_id"])]
    if a.limit:
        texts = texts.head(a.limit)
    total = len(texts)
    print(f"{total} comments to score with {a.model}")
    t0 = time.time()
    for i in range(0, total, a.chunk):
        part = texts.iloc[i:i + a.chunk]
        p, cls = m.predict_proba(part["text"].tolist())
        out = pd.DataFrame({"record_id": part["record_id"].values, "model": a.model,
                            "model_revision": m.meta.get("revision")})
        for j, c in enumerate(cls):
            out[f"p_{c[:3]}"] = p[:, j]
        out["label"] = [cls[k] for k in p.argmax(axis=1)]
        out["scored_at"] = utcnow()
        store.upsert("analysis", out, key="record_id")
        n = i + len(part)
        rate = n / max(time.time() - t0, 1e-9)
        print(f"  {n}/{total}  ({rate:.1f}/s, ~{(total - n) / max(rate, 1e-9) / 60:.0f} min left)", flush=True)
    print("done")


if __name__ == "__main__":
    main()
