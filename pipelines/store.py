"""Local restricted store (Parquet). Lives in data/restricted/, which is gitignored.

Nothing here is ever published. Only pipelines/export.py writes public files.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RESTRICTED = Path("data/restricted")


def _path(name: str, root: Path) -> Path:
    return root / f"{name}.parquet"


def load(name: str, root: Path = RESTRICTED) -> pd.DataFrame:
    p = _path(name, root)
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def upsert(name: str, df: pd.DataFrame, key: str, root: Path = RESTRICTED) -> pd.DataFrame:
    """Insert new rows, replace rows with the same key (latest wins)."""
    root.mkdir(parents=True, exist_ok=True)
    old = load(name, root)
    merged = pd.concat([old, df], ignore_index=True) if not old.empty else df.copy()
    merged = merged.drop_duplicates(subset=[key], keep="last").reset_index(drop=True)
    merged.to_parquet(_path(name, root), index=False)
    return merged


def save(name: str, df: pd.DataFrame, root: Path = RESTRICTED) -> None:
    root.mkdir(parents=True, exist_ok=True)
    df.to_parquet(_path(name, root), index=False)
