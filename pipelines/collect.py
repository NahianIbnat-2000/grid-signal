"""Collect comments for videos chosen by an explicit sampling frame.

Usage:
    export YOUTUBE_API_KEY=...            # never commit this
    python -m pipelines.collect --frame data/manifests/sampling_frame.yaml --dry-run
    python -m pipelines.collect --frame data/manifests/sampling_frame.yaml

Sampling: every upload from each listed channel inside the season window whose
title matches the event keywords. No view-count or virality filter, so the
sample is not tilted toward controversial videos.
"""
from __future__ import annotations

import argparse
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml

from . import store
from .preprocess import dedup_key
from .quota import QuotaExceeded, QuotaTracker
from .schemas import SourceRecord, TextRecord, utcnow
from .youtube_client import YouTubeClient, YouTubeError

log = logging.getLogger("collect")


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def parse_thread(item: dict) -> list[TextRecord]:
    """Map a commentThread resource to TextRecords. Author fields are dropped here."""
    top = item["snippet"]["topLevelComment"]
    sn = top["snippet"]
    text = sn.get("textOriginal") or sn.get("textDisplay") or ""
    rec = TextRecord(
        record_id=top["id"],
        video_id=sn["videoId"] if "videoId" in sn else item["snippet"]["videoId"],
        published_at=_ts(sn["publishedAt"]),
        updated_at=_ts(sn["updatedAt"]) if sn.get("updatedAt") else None,
        text=text,
        like_count=int(sn.get("likeCount", 0)),
        reply_count=int(item["snippet"].get("totalReplyCount", 0)),
        text_hash=dedup_key(text),
    )
    return [rec]


def select_videos(uploads: Iterable[dict], start: datetime, end: datetime, pattern: re.Pattern) -> list[dict]:
    out = []
    for it in uploads:
        sn = it["snippet"]
        pub = _ts(it["contentDetails"].get("videoPublishedAt") or sn["publishedAt"])
        if start <= pub <= end and pattern.search(sn.get("title", "")):
            out.append({"video_id": it["contentDetails"]["videoId"], "title": sn.get("title"),
                        "published_at": pub})
    return out


def run(frame_path: Path, dry_run: bool = False, max_comment_pages: int | None = None) -> dict:
    frame = yaml.safe_load(Path(frame_path).read_text())
    quota = QuotaTracker(Path("data/restricted/quota_state.json"))
    yt = YouTubeClient(quota)
    start, end = _ts(frame["window"]["start"]), _ts(frame["window"]["end"])
    pattern = re.compile("|".join(frame["title_keywords"]), re.IGNORECASE)

    sources: list[SourceRecord] = []
    for ch in frame["channels"]:
        try:
            meta = yt.channel_by_handle(ch["handle"])
        except YouTubeError as e:
            log.error("skip channel %s: %s", ch["handle"], e)
            continue
        uploads_id = meta["contentDetails"]["relatedPlaylists"]["uploads"]
        vids = select_videos(yt.uploads(uploads_id, max_pages=ch.get("max_upload_pages", 20)),
                             start, end, pattern)
        for v in vids:
            sources.append(SourceRecord(source_id=meta["id"], video_id=v["video_id"],
                                        channel_category=ch["category"], title=v["title"],
                                        published_at=v["published_at"],
                                        sampling_rule=f"{ch['handle']}|keywords|window"))
        log.info("%s: %d videos selected", ch["handle"], len(vids))

    summary = {"videos_selected": len(sources), "units_used": quota.units_used}
    if dry_run:
        return summary

    store.upsert("sources", pd.DataFrame([s.model_dump() for s in sources]), key="video_id")
    existing = store.load("texts")
    seen = set(existing["record_id"]) if not existing.empty else set()

    new_rows, unavailable = [], []
    for s in sources:
        try:
            for item in yt.comment_threads(s.video_id, max_pages=max_comment_pages):
                for rec in parse_thread(item):
                    if rec.record_id in seen:
                        break  # order=time: older comments were already collected
                    new_rows.append(rec.model_dump())
                    seen.add(rec.record_id)
        except YouTubeError as e:
            unavailable.append({"video_id": s.video_id, "reason": e.reason, "checked_at": utcnow()})
        except QuotaExceeded:
            log.warning("quota budget reached; stopping, rerun tomorrow to continue")
            break

    if new_rows:
        store.upsert("texts", pd.DataFrame(new_rows), key="record_id")
    if unavailable:
        store.upsert("unavailable_videos", pd.DataFrame(unavailable), key="video_id")
    summary.update(new_comments=len(new_rows), unavailable_videos=len(unavailable),
                   units_used=quota.units_used)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true", help="select videos only; no comment calls")
    ap.add_argument("--max-comment-pages", type=int, default=None)
    a = ap.parse_args()
    print(run(a.frame, a.dry_run, a.max_comment_pages))
