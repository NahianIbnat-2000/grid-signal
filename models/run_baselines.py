"""Run all sentiment models against the hand-labelled F1 set.

  python -m models.run_baselines --split dev                  # baselines only
  python -m models.run_baselines --split dev --transformers   # + transformer models
  python -m models.run_baselines --split test --final   # run ONCE at the end

Every test run is appended to research/results/test_runs.log, so repeated
peeking at the test set is visible to readers.
Output: research/results/baselines_<split>.json (metrics only, no text).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from annotation.workbook import ROOT as ANN_ROOT
from pipelines import store
from pipelines.schemas import utcnow

from .baselines import LABELS, Vader, load_dynasent, train_tfidf
from .evaluate import (cluster_bootstrap_ci, expected_calibration_error, paired_difference,
                       point_metrics, subgroup_table)

RESULTS = Path("research/results")


def load_gold(split: str, batch: str = "batch_01") -> tuple[pd.DataFrame, dict]:
    labels = pd.read_parquet(ANN_ROOT / f"labels_{batch}.parquet")
    meta = pd.read_parquet(ANN_ROOT / f"{batch}_meta.parquet")
    texts = store.load("texts")[["record_id", "text"]]
    df = meta.merge(labels, on="record_id").merge(texts, on="record_id", how="left")
    df = df[df["split"] == split]
    missing_text = int(df["text"].isna().sum())
    annotators = sorted(labels["annotator"].unique()) if "annotator" in labels else ["human"]
    counts = {"labelled": int(len(df)), "annotator": annotators,
              "label_distribution": df["overall"].value_counts().to_dict(),
              "text_no_longer_available": missing_text}
    df = df[df["text"].notna() & df["overall"].isin(LABELS)].copy()
    counts["scored_3class"] = int(len(df))
    df["text_len_words"] = df["text"].str.split().str.len()
    return df.reset_index(drop=True), counts


def timed(fn, texts) -> tuple[np.ndarray, float]:
    t0 = time.perf_counter()
    out = fn(texts)
    return out, (time.perf_counter() - t0) / max(len(texts), 1) * 1000  # ms per comment


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--final", action="store_true", help="required for --split test")
    ap.add_argument("--rounds", default="2", help="DynaSent rounds to train on, e.g. 2 or 1,2")
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--transformers", action="store_true", help="also run pretrained transformer models")
    ap.add_argument("--finetuned", default=None, help="folder of a model from models/finetune_dynasent.py")
    a = ap.parse_args()
    if a.split == "test" and not a.final:
        raise SystemExit("test set is for the final run only: add --final (this run will be logged)")
    rounds = tuple(int(x) for x in a.rounds.split(","))

    gold, counts = load_gold(a.split)
    if len(gold) < 30:
        raise SystemExit(f"only {len(gold)} scorable {a.split} items; label more first")
    texts, clusters = gold["text"].tolist(), gold["gp_key"].to_numpy()

    preds, info = {}, {}
    v = Vader()
    preds["vader"], ms = timed(v.predict, texts)
    info["vader"] = {"family": "lexicon", "training": "none", "thresholds": [v.neg, v.pos],
                     "licence": "MIT", "ms_per_comment": ms}

    dev, _ = load_gold("dev") if a.split == "test" else (gold, None)
    vt = v.tune(dev["text"].tolist(), dev["overall"].to_numpy())
    preds["vader_tuned"], ms = timed(vt.predict, texts)
    info["vader_tuned"] = {"family": "lexicon", "training": "threshold tuned on DEV labels",
                           "thresholds": [vt.neg, vt.pos], "licence": "MIT", "ms_per_comment": ms}

    train = load_dynasent("train", rounds)
    ds_test = load_dynasent("test", rounds)
    proba = {}
    for kind in ("logreg", "svm"):
        t0 = time.perf_counter()
        m = train_tfidf(kind, train)
        fit_s = time.perf_counter() - t0
        name = f"tfidf_{kind}"
        preds[name], ms = timed(m.predict, texts)
        if kind == "logreg":
            proba[name] = (m.predict_proba(texts), list(m.classes_))
        in_domain = point_metrics(ds_test["gold_label"], m.predict(ds_test["sentence"]))["macro_f1"]
        info[name] = {"family": "classical_ml", "training": f"DynaSent rounds {rounds} ({len(train)} sentences)",
                      "licence": "data CC BY 4.0", "fit_seconds": fit_s, "ms_per_comment": ms,
                      "dynasent_test_macro_f1": in_domain}

    if a.transformers:
        from .transformer_models import MODEL_INFO, default_models, time_per_comment
        for m in default_models(a.finetuned):
            if m.binary:
                m.tune_band(dev["text"].tolist(), dev["overall"].to_numpy())
            preds[m.name], ms = time_per_comment(m, texts)
            pr, cls = m.predict_proba(texts)
            if not m.binary:
                proba[m.name] = (pr, cls)
            info[m.name] = {**MODEL_INFO[m.name], **m.meta, "ms_per_comment": ms,
                            **({"neutral_band": m.band} if m.binary else {})}

    y = gold["overall"].to_numpy()
    w = gold["weight"].to_numpy()
    results = {}
    for name, p in preds.items():
        gold[f"pred_{name}"] = p
        r = {"sample": point_metrics(y, p), "population_weighted": point_metrics(y, p, w)}
        r["sample"]["macro_f1_ci95"] = cluster_bootstrap_ci(y, p, clusters, reps=a.reps)
        r["population_weighted"]["macro_f1_ci95"] = cluster_bootstrap_ci(y, p, clusters, w, reps=a.reps)
        r["subgroups"] = subgroup_table(gold, f"pred_{name}")
        if name in proba:
            pr, cls = proba[name]
            r["ece"] = expected_calibration_error(y, pr, cls)
        results[name] = {**info[name], **r}

    comparisons = {f"{n} - vader": paired_difference(y, preds[n], preds["vader"], clusters, reps=a.reps)
                   for n in preds if n != "vader"}

    out = {"split": a.split, "generated_at": utcnow().isoformat(), "counts": counts,
           "races": int(len(np.unique(clusters))), "bootstrap": f"cluster by race, {a.reps} reps",
           "note": "Sentiment estimated by GRID SIGNAL models; not YouTube data.",
           "gold_labels_by": counts["annotator"],
           "models": results, "comparisons": comparisons}
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"baselines_{a.split}.json"
    path.write_text(json.dumps(out, indent=2))
    if a.split == "test":
        with (RESULTS / "test_runs.log").open("a") as fh:
            fh.write(f"{out['generated_at']}\tbaselines\tn={len(gold)}\n")

    print(f"{a.split}: {len(gold)} items scored, {out['races']} races | {counts}")
    print(f"{'model':16s} {'macroF1':>8s} {'95% CI':>17s} {'acc':>6s} {'pop-wF1':>8s}")
    for n, r in results.items():
        lo, hi = r["sample"]["macro_f1_ci95"]
        print(f"{n:16s} {r['sample']['macro_f1']:8.3f}   [{lo:.3f}, {hi:.3f}] {r['sample']['accuracy']:6.3f} "
              f"{r['population_weighted']['macro_f1']:8.3f}")
    for k, c in comparisons.items():
        print(f"{k:24s} diff {c['diff']:+.3f}  CI [{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}]")
    print(f"saved {path}")


if __name__ == "__main__":
    main()
