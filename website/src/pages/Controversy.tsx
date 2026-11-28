import { useMemo, useState } from "react";
import { ChartFrame, DistBar, DotCI, Scatter, SentimentLegend } from "../components/charts";
import { Evidence, PageHead, SignalCard, Status } from "../components/ui";
import { fmtInt, mean, pct, raceName, VIDEO_TYPES, type AllData, type ControversyRow } from "../data";

const tier = (r: ControversyRow) =>
  r.p_top3_disagreement >= 0.2 ? "Most divided" : r.p_top3_disagreement <= 0.01 ? "Least divided" : "Cannot be ranked reliably";
const ORDER = ["Most divided", "Cannot be ranked reliably", "Least divided"];
const TIER_COLOR: Record<string, string> = { "Most divided": "var(--coral)", "Cannot be ranked reliably": "var(--neu-ink)", "Least divided": "var(--series)" };
const overlap = (a: [number, number], b: [number, number]) => a[0] <= b[1] && b[0] <= a[1];

export default function Controversy({ data }: { data: AllData }) {
  const rows = [...data.controversy.rows].sort((a, b) => ORDER.indexOf(tier(a)) - ORDER.indexOf(tier(b)) || b.disagreement - a.disagreement);
  const [a, setA] = useState(rows[0].gp_key);
  const [b, setB] = useState(rows[rows.length - 1].gp_key);
  const ra = rows.find((r) => r.gp_key === a)!, rb = rows.find((r) => r.gp_key === b)!;

  // pooled (equal-weight) corrected shares per race from the sentiment table
  const pooled = useMemo(() => (gp: string) => {
    const rs = data.sentiment.rows.filter((r) => r.gp_key === gp && (VIDEO_TYPES as readonly string[]).includes(r.video_type));
    return { neg: mean(rs.map((r) => r.adj_negative)), neu: mean(rs.map((r) => r.adj_neutral)), pos: mean(rs.map((r) => r.adj_positive)) };
  }, [data]);
  const themes = data.topics.topics.filter((t) => t.show && t.kind === "theme");
  const topicShare = (gp: string, id: number) => mean(VIDEO_TYPES.map((vt) =>
    data.topics.prevalence.find((p) => p.gp_key === gp && p.video_type === vt && p.topic === id)?.share ?? 0));
  const topThemes = (gp: string) => themes.map((t) => ({ t, s: topicShare(gp, t.id) })).sort((x, y) => y.s - x.s).slice(0, 3);

  const metrics: [string, (r: ControversyRow) => string, (r: ControversyRow) => [number, number]][] = [
    ["Disagreement", (r) => r.disagreement.toFixed(2), (r) => r.disagreement_ci],
    ["Negativity", (r) => pct(r.negativity), (r) => r.negativity_ci],
    ["Net sentiment", (r) => `${(r.net_sentiment * 100).toFixed(0)} pts`, (r) => r.net_sentiment_ci],
  ];

  return (
    <>
      <PageHead kicker="RQ3 · Controversy" title="Controversy Radar" tagline="Not every negative reaction is a divided opinion.">
        <p className="lede">Which race weekends split the comment sections? GRID SIGNAL keeps attention, negativity and disagreement apart, and never merges
          them into one arbitrary score.</p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 18 }}>
          <Status kind="available">Negativity · positivity · disagreement · volume</Status>
          <Status kind="unavailable">Stance disagreement: not measured</Status>
        </div>
      </PageHead>

      <div className="wrap page" style={{ paddingTop: 40 }}>
        <div className="grid-4">
          <SignalCard title="Attention" value="Volume" context="Comments on the race's four core videos. Mostly audience size." />
          <SignalCard title="Negativity" value="▼ share" context="Corrected share of negative comments." />
          <SignalCard title="Positivity" value="▲ share" context="Corrected share of positive comments." />
          <SignalCard title="Disagreement" value="0 → 1" context="0 = everyone agrees; 1 = an even positive/negative split." />
        </div>
        <div className="eq" aria-label="disagreement formula">disagreement = p<sub>pos</sub> + p<sub>neg</sub> − (p<sub>pos</sub> − p<sub>neg</sub>)²
          <span className="muted" style={{ marginLeft: 16 }}>variance of a −1 / 0 / +1 score</span></div>
        <Evidence title="Validation of the disagreement measure" items={[
          ["All negative", "0.00: unanimous criticism is not disagreement"], ["50/50 split", "1.00"], ["80% negative, 20% neutral", "0.16"],
          ["Uncertainty", "1,000 bootstrap draws (labelled set + each video's comments); error rates per video type"],
          ["P(top 3)", "Share of draws in which a race ranks in the top three"]]} />

        <section className="section-sm">
          <ChartFrame title="Disagreement by race" sub="Marker = estimate; line = 95% interval. Grouped by stability of rank across 1,000 resamples."
            legend={<div className="legend">{ORDER.map((t) => <span key={t}><span className="sw" style={{ background: TIER_COLOR[t] }} />{t}
              {t === "Most divided" ? " (top 3 in ≥ 20%)" : t === "Least divided" ? " (≤ 1%)" : ""}</span>)}</div>}>
            <DotCI ariaLabel="disagreement by race" domain={[0.5, 1]} fmt={(x) => x.toFixed(1)} labelWidth={150}
              rows={rows.map((r) => ({ key: r.gp_key, label: raceName(r.gp_key), value: r.disagreement, lo: r.disagreement_ci[0], hi: r.disagreement_ci[1],
                group: tier(r), color: TIER_COLOR[tier(r)],
                tip: `${raceName(r.gp_key)} · ${tier(r)}\ndisagreement ${r.disagreement.toFixed(2)} [${r.disagreement_ci[0].toFixed(2)}–${r.disagreement_ci[1].toFixed(2)}]\ntop 3 in ${pct(r.p_top3_disagreement)} of resamples\nnegativity ${pct(r.negativity)} · ${fmtInt(r.attention)} comments` }))} />
            <details className="table-view"><summary>Show as table</summary><div className="table-scroll"><table>
              <thead><tr><th>Race</th><th>Group</th><th className="n">Disagreement</th><th className="n">95% CI</th><th className="n">P(top 3)</th><th className="n">Negativity</th><th className="n">Comments</th></tr></thead>
              <tbody>{rows.map((r) => <tr key={r.gp_key}><td>{raceName(r.gp_key)}</td><td>{tier(r)}</td><td className="n">{r.disagreement.toFixed(3)}</td>
                <td className="n">{r.disagreement_ci[0].toFixed(2)}–{r.disagreement_ci[1].toFixed(2)}</td><td className="n">{pct(r.p_top3_disagreement, 1)}</td>
                <td className="n">{pct(r.negativity)}</td><td className="n">{fmtInt(r.attention)}</td></tr>)}</tbody></table></div></details>
          </ChartFrame>
        </section>

        {/* event comparison */}
        <section className="section">
          <div className="kicker">Event comparison</div>
          <h2>Compare two race weekends</h2>
          <div className="controls">
            {([["Event A", a, setA], ["Event B", b, setB]] as const).map(([lab, v, set]) => (
              <div className="control" key={lab}><label htmlFor={lab}>{lab}</label>
                <select id={lab} value={v} onChange={(e) => set(e.target.value)}>
                  {[...rows].sort((x, y) => x.round - y.round).map((r) => <option key={r.gp_key} value={r.gp_key}>R{r.round} {raceName(r.gp_key)}</option>)}
                </select></div>))}
          </div>
          <div className="grid-2">
            {[ra, rb].map((r, i) => { const p = pooled(r.gp_key); return (
              <div className="card" key={i} style={{ borderTop: `3px solid ${i ? "var(--cyan)" : "var(--coral)"}` }}>
                <div className="label">Event {i ? "B" : "A"} · R{r.round}</div>
                <h3 style={{ marginTop: 6 }}>{raceName(r.gp_key)}</h3>
                <SentimentLegend />
                <DistBar neg={p.neg} neu={p.neu} pos={p.pos} labels height={18} />
                <div className="grid-2" style={{ gap: 12, marginTop: 16 }}>
                  <div><div className="label">Disagreement</div><div className="num" style={{ fontSize: "1.4rem" }}>{r.disagreement.toFixed(2)}</div></div>
                  <div><div className="label">Volume</div><div className="num" style={{ fontSize: "1.4rem" }}>{fmtInt(r.attention)}</div></div>
                </div>
                <div className="label" style={{ marginTop: 16 }}>Most discussed themes</div>
                <ol className="small" style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                  {topThemes(r.gp_key).map(({ t, s }) => <li key={t.id}>{t.name} <span className="num muted">{pct(s, 1)}</span></li>)}
                </ol>
              </div>); })}
          </div>
          <div className="card" style={{ marginTop: 20 }}>
            <table>
              <thead><tr><th>Measure</th><th className="n">{raceName(a)}</th><th className="n">{raceName(b)}</th><th className="n">Difference</th><th>Verdict</th></tr></thead>
              <tbody>{metrics.map(([name, show, ci]) => {
                const d = name === "Disagreement" ? ra.disagreement - rb.disagreement : name === "Negativity" ? ra.negativity - rb.negativity : ra.net_sentiment - rb.net_sentiment;
                return <tr key={name}><td>{name}</td>
                  <td className="n">{show(ra)}<br /><span className="muted small">[{ci(ra)[0].toFixed(2)}, {ci(ra)[1].toFixed(2)}]</span></td>
                  <td className="n">{show(rb)}<br /><span className="muted small">[{ci(rb)[0].toFixed(2)}, {ci(rb)[1].toFixed(2)}]</span></td>
                  <td className="n">{d >= 0 ? "+" : ""}{d.toFixed(2)}</td>
                  <td className="small">{a === b ? "same race" : overlap(ci(ra), ci(rb)) ? "No reliable difference (intervals overlap)" : "Different"}</td></tr>;
              })}
              <tr><td>Volume</td><td className="n">{fmtInt(ra.attention)}</td><td className="n">{fmtInt(rb.attention)}</td><td className="n">{fmtInt(ra.attention - rb.attention)}</td><td className="small muted">count, no interval</td></tr>
              </tbody>
            </table>
            <p className="small muted" style={{ margin: "10px 0 0" }}>Non-overlapping 95% intervals are a conservative test. Source: official F1 YouTube channel, 2025;
              sentiment distributions average the four core videos equally.</p>
          </div>
        </section>

        <section className="section grid-2" style={{ alignItems: "start" }}>
          <ChartFrame title="Negativity is not disagreement" sub="Each marker is a race. Coral: top 3 for disagreement in at least half of resamples.">
            <Scatter ariaLabel="disagreement against negativity" xd={[0.2, 0.65]} yd={[0.7, 1]} xlab="negativity" ylab="disagreement" fmt={(v) => v.toFixed(2)}
              points={rows.map((r) => ({ key: r.gp_key, x: r.negativity, y: r.disagreement, label: raceName(r.gp_key), highlight: r.p_top3_disagreement >= 0.5,
                tip: `${raceName(r.gp_key)}\nnegativity ${pct(r.negativity)}\ndisagreement ${r.disagreement.toFixed(2)}` }))} />
          </ChartFrame>
          <div className="prose">
            <h2 style={{ marginTop: 0 }}>What this radar cannot tell you</h2>
            <ul>
              <li><strong>It is not stance.</strong> A split between positive and negative comments is a proxy. It does not show who people think was right in an incident.</li>
              <li><strong>Fan bases drive much of the split</strong>, even without a controversial event.</li>
              <li><strong>Use the groups, not the exact order.</strong> Most neighbouring races sit inside each other's intervals.</li>
              <li><strong>No users are scored.</strong> All measures are computed over comments, never over commenters.</li>
            </ul>
          </div>
        </section>
      </div>
    </>
  );
}
