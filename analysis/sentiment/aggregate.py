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
    an = store.load("analysis")
    an = an[an["model"] == MODEL]
    src = store.load("sources")[["video_id", "video_type", "gp_key"]]
    txt = store.load("texts")[["record_id", "video_id"]]
    df = an.merge(txt, on="record_id").merge(src, on="video_id")

    labels = pd.read_parquet(ANN_ROOT / "labels_batch_01.parquet")
    meta = pd.read_parquet(ANN_ROOT / "batch_01_meta.parquet")[["record_id", "split"]]
    # Error rates come from the DEV labels only until the final test run is done.
    cal = labels.merge(meta, on="record_id").merge(an[["record_id", "label"]], on="record_id")
    cal = cal[(cal["split"] == "dev") & cal["overall"].isin(["negative", "neutral", "positive"])]
    if len(cal) < 50:
        raise SystemExit("not enough scored DEV labels for the correction (need the corpus scored first)")

    rows = []
    for (gp, vt), g in df.groupby(["gp_key", "video_type"]):
        if len(g) < MIN_CELL:
            continue
        r = adjusted_shares_ci(g["label"].to_numpy(), cal["overall"].to_numpy(), cal["label"].to_numpy())
        rows.append({"gp_key": gp, "video_type": vt, **r})
    out = pd.DataFrame(rows)
    check_columns(out)
    payload = {"generated_at": utcnow().isoformat(), "model": MODEL,
               "correction": f"adjusted classify-and-count, error rates from {len(cal)} DEV labels",
               "gold_labels_by": sorted(labels["annotator"].unique()) if "annotator" in labels else ["human"],
               "note": "Sentiment estimated by GRID SIGNAL models; not YouTube data. Sampled online discourse only.",
               "rows": json.loads(out.to_json(orient="records"))}
    p = Path("research/results/sentiment_by_race.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2))
    print(f"{len(out)} race x video groups -> {p}")
    print(out[["gp_key", "video_type", "n", "raw_negative", "adj_negative"]].round(3).head(12).to_string(index=False))


if __name__ == "__main__":
    main()
