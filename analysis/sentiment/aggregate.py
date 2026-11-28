"""Race x video-type sentiment table for the website (aggregates only).

  python -m analysis.sentiment.aggregate

Reads the scored corpus + labelled set, applies the adjusted classify-and-count
correction, suppresses groups with < MIN_CELL comments, writes
research/results/sentiment_by_race.json. No comment text, no IDs.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from annotation.workbook import ROOT as ANN_ROOT
from pipelines import store
from pipelines.export import MIN_CELL, check_columns
from pipelines.schemas import utcnow

from .quantify import adjusted_shares_ci

MODEL = "roberta_twitter"


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", choices=["dev", "all"], default="dev",
                    help="'all' = dev+test labels; only allowed after the final test run")
    a = ap.parse_args()
    if a.labels == "all" and not Path("research/results/test_runs.log").exists():
        raise SystemExit("run the final test evaluation first (models.run_baselines --split test --final)")
    an = store.load("analysis")
    an = an[an["model"] == MODEL]
    src = store.load("sources")[["video_id", "video_type", "gp_key"]]
    txt = store.load("texts")[["record_id", "video_id"]]
    df = an.merge(txt, on="record_id").merge(src, on="video_id")

    labels = pd.read_parquet(ANN_ROOT / "labels_batch_01.parquet")
    meta = pd.read_parquet(ANN_ROOT / "batch_01_meta.parquet")[["record_id", "split", "weight"]]
    # Error rates come from the DEV labels only until the final test run is done.
    cal = labels.merge(meta, on="record_id").merge(an[["record_id", "label"]], on="record_id")
    keep_split = ["dev"] if a.labels == "dev" else ["dev", "test"]
    cal = cal[cal["split"].isin(keep_split) & cal["overall"].isin(["negative", "neutral", "positive"])]
    if len(cal) < 50:
        raise SystemExit("not enough scored DEV labels for the correction (need the corpus scored first)")

    rows = []
    for (gp, vt), g in df.groupby(["gp_key", "video_type"]):
        if len(g) < MIN_CELL:
            continue
        r = adjusted_shares_ci(g["label"].to_numpy(), cal["overall"].to_numpy(), cal["label"].to_numpy(),
                               cal["weight"].to_numpy())
        rows.append({"gp_key": gp, "video_type": vt, **r})
    out = pd.DataFrame(rows)
    check_columns(out)
    payload = {"generated_at": utcnow().isoformat(), "model": MODEL,
               "correction": f"adjusted classify-and-count, error rates from {len(cal)} labels ({'+'.join(keep_split)}), weighted to population",
               "gold_labels_by": sorted(labels["annotator"].unique()) if "annotator" in labels else ["human"],
               "note": "Sentiment estimated by GRID SIGNAL models; not YouTube data. Sampled online discourse only.",
               "rows": json.loads(out.to_json(orient="records"))}
    p = Path("research/results/sentiment_by_race.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2))
    print(f"{len(out)} race x video groups -> {p}")
    from .quantify import confusion_rates
    M = confusion_rates(cal["overall"], cal["label"], cal["weight"])
    print("error rates P(pred | true), columns = true neg/neu/pos:")
    print(pd.DataFrame(M, index=["pred_neg", "pred_neu", "pred_pos"],
                       columns=["true_neg", "true_neu", "true_pos"]).round(2).to_string())
    out["ci_width_neg"] = out["adj_negative_hi"] - out["adj_negative_lo"]
    print(f"median 95% CI width for adjusted negative share: {out['ci_width_neg'].median():.2f}")
    print(out[["gp_key", "video_type", "n", "raw_negative", "adj_negative", "adj_negative_lo",
               "adj_negative_hi"]].round(3).head(12).to_string(index=False))


if __name__ == "__main__":
    main()
