# GRID SIGNAL: Phase 1 Data Feasibility Report

Status: draft, written 2026-11-23. No comment data has been collected yet.
Every policy point below links to the source page it came from. Re-check them
before collection starts, because YouTube changed these rules as recently as June 2026.

---

## 1. Verdict in one paragraph

The project is feasible at $0, but not in the form the brief assumes. YouTube
comments can be collected legally through the Data API, yet the comment text
can only be kept for 30 days, and keeping sentiment results longer than that
needs YouTube's approval through an amendment process. Policies say nothing
about training models on comments, so the safe reading is: use YouTube
comments for inference and evaluation only, never for fine-tuning. That
reshapes RQ4 and the benchmark design. RQ5 (media framing) has no licensed
corpus and should be dropped from the first release.

---

## 2. Primary source: YouTube Data API v3

### 2.1 Quota (checked 2026-11-23)
Source: https://developers.google.com/youtube/v3/determine_quota_cost

| Item | Value |
|---|---|
| Default daily pool | 10,000 units, resets midnight Pacific Time |
| `commentThreads.list` | 1 unit per call, up to 100 comments per page |
| `comments.list` (refresh by ID) | 1 unit per call, up to 50 IDs |
| `playlistItems.list` (channel uploads) | 1 unit per call, 50 videos per page |
| `search.list` | own bucket: 100 calls/day |
| Failed requests | still cost at least 1 unit |

Design consequence: do not use `search.list` to find videos. List each
channel's uploads playlist instead. It is cheaper and it is a cleaner
sampling frame, because YouTube search ranking is opaque.

Capacity formula (fill in after the dry run):

```
collection_units  ≈ videos + Σ_v ceil(comments_v / 100)
refresh_units/30d ≈ ceil(total_stored_comments / 50)
```

Comment volume per video is unknown until the dry run. Do not assume a number.

### 2.2 Storage and retention
Source: https://developers.google.com/youtube/terms/developer-policies (III.E.4)

- Data obtained without a user's OAuth consent (our case) may be stored
  only temporarily and for no more than 30 days. After that it must be
  deleted or refreshed.
- Users can ask for their data to be deleted; that must happen within 7 days.
- III.E.4.h: you must not use API data to create new derived metrics or
  scores, except under the rules below. Any number you show alongside
  YouTube data must be clearly labelled as your own calculation.

### 2.3 Derived metrics (new since June 2026)
Source: https://developers.google.com/youtube/terms/derived-metrics-policy

- Viewer sentiment analysis, including NLP on comments fetched via the
  Data API, is a listed allowed use.
- Derived metrics such as sentiment may be stored for up to 36 months.
  Comment text, titles and descriptions still follow the 30-day rule.
- This exception applies only after you accept the Developer Policies
  amendment, choosing "Analytics & Reporting" as the use case. The revision
  history describes it as for developers who have explicitly applied.
- Sentiment must not be used to profile users by protected attributes.

**Gate:** before any collection beyond a small pilot, submit the API
Compliance Audit / amendment form and keep the approval email in the repo
(without credentials). Without approval, every published sentiment number
would need to be recomputed every 30 days, and historical trends could not
legally be stored.

