# GRID SIGNAL · The Signal Room redesign: audit & change log

## Phase 1 · Audit (before changes)
| Area | Finding | Decision |
|---|---|---|
| Data layer (6 result JSON files) | Real, aggregate-only, provenance fields present | **Kept unchanged**; no numbers altered |
| Charts | Fixed viewBox: text shrank on phones | Rebuilt to render at real container width |
| Navigation | Overflowed on phones | Mobile menu button + stacked menu |
| Brief's sentiment colours | `#279B80` vs `#8B96A3` fails CVD (ΔE 5.1); green vs coral-red ΔE 6.0 light / 4.8 dark | Kept hues, lightened neutral to `#C3CAD2`; **every sentiment mark also carries a shape (▲ ● ▼) and label**; pos-vs-neg never encoded by colour alone on dark panels |
| Driver/team, source category, stance, incident markers | No data in the pipeline | Shown as "Not available yet" status, never simulated |
| Driver Storylines | Needs target-aware sentiment (not built) | Page shipped with status "Data pending" and a requirements table |

## Phase 2 · Design system (`website/src/styles.css`)
Tokens: Midnight Ink `#101820`, Editorial Ivory `#F5F3EE`, Signal Coral `#F05A59` (actions/emphasis only), Telemetry Cyan `#42B8C6` (comparative series).
Type: Space Grotesk (display), Inter (body), IBM Plex Mono with tabular numerals (metrics/labels).
Components (`components/ui.tsx`): Wordmark + glyph, Status indicators (available / incomplete / unavailable / updated / experimental),
Evidence drawers, Signal cards, dark page heads. `prefers-reduced-motion` disables all transitions and the hero wave.

## Phase 3 · Homepage
Dark hero (wordmark, headline, brief's description, "Explore the Signals" / "Read the Research"), ambient wave drawn from real net sentiment,
compact Signal Monitor preview, then 01 Conversation / 02 Narrative / 03 Divide / 04 Intelligence in four different compositions.

## Phase 4 · Dashboards
- **Signal Monitor** (`/monitor`): volume, sentiment (net or negative, 95% band), disagreement (with intervals) and a chosen topic on one round axis;
  click/keyboard selection highlights all lanes; compare control; round range; weekend-stage panel; table view; evidence drawer.
- **Sentiment Observatory**: signal cards (source, sample, model, last update); prevalence and volume on separate charts.
- **Controversy Radar**: dark header, formula + validation drawer, tiered ranking, two-event comparison (distributions, themes, volume, verdicts).
- **Narrative Explorer**: archive list + topic dossier (description, label status, prevalence, coverage, stability, top words), topic timeline, co-movement table, heatmap.
- **Model Arena**: research-evidence drawers (dataset, labels, provenance), "why F1 language is hard" panel, misclassification share computed from data.

## Phase 5 · Research pages
Sticky numbered table of contents, equations for the correction and disagreement measure, footnotes, status table.

## Phase 6 · Verification (run on the build in this commit)
- `npm run build`: TypeScript strict + Vite production build, no errors.
- Headless Chrome: all 8 routes at 1280 px and 390 px; no console errors (other than blocked web fonts in the build sandbox); no horizontal overflow on phones.
- Python test suite: 54 passed.

## Known limitations
- Charts are hand-built SVG; tooltips work on hover and keyboard focus, touch shows them on tap.
- Driver Storylines, event studies, media framing and stance remain pending (see Research › Completed & pending).
- Web fonts load from Google Fonts; system fonts are the fallback.
