"""Privacy-safe export of aggregate artifacts for the website.

Rules enforced here (tests cover each):
  * no comment text or author fields in any output
  * cells with fewer than MIN_CELL comments are suppressed
  * every file carries provenance + a generated_at timestamp
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from .schemas import FORBIDDEN_EXPORT_FIELDS, utcnow

MIN_CELL = 10


class UnsafeExport(ValueError):
    pass


def check_columns(df: pd.DataFrame) -> None:
    bad = FORBIDDEN_EXPORT_FIELDS.intersection(df.columns)
    if bad:
        raise UnsafeExport(f"forbidden fields in export: {sorted(bad)}")


def sentiment_by_group(analysis: pd.DataFrame, texts: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    df = analysis.merge(texts[["record_id", "video_id", "published_at"]], on="record_id", how="inner")
    counts = df.groupby(group_cols + ["label"]).size().unstack("label", fill_value=0)
    for lab in ("positive", "neutral", "negative"):
        if lab not in counts:
            counts[lab] = 0
    counts["n"] = counts[["positive", "neutral", "negative"]].sum(axis=1)
    counts = counts[counts["n"] >= MIN_CELL].reset_index()
    for lab in ("positive", "neutral", "negative"):
        counts[f"share_{lab}"] = counts[lab] / counts["n"]
    check_columns(counts)
    return counts


def write_artifact(df: pd.DataFrame, path: Path, provenance: dict, generated_at: datetime | None = None) -> None:
    check_columns(df)
    payload = {
        "generated_at": (generated_at or utcnow()).isoformat(),
        "provenance": provenance,
        "min_cell_size": MIN_CELL,
        "rows": json.loads(df.to_json(orient="records", date_format="iso")),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