### 2.4 Machine learning and training
Neither the Developer Policies nor the derived-metrics page addresses
training models on comment text. YouTube has a separate creator opt-in for
third-party AI training on *videos*
(https://support.google.com/youtube/answer/15509945), which does not cover
comments. Under the brief's own rule ("analysis permission is not training
permission"), comments are **not used for fine-tuning**.

### 2.5 Combining with race data
III.E.4.h requires that non-YouTube data shown next to YouTube data is clearly
labelled. Event-time alignment with Jolpica race dates is fine as long as the
site says which numbers come from where. Flag this use in the audit form so
YouTube can object early.

### 2.6 Historical coverage
Comments on old videos stay available unless deleted, so the 2025 season can
be studied now. But: (a) comments are fetched today, so deleted comments are
missing and the gap is likely larger around controversial events (that is a
non-random missingness problem for RQ3); (b) a comment's date is when it was
posted, not when the video went up, so event windows must use comment
`publishedAt`; (c) replies beyond the first few per thread need extra calls.

---

## 3. Event metadata: Jolpica-F1 (via FastF1 or direct)
Source: https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md

- Free for non-commercial use. Data licence CC BY-NC-SA 4.0, so published
  calendar files must carry the same licence and attribution.
- Rate limits: 4 requests/second, 500/hour, with a note that limits will drop.
- Older races have no start time; the pipeline flags these so they are not
  used for hour-level event windows.
- Race incidents (penalties, crashes) are **not** in Jolpica. The event list
  for RQ3 and event studies must be built by hand from FIA stewards'
  decision documents, with a link per event.

---

## 4. Secondary text datasets

| Candidate | Finding | Decision |
|---|---|---|
| `Malekith/twitter_f1` (Hugging Face) | Team/driver account tweets, no licence stated | Reject |
| SportsOri (Zenodo 15599619) | ~43k YouTube comments on controversial sports events, redistributed | Reject for training: upstream 30-day rule |
| `kcrl/Sports-Comment` (HF, MIT) | Small, provenance not yet checked | Check source before use |
| Reddit r/formula1 | Needs Reddit for Researchers approval | Out of scope |

No licensed, F1-specific, labelled training set was found. Following the
brief's fallback: train classical baselines on a general-domain corpus with
an explicit licence that allows training, then evaluate everything on a
small F1 set you annotate yourself. Licence check of the general corpus is
still open (several popular ones, such as tweet-based sets, inherit platform
terms).

### Pretrained checkpoints
- `cardiffnlp/twitter-roberta-base-sentiment-latest`: 3-class, widely used,
  but the model card showed no licence tag when checked. Evaluate only until
  confirmed.
- Any SST-2 model (e.g. DistilBERT SST-2) is **binary**. It cannot output
  "neutral", so a 3-class comparison against it is unfair unless you
  threshold it and report that choice.

---

## 5. Problems with the brief itself (critical read)

1. **Scope.** Five RQs, 11 pages and a framing corpus is a team-year. For
   one person, a credible v1 is RQ1 + RQ3 + RQ4 on one season.
2. **The test set cannot be frozen.** Text expires after 30 days, and others
   can never download it. Store comment IDs and your labels; re-fetch text
   to re-run models; report the benchmark's size at each run, since
   deletions will shrink it. Annotate within the window.
3. **One annotator.** Inter-annotator agreement needs a second person on at
   least 150 to 200 items. If you cannot get one, do a blind re-label of a
   subset two weeks later and report intra-annotator agreement, clearly
   named as such.
4. **Polarization needs stance, not just sentiment.** "Negative about the
   stewards" and "negative about Verstappen" can be the same side. Without a
   stance label per event, the index measures mixed sentiment, not
   polarization. Existing measures to build on: Esteban and Ray (1994,
   Econometrica) for polarization, and van der Eijk (2001, Quality &
   Quantity) agreement index for ordered scales.
5. **Event studies.** Comment volume follows video upload timing, which
   follows the race schedule. Without a control (e.g. same window on races
   with no incident), before/after changes say little.
6. **Selection.** Official channel comment sections are moderated, and
   ranking is irrelevant here only because the pipeline uses `order=time`.
   Moderation and deletions still bias toward milder text.

---

## 6. Feasibility deliverable checklist

| # | Item | Status |
|---|---|---|
| 1 | Primary permitted source | YouTube Data API, own key |
| 2 | Approved uses | Inference + evaluation; no training; 30-day text; derived storage pending amendment |
| 3 | Confirmed obtainable observations | **Not yet.** Run the dry run (section 7) |
| 4 | Historical coverage | 2025 season, minus deleted comments |
| 5 | Sampling limitations | Section 2.6 and 5.6 |
| 6 | Access requirements | Google Cloud project + API key; amendment approval |
| 7 | Initial research sample | Pilot: 3 races × all channels in frame |
| 8 | Zero cost | Yes: default quota, GitHub Pages, Colab/local for models |

---

## 7. Next steps (in order)

1. Create a Google Cloud project, enable YouTube Data API v3, put the key in `.env`.
2. Fill in the other channels in `data/manifests/sampling_frame.yaml`.
3. `python -m pipelines.collect --frame data/manifests/sampling_frame.yaml --dry-run`
   to count selected videos (cheap: uploads pages only).
4. Submit the amendment / audit form, describing GRID SIGNAL as a
   non-commercial analytics and research site.
5. Pilot collection on 3 races with `--max-comment-pages 5`, then fill in
   item 3 above with real counts.
6. Only then start Phase 2 (annotation guide, baselines).
