import { useMemo, useState } from "react";
import { ChartFrame, DistBar, DotCI, SentimentLegend, SHAPE, Strip } from "../components/charts";
import { Evidence, SignalCard } from "../components/ui";
import { fmtInt, lastUpdated, pct, raceName, roundOf, VIDEO_LABEL, VIDEO_TYPES, type AllData, type SentimentRow } from "../data";

type Cls = "negative" | "neutral" | "positive";
const COLOR: Record<Cls, string> = { negative: "var(--neg)", neutral: "var(--neu-ink)", positive: "var(--pos)" };
const val = (r: SentimentRow, c: Cls, est: "adj" | "raw") => (est === "adj" ? r[`adj_${c}`] : r[`raw_${c}`]);
const cap = (s: string) => s[0].toUpperCase() + s.slice(1);

export default function Observatory({ data }: { data: AllData }) {
  const [vt, setVt] = useState("race_reactions");
  const [cls, setCls] = useState<Cls>("negative");
  const [est, setEst] = useState<"adj" | "raw">("adj");
  const rounds = roundOf(data);
  const rows = useMemo(() => data.sentiment.rows.filter((r) => r.video_type === vt)
    .sort((a, b) => (rounds[a.gp_key] ?? 99) - (rounds[b.gp_key] ?? 99)), [data, vt, rounds]);
  const nSel = rows.reduce((s, r) => s + r.n, 0), vMax = Math.max(...rows.map((r) => r.n));

  return (
    <div className="wrap page">
      <div className="kicker">RQ1 · Sentiment dynamics</div>
      <h1>Sentiment Observatory</h1>
      <p className="lede">How positive, neutral and negative are the comments under each official race-weekend video? Shares are <strong>corrected</strong> for
        the model's measured errors, and every estimate carries a 95% interval.</p>

      <div className="grid-4" style={{ marginTop: 28 }}>
        <SignalCard title="Source" value="F1 · YouTube" context="Official channel, public comments" />
        <SignalCard title="Sample in view" value={fmtInt(nSel)} context={`${rows.length} videos · ${VIDEO_LABEL[vt]}`} />
        <SignalCard title="Model" value="RoBERTa" context="Twitter-pretrained, inference only" source="cardiffnlp · CC BY 4.0" />
        <SignalCard title="Last update" value={<span style={{ fontSize: "1.25rem" }}>{lastUpdated(data)}</span>} context="Static results, no live data" />
      </div>

      <div className="controls" role="group" aria-label="Filters">
        <div className="control"><label htmlFor="vt">Video type</label>
          <select id="vt" value={vt} onChange={(e) => setVt(e.target.value)}>
            {Object.keys(VIDEO_LABEL).map((v) => <option key={v} value={v}>{VIDEO_LABEL[v]}</option>)}
          </select></div>
        <div className="control"><span>Sentiment</span>
          <div className="seg">{(["negative", "neutral", "positive"] as Cls[]).map((c) =>
            <button key={c} aria-pressed={cls === c} onClick={() => setCls(c)}>{SHAPE[c]} {cap(c)}</button>)}</div></div>
        <div className="control"><span>Estimate</span>
          <div className="seg">
            <button aria-pressed={est === "adj"} onClick={() => setEst("adj")}>Corrected</button>
            <button aria-pressed={est === "raw"} onClick={() => setEst("raw")}>Raw model count</button>
          </div></div>
      </div>
      {est === "raw" && <p className="note warn">Raw counts are shown for comparison only. The model labels about half of truly negative comments as neutral,
        so raw negative shares are biased downward and carry no valid interval.</p>}

      <ChartFrame title={`${SHAPE[cls]} ${cap(cls)} share by race · ${VIDEO_LABEL[vt]}`}
        sub={est === "adj" ? "Marker = corrected share; line = 95% interval. Calendar order." : "Raw share of comments the model labelled this way."}>
        <DotCI ariaLabel={`${cls} share by race`} domain={[0, 1]} fmt={(x) => pct(x)} labelWidth={170}
          rows={rows.map((r) => {
            const v = val(r, cls, est);
            const lo = est === "adj" ? r[`adj_${cls}_lo`] : undefined, hi = est === "adj" ? r[`adj_${cls}_hi`] : undefined;
            return { key: r.gp_key, label: `R${rounds[r.gp_key]} ${raceName(r.gp_key)}`, value: v, lo, hi, color: COLOR[cls], shape: cls,
              tip: `${raceName(r.gp_key)} · ${VIDEO_LABEL[vt]}\n${cls}: ${pct(v, 1)}${lo !== undefined ? ` (95% CI ${pct(lo)}–${pct(hi!)})` : " (raw)"}\nraw count ${pct(r[`raw_${cls}`], 1)} · ${fmtInt(r.n)} comments` };
          })} />
        <details className="table-view"><summary>Show as table</summary>
          <div className="table-scroll"><table>
            <thead><tr><th>Race</th><th className="n">Comments</th><th className="n">▼ Neg.</th><th className="n">● Neu.</th><th className="n">▲ Pos.</th><th className="n">Neg. 95% CI</th></tr></thead>
            <tbody>{rows.map((r) => <tr key={r.gp_key}><td>{raceName(r.gp_key)}</td><td className="n">{fmtInt(r.n)}</td>
              <td className="n">{pct(val(r, "negative", est), 1)}</td><td className="n">{pct(val(r, "neutral", est), 1)}</td><td className="n">{pct(val(r, "positive", est), 1)}</td>
              <td className="n">{pct(r.adj_negative_lo)}–{pct(r.adj_negative_hi)}</td></tr>)}</tbody>
          </table></div></details>
      </ChartFrame>

      <section className="section-sm grid-2" style={{ alignItems: "start" }}>
        <ChartFrame title={`Full mix · ${VIDEO_LABEL[vt]}`} sub="Corrected shares. Prevalence, not volume." legend={<SentimentLegend />}>
          <div style={{ display: "grid", gap: 7 }}>{rows.map((r) => (
            <div key={r.gp_key} style={{ display: "grid", gridTemplateColumns: "minmax(0,120px) minmax(0,1fr)", gap: 10, alignItems: "center" }}
              title={`${raceName(r.gp_key)}: ▼ ${pct(r.adj_negative)} ● ${pct(r.adj_neutral)} ▲ ${pct(r.adj_positive)}`}>
              <span className="small">{raceName(r.gp_key)}</span>
              <DistBar neg={r.adj_negative} neu={r.adj_neutral} pos={r.adj_positive} height={12} />
            </div>))}</div>
        </ChartFrame>
        <ChartFrame title={`Discussion volume · ${VIDEO_LABEL[vt]}`} sub="Comments per video. Volume, not sentiment: kept on its own axis.">
          <div style={{ display: "grid", gap: 7 }}>{rows.map((r) => (
            <div key={r.gp_key} style={{ display: "grid", gridTemplateColumns: "minmax(0,120px) minmax(0,1fr) 54px", gap: 10, alignItems: "center" }}>
              <span className="small">{raceName(r.gp_key)}</span>
              <div className="meter" style={{ height: 12, marginTop: 0 }}><b style={{ width: `${(r.n / vMax) * 100}%`, background: "var(--series)" }} /></div>
              <span className="num small" style={{ textAlign: "right" }}>{fmtInt(r.n)}</span>
            </div>))}</div>
        </ChartFrame>
      </section>

      <section className="section-sm">
        <ChartFrame title={`${SHAPE[cls]} ${cap(cls)} share across the four core formats`} sub="One marker per race; bar = median race. Compares formats, not races.">
          <Strip ariaLabel="share by video type" domain={[0, 1]} fmt={(x) => pct(x)} color={COLOR[cls]} shape={cls}
            groups={VIDEO_TYPES.map((v) => ({ label: VIDEO_LABEL[v], points: data.sentiment.rows.filter((r) => r.video_type === v)
              .map((r) => ({ value: val(r, cls, est), tip: `${raceName(r.gp_key)} · ${VIDEO_LABEL[v]}\n${cls}: ${pct(val(r, cls, est), 1)}` })) }))} />
        </ChartFrame>
      </section>

      <section className="section-sm split">
        <div className="prose">
          <h2 style={{ marginTop: 0 }}>Reading this page</h2>
          <ul>
            <li><strong>Compare formats before races.</strong> Format differences are larger than most race differences. Overlapping intervals mean no reliable difference.</li>
            <li><strong>Volume is not sentiment.</strong> The season opener drew about twice the comments of a typical race; compare shares, not counts.</li>
            <li><strong>Survivorship.</strong> Deleted or moderated comments are missing and likely harsher than average, so negativity is probably understated.</li>
            <li><strong>Not representative.</strong> These are commenters on the official channel, not all fans.</li>
          </ul>
        </div>
        <Evidence items={[["Correction", data.sentiment.correction], ["Model", "cardiffnlp/twitter-roberta-base-sentiment-latest, pretrained inference"],
          ["Labels", (data.sentiment.gold_labels_by ?? []).join(", ").replace("ai:claude-opus-5-5", "AI-assisted (Claude)")],
          ["Suppression", "Groups under 10 comments are not shown"], ["Generated", lastUpdated(data)]]} />
      </section>
    </div>
  );
}
