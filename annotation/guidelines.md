# GRID SIGNAL Annotation Guide (v1.0)

Annotator: Nahian Ibnat (single annotator; see "Agreement" below)
Unit: one top-level YouTube comment, read together with its video context
(Grand Prix + video type, both shown in the workbook).

Read the comment once, decide, move on. If you need more than ~20 seconds,
pick the best label and tick `unsure`.

---

## 1. Overall sentiment (`overall`)

The writer's attitude toward the F1 subject of the comment. Not the topic.

| Label | Use when | Example (made up, for illustration) |
|---|---|---|
| `positive` | praise, joy, admiration, support | "What a drive from Hulkenberg, so deserved" |
| `negative` | criticism, anger, disappointment, mockery | "Ferrari strategy is a joke again" |
| `neutral` | facts, questions, predictions with no evaluation | "Who got the fastest lap?" |
| `mixed` | clear positive AND clear negative, neither dominates | "Great drive from Leclerc but Ferrari ruined it" |
| `off_topic` | not about F1 at all (spam, self-promotion, unrelated) | "Check my channel" |

Rules:
- **Sarcasm counts by meaning, not words.** "Great job Ferrari, another masterpiece" after a bad strategy = `negative`.
- **Banter with no evaluation** ("Smooth operator 🎵") = `neutral` unless the tone is clearly praise or mockery.
- **Emoji-only:** label the emoji's plain meaning (🔥 👏 🐐 = positive, 😭 💀 can be either; if unclear = `neutral` + `unsure`).
- **Non-English:** label if you understand it; otherwise `overall` = `neutral`, tick `unsure`, write `lang` in notes.
- **Questions with an edge** ("Why is Stroll still in F1?") = `negative`.
- **Prediction or hope** ("Lando will win the title") = `positive` toward Lando only if supportive in tone; plain forecasts = `neutral`.

## 2. Sarcasm (`sarcasm`)

`yes` if the literal words say the opposite of what is meant. `no` otherwise.
Irony about the sport in general ("F1 2025: where the pit wall plays chess
blindfolded") counts as `yes`.

## 3. Targets (`target_1` .. `target_3`, `target_1_sent` ..)

Fill only for drivers or teams the comment actually evaluates or mentions.

- Use the canonical name from the dropdown (surname for drivers, short team name).
- Nicknames count: "Max" -> Verstappen, "Checo" -> Perez, "Kimi" (2025) -> Antonelli
  unless clearly Raikkonen. If you cannot tell who is meant, skip the target.
- `target_k_sent` is the sentiment **toward that target**, using positive / negative / neutral.
- Up to 3 targets. More than 3: keep the three with the clearest evaluation.
- The FIA, stewards and race control are a target (`FIA/Stewards`).

Example: "Amazing drive from Leclerc, but Ferrari completely ruined the strategy."
overall = `mixed`; Leclerc = `positive`; Ferrari = `negative`.

## 4. Flags

- `unsure`: tick when you hesitated between two labels.
- `notes`: short reason for hard cases, or `lang`, `dup`, `context` (needs the video to understand).

## 5. Do not

- Do not look at model predictions before labelling.
- Do not open the video to "check" what happened; label from the comment plus the context column.
- Do not change the guide mid-batch. Write ideas in `notes`, then revise the guide between batches and bump the version.

## 6. Agreement (single annotator)

Inter-annotator agreement needs a second person. If one is available, they
label the `agreement` subset independently. Otherwise, re-label the same
subset blind after at least 14 days and report **intra-annotator** agreement
(Cohen's kappa), clearly named as such. This measures consistency, not
validity, and the limitation must be stated on the website.

## 7. Retention

The workbook contains comment text, so it lives in `data/restricted/` only and
falls under the 30-day rule. Your labels are keyed by comment ID and kept;
the text is re-fetched when needed. Comments deleted since labelling drop out
of the test set, and each evaluation reports the test-set size it used.
