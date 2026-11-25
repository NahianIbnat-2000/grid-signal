import numpy as np
import pandas as pd
import pytest

from annotation import workbook as wbk


def _fake(n_races=24, per_vid=40):
    gps = [f"race {i:02d} grand prix" for i in range(n_races)]
    src, txt = [], []
    for g in gps:
        for vt in wbk.CORE_TYPES + ["sprint_highlights"]:
            vid = f"{g}|{vt}"
            src.append({"video_id": vid, "video_type": vt, "gp_key": g})
            for k in range(per_vid):
                body = f"Norris drove well lap {k} {vid}" if k % 3 == 0 else f"what a race number {k} {vid}"
                txt.append({"record_id": f"{vid}#{k}", "video_id": vid, "text": body})
    txt.append({"record_id": "dupe", "video_id": src[0]["video_id"], "text": txt[1]["text"]})
    return pd.DataFrame(txt), pd.DataFrame(src), gps


def test_split_is_by_race_and_disjoint():
    _, _, gps = _fake()
    sp = wbk.make_split(gps)
    assert len(sp["dev"]) == 6 and len(sp["test"]) == 18
    assert not set(sp["dev"]) & set(sp["test"])
    assert wbk.make_split(gps) == sp  # deterministic


def test_sample_sizes_strata_weights_and_no_leakage():
    t, s, gps = _fake()
    sp = wbk.make_split(gps)
    out = wbk.draw_sample(t, s, sp, per_cell={"dev": 8, "test": 11})
    assert (out.split == "dev").sum() == 6 * 4 * 8
    assert (out.split == "test").sum() == 18 * 4 * 11
    assert "sprint_highlights" not in set(out.video_type)
    assert "dupe" not in set(out.record_id)
    assert set(out[out.split == "dev"].gp_key) <= set(sp["dev"])
    assert out.agreement.sum() == 150 and set(out[out.agreement].split) == {"test"}
    # entity stratum (1/3 of comments) is over-sampled to ~half, so its weight is lower
    w = out.groupby("has_entity").weight.mean()
    assert w[True] < w[False]
    assert out.record_id.is_unique


def test_workbook_roundtrip_and_validation(tmp_path):
    t, s, gps = _fake(per_vid=6)
    out = wbk.draw_sample(t, s, wbk.make_split(gps), per_cell={"dev": 2, "test": 2}).head(3)
    p = tmp_path / "b.xlsx"
    wbk.write_workbook(out, p)
    from openpyxl import load_workbook
    wb = load_workbook(p)
    ws = wb["label"]
    hdr = [c.value for c in ws[1]]
    ws.cell(row=2, column=hdr.index("overall") + 1, value="mixed")
    ws.cell(row=2, column=hdr.index("target_1") + 1, value="Leclerc")
    ws.cell(row=2, column=hdr.index("target_1_sent") + 1, value="positive")
    ws.cell(row=3, column=hdr.index("overall") + 1, value="angry")          # invalid
    ws.cell(row=4, column=hdr.index("overall") + 1, value="negative")
    ws.cell(row=4, column=hdr.index("target_1") + 1, value="Ferrari")       # missing sentiment
    wb.save(p)
    df = wbk.read_workbook(p)
    errs = wbk.validate(df)
    assert any("item 2" in e and "overall" in e for e in errs)
    assert len(errs) == 2  # untouched rows (none here) would not be reported
    assert any("item 3" in e and "target_1" in e for e in errs)
    assert not any(e.startswith("item 1:") for e in errs)
    assert len(ws.data_validations.dataValidation) >= 8


def test_cohen_kappa_known_values():
    assert wbk.cohen_kappa(list("aabb"), list("aabb")) == pytest.approx(1.0)
    # classic example: po=0.7, pe=0.5 -> 0.4
    a = ["y"] * 5 + ["n"] * 5
    b = ["y"] * 4 + ["n"] + ["y"] * 2 + ["n"] * 3
    assert wbk.cohen_kappa(a, b) == pytest.approx((0.7 - 0.5) / 0.5)


def test_untouched_rows_are_not_errors():
    df = pd.DataFrame([{**{c: "" for c in wbk.LABEL_COLS}, "item": "1"},
                       {**{c: "" for c in wbk.LABEL_COLS}, "item": "2", "overall": "neutral"}])
    assert wbk.validate(df) == []
