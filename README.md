# GRID SIGNAL

**Beyond the Race. Decode the Reaction.**

An independent NLP research observatory on sentiment, narratives and
disagreement in Formula 1 online discussion. Not affiliated with or endorsed
by Formula 1, the FIA, any team, or YouTube.

## Status: Phase 1 done, Phase 2 (annotation) starting

| Component | State |
|---|---|
| Feasibility report | Draft: `docs/feasibility_report.md` |
| Data access register | `data/manifests/data_access_register.yaml` |
| YouTube ingestion (quota, pagination, backoff, dedup) | Built, tested offline, **not yet run on real data** |
| 30-day retention + refresh | Built, tested offline |
| Jolpica race calendar | Built, tested offline |
| Privacy-safe aggregate export | Built, tested offline |
| Annotation guide v1.0 + labelling workbook + agreement check | Built, tested offline |
| Pilot (3 races, 12 videos) | Collected; diagnostics only, not findings |
| Models, topics, controversy index, website | Not started |

No findings exist yet. Nothing in this repo is a result.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add YOUTUBE_API_KEY, never commit it
export $(cat .env | xargs)
python -m pytest -q             # offline, no key needed
```

## Run

```bash
python -m pipelines.events 2025                    # race calendar (CC BY-NC-SA 4.0)
python -m pipelines.collect --frame data/manifests/sampling_frame.yaml --dry-run
python -m pipelines.collect --frame data/manifests/sampling_frame.yaml --max-comment-pages 5
python -m pipelines.retention refresh              # run at least every 30 days
```

Raw data lives in `data/restricted/` (gitignored). Only
`pipelines/export.py` writes public files, and it refuses text or author
fields and suppresses groups with fewer than 10 comments.
