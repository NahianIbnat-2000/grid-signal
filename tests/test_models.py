import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from models.baselines import LABELS, Vader, load_dynasent, train_tfidf
from models.evaluate import cluster_bootstrap_ci, paired_difference, point_metrics

POS = ["great drive", "brilliant race", "amazing win, so happy", "love this team", "fantastic overtake"]
NEG = ["terrible strategy", "awful pit stop", "worst race ever", "so disappointing", "hate this penalty"]
NEU = ["the race starts at 3pm", "who got pole", "lap 12 pit stop", "the car is red", "next race is monaco"]


def _write_dynasent(root, n=12):
    root.mkdir(parents=True, exist_ok=True)
    for split in ("train", "test"):
        rows = []
        for i in range(n):
            for lab, src in (("positive", POS), ("negative", NEG), ("neutral", NEU)):
                rows.append({"sentence": f"{src[i % 5]} {i}", "gold_label": lab})
        rows += [{"sentence": "meh but ok", "gold_label": None}, {"sentence": "good and bad", "gold_label": "mixed"}]
        p = root / f"dynasent-v1.1-round02-dynabench-{split}.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def test_dynasent_loader_drops_unlabelled_and_mixed(tmp_path):
    _write_dynasent(tmp_path)
    df = load_dynasent("train", (2,), root=tmp_path)
    assert set(df.gold_label) == set(LABELS) and len(df) == 36


def test_dynasent_missing_files_give_clear_message(tmp_path):
    with pytest.raises(SystemExit, match="Download"):
        load_dynasent("train", (2,), root=tmp_path)


def test_vader_basic_and_tuning():
    v = Vader()
    assert list(v.predict(["What a brilliant drive!", "This is awful.", "Lap 12."])) == ["positive", "negative", "neutral"]
    vt = v.tune(POS + NEG + NEU, ["positive"] * 5 + ["negative"] * 5 + ["neutral"] * 5)
    assert 0.05 <= vt.pos <= 0.7 and vt.neg == -vt.pos


def test_tfidf_models_learn_toy_data(tmp_path):
    _write_dynasent(tmp_path)
    tr = load_dynasent("train", (2,), root=tmp_path)
    for kind in ("logreg", "svm"):
        m = train_tfidf(kind, tr)
        assert set(m.predict(["brilliant race 99", "awful pit stop 99"])) <= set(LABELS)


def test_point_metrics_known_values():
    g = ["positive", "negative", "neutral", "positive"]
    p = ["positive", "negative", "positive", "positive"]
    m = point_metrics(g, p)
    assert m["accuracy"] == 0.75
    # F1: pos 0.8, neg 1.0, neu 0.0 -> macro 0.6
    assert m["macro_f1"] == pytest.approx(0.6)
    assert sum(map(sum, m["confusion"]["matrix"])) == 4


def test_bootstrap_ci_and_paired_difference():
    rng = np.random.default_rng(1)
    g = rng.choice(LABELS, 300)
    good = np.where(rng.random(300) < 0.8, g, rng.choice(LABELS, 300))
    bad = rng.choice(LABELS, 300)
    races = np.repeat([f"r{i}" for i in range(10)], 30)
    lo, hi = cluster_bootstrap_ci(g, good, races, reps=300)
    pm = point_metrics(g, good)["macro_f1"]
    assert lo <= pm <= hi
    same = paired_difference(g, good, good, races, reps=200)
    assert same["diff"] == 0 and same["ci95"] == [0.0, 0.0]
    d = paired_difference(g, good, bad, races, reps=300)
    assert d["diff"] > 0.3 and d["ci95"][0] > 0


