"""Build, read back and check the annotation workbook.

Commands (run from the repo root):
  python -m annotation.workbook sample            # make data/restricted/annotation/batch_01.xlsx
  python -m annotation.workbook load batch_01      # validate + save labels
  python -m annotation.workbook relabel            # blind re-label set (>= 14 days later)
  python -m annotation.workbook load relabel_01
  python -m annotation.workbook agreement          # Cohen's kappa, first vs re-label

Design
- Split by RACE, not by comment: 6 dev races, 18 test races (seeded). No race
  appears in both, so a model tuned on dev never sees a test event.
- Only the 4 core video types (balanced across races). Sprints are left out.
- Per race x video type: up to `per_cell` comments, half that mention a
  driver/team (if available) and half that do not. Exact duplicates removed.
- Each item stores a sampling weight (cell size / sampled), so metrics can be
  reported both on the sample and re-weighted to the collected population.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from pipelines import store
from pipelines.pilot_stats import ENTITY_RE
from pipelines.preprocess import dedup_key
from pipelines.schemas import utcnow

ROOT = Path("data/restricted/annotation")
SPLIT_FILE = Path("data/manifests/annotation_split.yaml")
GUIDE_VERSION = "1.0"
CORE_TYPES = ["qualifying_highlights", "qualifying_reactions", "race_highlights", "race_reactions"]

OVERALL = ["positive", "negative", "neutral", "mixed", "off_topic"]
YESNO = ["yes", "no"]
TSENT = ["positive", "negative", "neutral"]
TARGETS = [
    "Verstappen", "Tsunoda", "Lawson", "Norris", "Piastri", "Leclerc", "Hamilton", "Russell",
    "Antonelli", "Alonso", "Stroll", "Gasly", "Doohan", "Colapinto", "Ocon", "Bearman", "Albon",
    "Sainz", "Hulkenberg", "Bortoleto", "Hadjar", "Perez",
    "Red Bull", "McLaren", "Ferrari", "Mercedes", "Aston Martin", "Alpine", "Haas", "Williams",
    "Sauber", "Racing Bulls", "FIA/Stewards", "F1 (sport/organisers)", "Other driver/team",
]
LABEL_COLS = ["overall", "sarcasm", "target_1", "target_1_sent", "target_2", "target_2_sent",
              "target_3", "target_3_sent", "unsure", "notes"]


# ---------------------------------------------------------------- split
def make_split(gp_keys: list[str], n_dev: int = 6, seed: int = 2025) -> dict:
    keys = sorted(gp_keys)
    rng = random.Random(seed)
    dev = sorted(rng.sample(keys, n_dev))
    return {"seed": seed, "dev": dev, "test": [k for k in keys if k not in dev]}


def load_or_create_split(gp_keys: list[str]) -> dict:
    if SPLIT_FILE.exists():
        return yaml.safe_load(SPLIT_FILE.read_text())
    split = make_split(gp_keys)
    SPLIT_FILE.write_text("# Race-level split for annotation. Fixed once; never edit after labelling starts.\n"
                          + yaml.safe_dump(split, sort_keys=False))
    return split


# ---------------------------------------------------------------- sample
def draw_sample(texts: pd.DataFrame, sources: pd.DataFrame, split: dict,
                per_cell: dict[str, int], seed: int = 7, n_agreement: int = 150) -> pd.DataFrame:
    df = texts.merge(sources[["video_id", "video_type", "gp_key"]], on="video_id")
    df = df[df["video_type"].isin(CORE_TYPES) & df["text"].notna()].copy()
    df["dkey"] = df["text"].map(dedup_key)
    df = df.drop_duplicates("dkey")
    df["has_entity"] = df["text"].str.contains(ENTITY_RE)
    df["split"] = np.where(df["gp_key"].isin(split["dev"]), "dev",
                           np.where(df["gp_key"].isin(split["test"]), "test", None))
    df = df[df["split"].notna()]

    rng = np.random.default_rng(seed)
    parts = []
    for (sp, gp, vt), cell in df.groupby(["split", "gp_key", "video_type"]):
        n = per_cell[sp]
        ent, non = cell[cell.has_entity], cell[~cell.has_entity]
        k_ent = min(len(ent), n // 2)
        k_non = min(len(non), n - k_ent)
        k_ent = min(len(ent), n - k_non)  # top up from entity stratum if non-entity ran short
        for stratum, k in ((ent, k_ent), (non, k_non)):
            if k == 0:
                continue
            pick = stratum.iloc[rng.choice(len(stratum), size=k, replace=False)].copy()
            pick["weight"] = len(stratum) / k
            parts.append(pick)
    s = pd.concat(parts, ignore_index=True)
    s = s.sample(frac=1, random_state=seed).reset_index(drop=True)  # random order hides race/type
    s["item"] = np.arange(1, len(s) + 1)
    test_idx = s.index[s["split"] == "test"]
    agree = rng.choice(test_idx, size=min(n_agreement, len(test_idx)), replace=False)
    s["agreement"] = s.index.isin(agree)
    return s[["item", "record_id", "split", "gp_key", "video_type", "has_entity",
              "weight", "agreement", "text"]]


# ---------------------------------------------------------------- workbook io
def write_workbook(sample: pd.DataFrame, path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "label"
    head = ["item", "record_id", "grand_prix", "video_type", "comment"] + LABEL_COLS
    ws.append(head)
    for r in sample.itertuples():
        ws.append([r.item, r.record_id, r.gp_key.title(), r.video_type.replace("_", " "), r.text]
                  + [""] * len(LABEL_COLS))

    lists = wb.create_sheet("lists")
    for j, (name, vals) in enumerate([("overall", OVERALL), ("yesno", YESNO),
                                      ("tsent", TSENT), ("targets", TARGETS)], start=1):
        for i, v in enumerate(vals, start=1):
            lists.cell(row=i, column=j, value=v)
    lists.sheet_state = "hidden"
    col = {h: i + 1 for i, h in enumerate(head)}
    n = len(sample) + 1

    def dv(ref_col: int, rng: str) -> None:
        from openpyxl.utils import get_column_letter
        v = DataValidation(type="list", formula1=rng, allow_blank=True)
        ws.add_data_validation(v)
        L = get_column_letter(ref_col)
        v.add(f"{L}2:{L}{n}")

    dv(col["overall"], f"=lists!$A$1:$A${len(OVERALL)}")
    dv(col["sarcasm"], f"=lists!$B$1:$B${len(YESNO)}")
    dv(col["unsure"], f"=lists!$B$1:$B${len(YESNO)}")
    for k in (1, 2, 3):
        dv(col[f"target_{k}"], f"=lists!$D$1:$D${len(TARGETS)}")
        dv(col[f"target_{k}_sent"], f"=lists!$C$1:$C${len(TSENT)}")

    widths = {"item": 6, "record_id": 4, "grand_prix": 18, "video_type": 16, "comment": 70, "notes": 24}
    from openpyxl.utils import get_column_letter
    for h, i in col.items():
        ws.column_dimensions[get_column_letter(i)].width = widths.get(h, 13)
    ws.column_dimensions["B"].hidden = True
    for row in ws.iter_rows(min_row=2, min_col=col["comment"], max_col=col["comment"]):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="DDE3EA")
    ws.freeze_panes = "F2"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def read_workbook(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="label", dtype=str).fillna("")
    for c in df.columns:
        df[c] = df[c].str.strip()
    return df


def started(df: pd.DataFrame) -> pd.Series:
    """Rows where any label cell has been filled in."""
    return (df[LABEL_COLS] != "").any(axis=1)


def validate(df: pd.DataFrame) -> list[str]:
    """Check only rows that have been started; untouched rows are just 'not yet'."""
    errs = []
    for r in df[started(df)].itertuples():
        i = r.item
        if r.overall not in OVERALL:
            errs.append(f"item {i}: overall missing/invalid ({r.overall!r})")
        if r.sarcasm not in ("", *YESNO):
            errs.append(f"item {i}: sarcasm must be yes/no")
        for k in (1, 2, 3):
            t, s = getattr(r, f"target_{k}"), getattr(r, f"target_{k}_sent")
            if t and t not in TARGETS:
                errs.append(f"item {i}: target_{k} not in list ({t!r})")
            if bool(t) != bool(s):
                errs.append(f"item {i}: target_{k} and target_{k}_sent must both be filled or both empty")
            if s and s not in TSENT:
                errs.append(f"item {i}: target_{k}_sent invalid ({s!r})")
        ts = [getattr(r, f"target_{k}") for k in (1, 2, 3) if getattr(r, f"target_{k}")]
        if len(ts) != len(set(ts)):
            errs.append(f"item {i}: same target listed twice")
    return errs


# ---------------------------------------------------------------- agreement
def cohen_kappa(a: list[str], b: list[str]) -> float:
    a, b = np.asarray(a), np.asarray(b)
    cats = sorted(set(a) | set(b))
    po = float(np.mean(a == b))
    pe = sum(float(np.mean(a == c)) * float(np.mean(b == c)) for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


# ---------------------------------------------------------------- cli
def cmd_sample(args) -> None:
    texts, sources = store.load("texts"), store.load("sources")
    if texts.empty:
        raise SystemExit("no comments collected; run the full-season collection first")
    status = store.load("video_status")
    core = sources[sources["video_type"].isin(CORE_TYPES)]
    if status.empty:
        raise SystemExit("no video_status found; run the collection first")
    open_vids = set(core["video_id"]) - set(status.loc[status["complete"], "video_id"])
    if open_vids:
        raise SystemExit(f"{len(open_vids)} core videos are not fully collected. Re-run "
                         "pipelines.collect until incomplete_videos is 0, then sample again.")
    gps = sorted(sources["gp_key"].dropna().unique())
    if len(gps) < 24:
        raise SystemExit(f"only {len(gps)} races collected; collect the full season before sampling")
    split = load_or_create_split(gps)
    s = draw_sample(texts, sources, split, per_cell={"dev": args.dev_per_cell, "test": args.test_per_cell})
    ROOT.mkdir(parents=True, exist_ok=True)
    s.drop(columns=["text"]).to_parquet(ROOT / "batch_01_meta.parquet", index=False)
    write_workbook(s, ROOT / "batch_01.xlsx")
    print(f"batch_01.xlsx: {len(s)} items | dev {int((s.split == 'dev').sum())} | "
          f"test {int((s.split == 'test').sum())} | agreement subset {int(s.agreement.sum())}")
    print("dev races:", ", ".join(split["dev"]))


def cmd_load(args) -> None:
    df = read_workbook(ROOT / f"{args.batch}.xlsx")
    errs = validate(df)
    done = df[df["overall"] != ""]
    print(f"{len(done)} of {len(df)} items labelled | {int(started(df).sum())} started")
    if errs:
        print(f"{len(errs)} problems:")
        print("\n".join(errs[:40]))
        if len(errs) > 40:
            print(f"... and {len(errs) - 40} more")
        if not args.partial:
            raise SystemExit("fix these in Excel and run again (or use --partial to save valid rows)")
    bad_items = {e.split(":")[0].split()[1] for e in errs}
    keep = done[~done["item"].isin(bad_items)].copy()
    keep = keep[["record_id"] + LABEL_COLS]
    keep["batch"], keep["guide_version"], keep["loaded_at"] = args.batch, GUIDE_VERSION, utcnow()
    out = ROOT / f"labels_{args.batch}.parquet"
    keep.to_parquet(out, index=False)
    print(f"saved {len(keep)} labels -> {out}")


def cmd_relabel(args) -> None:
    meta = pd.read_parquet(ROOT / "batch_01_meta.parquet")
    texts = store.load("texts")[["record_id", "text"]]
    sub = meta[meta["agreement"]].merge(texts, on="record_id")
    sub = sub.sample(frac=1, random_state=99).reset_index(drop=True)
    sub["item"] = np.arange(1, len(sub) + 1)
    write_workbook(sub, ROOT / "relabel_01.xlsx")
    print(f"relabel_01.xlsx: {len(sub)} items, new order. Do NOT open batch_01.xlsx while labelling.")


def cmd_agreement(args) -> None:
    a = pd.read_parquet(ROOT / "labels_batch_01.parquet")
    b = pd.read_parquet(ROOT / "labels_relabel_01.parquet")
    m = a.merge(b, on="record_id", suffixes=("_1", "_2"))
    print(f"items in both: {len(m)}")
    for c in ("overall", "sarcasm"):
        x, y = m[f"{c}_1"].replace("", "no" if c == "sarcasm" else ""), m[f"{c}_2"].replace(
            "", "no" if c == "sarcasm" else "")
        print(f"{c}: raw agreement {np.mean(x == y):.3f} | Cohen's kappa {cohen_kappa(list(x), list(y)):.3f}")
    print("Report this as INTRA-annotator agreement (same person, >= 14 days apart).")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("sample")
    p.add_argument("--dev-per-cell", type=int, default=8)    # 6 races x 4 types x 8  = 192
    p.add_argument("--test-per-cell", type=int, default=11)  # 18 races x 4 types x 11 = 792
    p.set_defaults(f=cmd_sample)
    p = sub.add_parser("load")
    p.add_argument("batch")
    p.add_argument("--partial", action="store_true")
    p.set_defaults(f=cmd_load)
    sub.add_parser("relabel").set_defaults(f=cmd_relabel)
    sub.add_parser("agreement").set_defaults(f=cmd_agreement)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
