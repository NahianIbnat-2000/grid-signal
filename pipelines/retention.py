"""Enforce the 30-day rule on stored comment text.

YouTube Developer Policies III.E.4: non-authorized API data must be deleted
or refreshed within 30 days. Two modes:

  purge   - drop text older than 30 days, keep id + timestamps + derived labels
  refresh - re-fetch by ID; comments YouTube no longer returns are deleted
            locally (and logged, so missingness can be reported)

Run one of them at least weekly (see .github/workflows/refresh.yml, to add).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import store
from .preprocess import dedup_key
from .quota import QuotaTracker
from .schemas import TEXT_RETENTION_DAYS, utcnow


def purge(texts: pd.DataFrame, now: datetime | None = None) -> tuple[pd.DataFrame, int]:
    if texts.empty:
        return texts, 0
    now = now or utcnow()
    cutoff = now - timedelta(days=TEXT_RETENTION_DAYS)
    collected = pd.to_datetime(texts["collected_at"], utc=True)
    expired = (collected < cutoff) & texts["text"].notna()
    out = texts.copy()
    out.loc[expired, "text"] = None
    return out, int(expired.sum())


def apply_refresh(texts: pd.DataFrame, fetched: list[dict], now: datetime | None = None
                  ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pure function: merge a refresh response into the store.

    Returns (updated_texts, deletion_log).
    """
    now = now or utcnow()
    by_id = {c["id"]: c["snippet"] for c in fetched}
    alive = texts["record_id"].isin(by_id)
    deleted = texts.loc[~alive, ["record_id", "video_id", "published_at"]].copy()
    deleted["detected_deleted_at"] = now
    kept = texts.loc[alive].copy()
    for idx, rid in kept["record_id"].items():
        sn = by_id[rid]
        txt = sn.get("textOriginal") or sn.get("textDisplay") or ""
        kept.at[idx, "text"] = txt
        kept.at[idx, "text_hash"] = dedup_key(txt)
        kept.at[idx, "like_count"] = int(sn.get("likeCount", 0))
        kept.at[idx, "collected_at"] = now  # refresh restarts the 30-day clock
    return kept.reset_index(drop=True), deleted.reset_index(drop=True)


def refresh(ids_limit: int | None = None) -> dict:
    from .youtube_client import YouTubeClient

    texts = store.load("texts")
    if texts.empty:
        return {"refreshed": 0}
    target = texts if ids_limit is None else texts.head(ids_limit)
    yt = YouTubeClient(QuotaTracker(Path("data/restricted/quota_state.json")))
    fetched = yt.comments_by_id(target["record_id"].tolist())
    updated, deleted = apply_refresh(target, fetched)
    rest = texts[~texts["record_id"].isin(target["record_id"])]
    store.save("texts", pd.concat([rest, updated], ignore_index=True))
    if not deleted.empty:
        store.upsert("deletion_log", deleted, key="record_id")
    # Derived analysis rows for deleted comments must go too.
    analysis = store.load("analysis")
    if not analysis.empty and not deleted.empty:
        store.save("analysis", analysis[~analysis["record_id"].isin(deleted["record_id"])])
    return {"refreshed": len(updated), "deleted": len(deleted)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["purge", "refresh"])
    a = ap.parse_args()
    if a.mode == "purge":
        df, n = purge(store.load("texts"))
        store.save("texts", df)
        print({"purged_text": n})
    else:
        print(refresh())