def test_run_baselines_end_to_end(tmp_path, monkeypatch):
    """Full run on fake labels + fake DynaSent; output must contain no comment text."""
    monkeypatch.chdir(tmp_path)
    _write_dynasent(tmp_path / "data/external/dynasent")
    rng = np.random.default_rng(0)
    rows, meta, labels = [], [], []
    for i in range(240):
        lab = LABELS[i % 3]
        src = {"positive": POS, "negative": NEG, "neutral": NEU}[lab]
        rid = f"c{i}"
        rows.append({"record_id": rid, "video_id": "v", "text": f"SECRET {src[i % 5]}"})
        meta.append({"record_id": rid, "split": "dev" if i < 80 else "test", "gp_key": f"gp{i % 8}",
                     "video_type": "race_highlights", "has_entity": bool(i % 2), "weight": 1.0 + i % 3,
                     "agreement": False})
        labels.append({"record_id": rid, "overall": lab, "sarcasm": "", "unsure": ""})
    (tmp_path / "data/restricted/annotation").mkdir(parents=True)
    pd.DataFrame(rows).to_parquet(tmp_path / "data/restricted/texts.parquet")
    pd.DataFrame(meta).to_parquet(tmp_path / "data/restricted/annotation/batch_01_meta.parquet")
    pd.DataFrame(labels).to_parquet(tmp_path / "data/restricted/annotation/labels_batch_01.parquet")
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    env = {**__import__("os").environ, "PYTHONPATH": str(repo)}
    r = subprocess.run([sys.executable, "-m", "models.run_baselines", "--split", "test"],
                       capture_output=True, text=True, env=env)
    assert r.returncode != 0 and "--final" in (r.stdout + r.stderr)
    r = subprocess.run([sys.executable, "-m", "models.run_baselines", "--split", "test", "--final",
                        "--reps", "50"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    out = (tmp_path / "research/results/baselines_test.json").read_text()
    assert "SECRET" not in out
    res = json.loads(out)
    assert set(res["models"]) == {"vader", "vader_tuned", "tfidf_logreg", "tfidf_svm"}
    assert res["counts"]["scored_3class"] == 160 and res["races"] == 8
    assert (tmp_path / "research/results/test_runs.log").read_text().count("baselines") == 1


def test_run_with_transformers_uses_same_items(tmp_path, monkeypatch):
    """--transformers path, with fake models injected (no download)."""
    import models.transformer_models as tm
    from models import run_baselines
    monkeypatch.chdir(tmp_path)
    _write_dynasent(tmp_path / "data/external/dynasent")
    rows, meta, labels = [], [], []
    for i in range(120):
        lab = LABELS[i % 3]
        rid = f"c{i}"
        rows.append({"record_id": rid, "video_id": "v", "text": f"{lab} text {i}"})
        meta.append({"record_id": rid, "split": "dev", "gp_key": f"gp{i % 6}", "video_type": "race_highlights",
                     "has_entity": False, "weight": 1.0, "agreement": False})
        labels.append({"record_id": rid, "overall": lab, "sarcasm": "", "unsure": ""})
    (tmp_path / "data/restricted/annotation").mkdir(parents=True)
    pd.DataFrame(rows).to_parquet(tmp_path / "data/restricted/texts.parquet")
    pd.DataFrame(meta).to_parquet(tmp_path / "data/restricted/annotation/batch_01_meta.parquet")
    pd.DataFrame(labels).to_parquet(tmp_path / "data/restricted/annotation/labels_batch_01.parquet")

    def oracle(texts):  # perfect fake 3-class model
        return np.array([[t.startswith(l) * 0.9 + 0.05 for l in LABELS] for t in texts]), LABELS
    fake = tm.HFSentiment("roberta_twitter", "fake", _proba_fn=oracle)
    monkeypatch.setattr(tm, "default_models", lambda d=None: [fake])
    monkeypatch.setattr(sys, "argv", ["x", "--split", "dev", "--transformers", "--reps", "30"])
    run_baselines.main()
    res = json.loads((tmp_path / "research/results/baselines_dev.json").read_text())
    assert res["models"]["roberta_twitter"]["sample"]["macro_f1"] == pytest.approx(1.0)
    assert res["models"]["roberta_twitter"]["licence"] == "CC BY 4.0"
    assert "roberta_twitter - vader" in res["comparisons"]
