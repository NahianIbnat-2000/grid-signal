"""Fine-tune DistilBERT on DynaSent Round 2 (general-domain, CC BY 4.0).

This is the ONLY fine-tuning in GRID SIGNAL. It uses no YouTube comments.
On the website it must be described as "fine-tuned on a general-domain
sentiment corpus", never as "fine-tuned on F1 data".

Run on free Google Colab (Runtime > Change runtime type > T4 GPU):

    !pip -q install transformers accelerate scikit-learn pandas
    # upload the 3 round02 .jsonl files to /content/dynasent/
    !python finetune_dynasent.py --data /content/dynasent --out /content/distilbert-dynasent

About 15-25 minutes on a T4. Then download the --out folder (zip it), unzip
it on your laptop into models/artifacts/distilbert-dynasent/ (gitignored) and run:

    python -m models.run_baselines --split dev --transformers --finetuned models/artifacts/distilbert-dynasent
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

LABELS = ["negative", "neutral", "positive"]
BASE = "distilbert/distilbert-base-uncased"  # Apache-2.0


def read(path: Path) -> tuple[list[str], list[int]]:
    texts, ys = [], []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("gold_label") in LABELS:
                texts.append(r["sentence"])
                ys.append(LABELS.index(r["gold_label"]))
    return texts, ys


def main() -> None:
    import torch
    from sklearn.metrics import f1_score
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer, Trainer,
                              TrainingArguments, set_seed)

    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    set_seed(a.seed)

    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE, num_labels=3, id2label=dict(enumerate(LABELS)), label2id={l: i for i, l in enumerate(LABELS)})

    class DS(torch.utils.data.Dataset):
        def __init__(self, split):
            self.x, self.y = read(a.data / f"dynasent-v1.1-round02-dynabench-{split}.jsonl")
            self.enc = tok(self.x, truncation=True, max_length=128)

        def __len__(self):
            return len(self.y)

        def __getitem__(self, i):
            return {**{k: v[i] for k, v in self.enc.items()}, "labels": self.y[i]}

    train, dev, test = DS("train"), DS("dev"), DS("test")

    def metrics(ev):
        pred = np.argmax(ev.predictions, axis=1)
        return {"macro_f1": f1_score(ev.label_ids, pred, average="macro")}

    args = TrainingArguments(
        output_dir=str(a.out / "_ckpt"), num_train_epochs=a.epochs, learning_rate=3e-5,
        per_device_train_batch_size=32, per_device_eval_batch_size=64, weight_decay=0.01,
        warmup_ratio=0.06, eval_strategy="epoch", save_strategy="epoch", load_best_model_at_end=True,
        metric_for_best_model="macro_f1", save_total_limit=1, seed=a.seed, report_to=[],
        fp16=torch.cuda.is_available())
    tr = Trainer(model=model, args=args, train_dataset=train, eval_dataset=dev,
                 processing_class=tok, compute_metrics=metrics)
    tr.train()
    res = {"dev": tr.evaluate(dev), "test": tr.evaluate(test), "base_model": BASE,
           "train_size": len(train), "seed": a.seed, "epochs": a.epochs,
           "data": "DynaSent v1.1 round 2 (CC BY 4.0)"}
    tr.save_model(str(a.out))
    tok.save_pretrained(str(a.out))
    (a.out / "training_summary.json").write_text(json.dumps(res, indent=2, default=float))
    print(json.dumps(res, indent=2, default=float))


if __name__ == "__main__":
    main()
