import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { DistBar, SentimentLegend } from "../components/charts";
import { buildMonitor, SignalMonitor, type SentMetric } from "../components/SignalMonitor";
import { Evidence, PageHead, Status } from "../components/ui";
import { fmtInt, lastUpdated, pct, raceName, VIDEO_LABEL, type AllData } from "../data";

const STAGES = ["qualifying_highlights", "qualifying_reactions", "race_highlights", "race_reactions", "sprint_highlights", "sprint_reactions"];

export default function Monitor({ data }: { data: AllData }) {
  const [params, setParams] = useSearchParams();
  const topics = data.topics.topics.filter((t) => t.show);
  const [topicId, setTopicId] = useState(topics.find((t) => t.kind === "theme")?.id ?? topics[0].id);
  const [metric, setMetric] = useState<SentMetric>("net");
  const all = useMemo(() => buildMonitor(data, topicId), [data, topicId]);
  const [from, setFrom] = useState(1), [to, setTo] = useState(all.length);
  const races = all.filter((r) => r.round >= from && r.round <= to);
  const sel = params.get("race") && all.some((r) => r.gp === params.get("race")) ? params.get("race")! : all[all.length - 1].gp;
  const [cmp, setCmp] = useState<string>("");
  const setSel = (gp: string) => setParams({ race: gp }, { replace: true });
  const R = all.find((r) => r.gp === sel)!;
  const C = all.find((r) => r.gp === cmp);
  const topicName = topics.find((t) => t.id === topicId)?.name ?? "";
  const stages = STAGES.map((vt) => data.sentiment.rows.find((r) => r.gp_key === sel && r.video_type === vt)).filter(Boolean);

  return (
    <>
      <PageHead kicker="Signature feature" title="The Signal Monitor" tagline="Four signals, one race-weekend axis.">
        <p className="lede">Discussion volume, corrected sentiment, disagreement and topic activity for every 2025 Grand Prix, on one coordinated timeline.
          Select a round to highlight it across every lane and open its weekend stages.</p>
      </PageHead>

      <section className="dark" style={{ paddingTop: 8, paddingBottom: 56 }}>
        <div className="wrap">
          <div className="controls" role="group" aria-label="Monitor controls">
            <div className="control"><span>Season</span>
              <select disabled value="2025" aria-describedby="season-note"><option>2025</option></select></div>
            <div className="control"><label htmlFor="gp">Grand Prix</label>
              <select id="gp" value={sel} onChange={(e) => setSel(e.target.value)}>
                {all.map((r) => <option key={r.gp} value={r.gp}>R{r.round} {raceName(r.gp)}</option>)}
              </select></div>
            <div className="control"><label htmlFor="cmp">Compare with</label>
              <select id="cmp" value={cmp} onChange={(e) => setCmp(e.target.value)}>
                <option value="">None</option>
                {all.filter((r) => r.gp !== sel).map((r) => <option key={r.gp} value={r.gp}>R{r.round} {raceName(r.gp)}</option>)}
              </select></div>
            <div className="control"><span>Sentiment lane</span>
              <div className="seg">
                <button aria-pressed={metric === "net"} onClick={() => setMetric("net")}>Net</button>
                <button aria-pressed={metric === "negative"} onClick={() => setMetric("negative")}>Negative share</button>
              </div></div>
            <div className="control"><label htmlFor="topic">Topic lane</label>
              <select id="topic" value={topicId} onChange={(e) => setTopicId(+e.target.value)}>
                {topics.map((t) => <option key={t.id} value={t.id}>{t.name}{t.kind === "reaction" ? " (reaction)" : ""}</option>)}
              </select></div>
            <div className="control"><span>Rounds</span>
              <div style={{ display: "flex", gap: 6 }}>
                <select aria-label="from round" value={from} onChange={(e) => setFrom(Math.min(+e.target.value, to - 2))} style={{ minWidth: 76 }}>
                  {all.map((r) => <option key={r.round} value={r.round}>R{r.round}</option>)}</select>
                <select aria-label="to round" value={to} onChange={(e) => setTo(Math.max(+e.target.value, from + 2))} style={{ minWidth: 76 }}>
                  {all.map((r) => <option key={r.round} value={r.round}>R{r.round}</option>)}</select>
              </div></div>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }} id="season-note">
            <Status kind="available">Volume · sentiment · disagreement · topics</Status>
            <Status kind="unavailable">Driver / team filter: target-aware sentiment pending</Status>
            <Status kind="unavailable">Other seasons &amp; source categories</Status>
            <Status kind="unavailable">Incident annotations: none verified yet</Status>
          </div>

          <div className="monitor">
            <div className="monitor-head">
              <span className="title"><span style={{ color: "var(--coral)" }}>◆</span> R{from}–R{to} · 2025</span>
              <span className="legend" style={{ margin: 0 }}>
                <span><span className="sw" style={{ background: "var(--coral)" }} />Selected: {raceName(sel)}</span>
                {C && <span><span className="sw" style={{ background: "var(--cyan)" }} />Compared: {raceName(C.gp)}</span>}
              </span>
            </div>
            <SignalMonitor races={races} selected={sel} compare={cmp || undefined} onSelect={setSel} metric={metric} topicName={topicName} />
            <p className="small muted" style={{ marginTop: 10 }}>◆ markers on the axis are race weekends (Jolpica-F1 calendar). Shaded bands are 95% intervals.
              Disagreement axis runs 0.5–1.0.</p>
          </div>

          <Evidence items={[
            ["Volume", "Comments on the race's four core videos (raw count; mostly audience size)."],
            ["Sentiment", "RoBERTa-Twitter labels, corrected for its measured error rates (adjusted classify-and-count). 95% bootstrap band."],
            ["Disagreement", "Variance of a −1/0/+1 sentiment score: 0 = everyone agrees, 1 = even positive/negative split."],
            ["Topic", "Share of comments assigned to the chosen NMF topic, averaged over the four video formats."],
            ["Source", `Official Formula 1 YouTube channel, 2025 season. Results generated ${lastUpdated(data)}.`],
          ]} />
        </div>
      </section>

      {/* selected race: weekend stages */}
      <section className="wrap section-sm" style={{ paddingBottom: 72 }}>
        <div className="kicker">Weekend stages</div>
        <h2>R{R.round} {raceName(sel)}{C ? <span className="muted" style={{ fontWeight: 400 }}> vs R{C.round} {raceName(C.gp)}</span> : null}</h2>
        <div className="grid-4" style={{ marginTop: 20 }}>
          {[["Volume", fmtInt(R.volume), C && fmtInt(C.volume), "comments"],
            ["Net sentiment", `${(R.net * 100).toFixed(0)} pts`, C && `${(C.net * 100).toFixed(0)} pts`, `95% CI ${(R.netCI[0] * 100).toFixed(0)} to ${(R.netCI[1] * 100).toFixed(0)}`],
            ["Negative share", pct(R.neg), C && pct(C.neg), `95% CI ${pct(R.negCI[0])}–${pct(R.negCI[1])}`],
            ["Disagreement", R.dis.toFixed(2), C && C.dis.toFixed(2), `95% CI ${R.disCI[0].toFixed(2)}–${R.disCI[1].toFixed(2)}`]].map(([k, v, c, note]) => (
            <div className="signal-card" key={k as string}>
              <span className="t">{k}</span><span className="v">{v}</span>
              {c && <span className="c" style={{ color: "#1b6a75" }}>vs {c}</span>}
              <span className="src">{note}</span>
            </div>
          ))}
        </div>

        <div className="card" style={{ marginTop: 24 }}>
          <p className="chart-title">Sentiment at each stage of the weekend</p>
          <p className="chart-sub">Corrected shares per video. Stages follow the weekend from qualifying to the race.</p>
          <SentimentLegend />
          <div style={{ display: "grid", gap: 16, marginTop: 8 }}>
            {stages.map((r) => r && (
              <div key={r.video_type} style={{ display: "grid", gridTemplateColumns: "minmax(0, 220px) minmax(0, 1fr)", gap: 16, alignItems: "center" }}>
                <div><div className="small" style={{ fontWeight: 600 }}>{VIDEO_LABEL[r.video_type]}</div>
                  <div className="num small muted">{fmtInt(r.n)} comments · neg. CI {pct(r.adj_negative_lo)}–{pct(r.adj_negative_hi)}</div></div>
                <DistBar neg={r.adj_negative} neu={r.adj_neutral} pos={r.adj_positive} labels />
              </div>
            ))}
          </div>
        </div>
        <details className="table-view">
          <summary>Show all races as a table</summary>
          <div className="table-scroll"><table>
            <thead><tr><th>Round</th><th>Race</th><th className="n">Volume</th><th className="n">Net</th><th className="n">Negative</th><th className="n">Disagreement</th><th className="n">{topicName}</th></tr></thead>
            <tbody>{all.map((r) => <tr key={r.gp}><td>R{r.round}</td><td>{raceName(r.gp)}</td><td className="n">{fmtInt(r.volume)}</td>
              <td className="n">{(r.net * 100).toFixed(0)}</td><td className="n">{pct(r.neg)}</td><td className="n">{r.dis.toFixed(2)}</td><td className="n">{pct(r.topic, 1)}</td></tr>)}</tbody>
          </table></div>
        </details>
      </section>
    </>
  );
}
