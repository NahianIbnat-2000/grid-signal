"""Pilot diagnostics. Prints counts only, never comment text.

Run:  python -m pipelines.pilot_stats
"""
from __future__ import annotations

import re

import pandas as pd

from . import store
from .preprocess import dedup_key

# Rough 2025 grid surnames + team names. Pilot indicator only, not the real
# entity linker (that comes in Phase 4 and must handle nicknames and context).
ENTITY_TERMS = [
    "verstappen", "tsunoda", "lawson", "norris", "piastri", "leclerc", "hamilton", "russell",
    "antonelli", "alonso", "stroll", "gasly", "doohan", "colapinto", "ocon", "bearman", "albon",
    "sainz", "hulkenberg", "hülkenberg", "bortoleto", "hadjar",
    "red bull", "mclaren", "ferrari", "mercedes", "aston martin", "alpine", "haas", "williams",
    "sauber", "racing bulls", "vcarb",
]
ENTITY_RE = re.compile(r"\b(?:" + "|".join(map(re.escape, ENTITY_TERMS)) + r")\b", re.IGNORECASE)


def per_video(texts: pd.DataFrame, sources: pd.DataFrame) -> pd.DataFrame:
    df = texts.merge(sources[["video_id", "video_type", "gp_key", "published_at"]],
                     on="video_id", suffixes=("", "_video"))
    lag_h = (pd.to_datetime(df["published_at"], utc=True)
             - pd.to_datetime(df["published_at_video"], utc=True)).dt.total_seconds() / 3600
    txt = df["text"].fillna("")
    df = df.assign(
        lag_h=lag_h,
        within_24h=lag_h <= 24, within_7d=lag_h <= 24 * 7,
        mentions_entity=txt.str.contains(ENTITY_RE),
        short=txt.str.split().str.len().fillna(0) < 4,
        emoji_only=~txt.str.contains(r"\w", regex=True),
        dup=txt.map(dedup_key).duplicated(keep=False),  # recomputed: old hashes had the emoji bug
    )
    g = df.groupby(["gp_key", "video_type"])
    out = g.agg(n=("record_id", "size"), median_lag_h=("lag_h", "median"),
                share_24h=("within_24h", "mean"), share_7d=("within_7d", "mean"),
                share_entity=("mentions_entity", "mean"), share_short=("short", "mean"), share_emoji_only=("emoji_only", "mean"),
                share_dup=("dup", "mean")).round(3)
    return out.reset_index()


if __name__ == "__main__":
    t, s = store.load("texts"), store.load("sources")
    if t.empty:
        raise SystemExit("no comments collected yet")
    pd.set_option("display.width", 200)
    res = per_video(t, s)
    print(res.to_string(index=False))
    print(f"\nTOTAL comments: {len(t)} | videos: {t.video_id.nunique()}")
    errs = store.load("unavailable_videos")
    if not errs.empty:
        print("\nERRORS during collection:")
        print(errs.merge(s[["video_id", "gp_key", "video_type"]], on="video_id", how="left")
              .drop(columns=["checked_at"]).to_string(index=False))
    st = store.load("video_status")
    if not st.empty:
        print(f"\nvideos marked complete: {int(st.complete.sum())} of {len(st)}")
