"""Race-level attention, negativity and disagreement, with uncertainty.

  python -m analysis.polarization.controversy

Definitions (per race, pooling the 4 core video types with EQUAL weight, so a
race is not driven by which video happened to get more comments):

  attention     comments on the race's 4 core videos (raw count; mostly reflects
                audience size, e.g. the season opener)
  negativity    corrected share of negative comments
  net sentiment corrected positive share minus negative share
  disagreement  sentiment bipolarity = variance of X in {-1, 0, +1}
                = p_pos + p_neg - (p_pos - p_neg)^2, in [0, 1].
                0 when everyone agrees (all negative, all positive or all
                neutral); 1 when comments split 50/50 positive vs negative.
                A heavily criticised race therefore scores HIGH negativity
                but LOW disagreement, as the research brief requires.

NOT measured: stance (who is right in an incident) and polarization in the
sense of opposing camps. Sentiment split is a proxy, not stance.

Uncertainty: 1,000 bootstrap draws resample the labelled set (classifier
error rates, shared across video types in a draw) and each video's comments.
We also report P(top 3): the share of draws in which a race ranks in the top 3
for disagreement, so readers see how stable the ranking is.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from annotation.workbook import CORE_TYPES, ROOT as ANN_ROOT
from pipelines import store
from pipelines.schemas import utcnow

from ..sentiment.quantify import LABELS, adjust, confusion_rates, shares

MODEL = "roberta_twitter"


def bipolarity(p: np.ndarray) -> np.ndarray:
    """p[..., 0]=neg, p[..., 2]=pos. Variance of {-1,0,+1}."""
    neg, pos = p[..., 0], p[..., 2]
    return pos + neg - (pos - neg) ** 2


def race_draws(groups: dict[str, np.ndarray], gold, gold_pred, weight, reps=1000, seed=0):
    """groups: video_type -> predicted labels. Returns point (3,) and draws (reps, 3)
    of the equally weighted mean of corrected shares across video types."""
    rng = np.random.default_rng(seed)
    gold, gold_pred, weight = map(np.asarray, (gold, gold_pred, weight))
    M = confusion_rates(gold, gold_pred, weight)
    point = np.mean([adjust(shares(g), M) for g in groups.values()], axis=0)
    draws = np.empty((reps, 3))
    for b in range(reps):
        gi = rng.integers(0, len(gold), len(gold))
        Mb = confusion_rates(gold[gi], gold_pred[gi], weight[gi])
        ps = []
        for g in groups.values():
            qi = rng.integers(0, len(g), len(g))
            ps.append(adjust(shares(g[qi]), Mb))
        draws[b] = np.mean(ps, axis=0)
    return point, draws


def build(df: pd.DataFrame, cal: pd.DataFrame, reps: int = 1000) -> pd.DataFrame:
    rows, all_draws = [], {}
    for gp, g in df.groupby("gp_key"):
        groups = {vt: x["label"].to_numpy() for vt, x in g.groupby("video_type") if len(x) >= 10}
        if len(groups) < 4:
            continue
        point, draws = race_draws(groups, cal["overall"], cal["label"], cal["weight"], reps)
        all_draws[gp] = bipolarity(draws)
        def ci(v):
            return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))
        rows.append({
            "gp_key": gp, "attention": int(len(g)),
            "negativity": float(point[0]), "negativity_ci": ci(draws[:, 0]),
            "net_sentiment": float(point[2] - point[0]), "net_sentiment_ci": ci(draws[:, 2] - draws[:, 0]),
            "disagreement": float(bipolarity(point)), "disagreement_ci": ci(bipolarity(draws)),
        })
    out = pd.DataFrame(rows)
    D = np.column_stack([all_draws[g] for g in out["gp_key"]])      # reps x races
    ranks = (-D).argsort(axis=1).argsort(axis=1)                      # 0 = highest
    out["p_top3_disagreement"] = (ranks < 3).mean(axis=0)
    return out.sort_values("disagreement", ascending=False).reset_index(drop=True)


def main() -> None:
    an = store.load("analysis")
    an = an[an["model"] == MODEL]
    src = store.load("sources")[["video_id", "video_type", "gp_key"]]
    txt = store.load("texts")[["record_id", "video_id"]]
    df = an.merge(txt, on="record_id").merge(src, on="video_id")
    df = df[df["video_type"].isin(CORE_TYPES)]

    labels = pd.read_parquet(ANN_ROOT / "labels_batch_01.parquet")
    meta = pd.read_parquet(ANN_ROOT / "batch_01_meta.parquet")[["record_id", "weight"]]
    cal = labels.merge(meta, on="record_id").merge(an[["record_id", "label"]], on="record_id")
    cal = cal[cal["overall"].isin(LABELS)]

    out = build(df, cal)
    cal_path = Path("data/processed/calendar_2025.csv")
    if cal_path.exists():
        from pipelines.collect import gp_key
        c = pd.read_csv(cal_path)
        c["gp_key"] = c["race_name"].map(gp_key)
        out = out.merge(c[["gp_key", "round", "race_name", "race_start_utc"]], on="gp_key", how="left")

    payload = {"generated_at": utcnow().isoformat(), "model": MODEL,
               "gold_labels_by": sorted(labels["annotator"].unique()) if "annotator" in labels else ["human"],
               "definitions": __doc__, "note": "Sampled YouTube discourse on official F1 videos only. "
               "Rankings apply to this sample and this metric.", "rows": json.loads(out.to_json(orient="records"))}
    p = Path("research/results/controversy_by_race.json")
    p.write_text(json.dumps(payload, indent=2))
    show = out[["gp_key", "attention", "negativity", "disagreement", "p_top3_disagreement"]].copy()
    show["dis_lo"] = [x[0] for x in out["disagreement_ci"]]
    show["dis_hi"] = [x[1] for x in out["disagreement_ci"]]
    print(show.round(3).to_string(index=False))
    print(f"saved {p}")


if __name__ == "__main__":
    main()
