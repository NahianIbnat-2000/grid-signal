import { useMemo, useState } from "react";
import { ChartFrame, Heatmap, Line } from "../components/charts";
import { Evidence, Status } from "../components/ui";
import { mean, pct, raceName, racesInOrder, TOPIC_DESC, VIDEO_LABEL, VIDEO_TYPES, type AllData } from "../data";

function corr(a: number[], b: number[]) {
  const ma = mean(a), mb = mean(b);
  let num = 0, da = 0, db = 0;
  a.forEach((x, i) => { num += (x - ma) * (b[i] - mb); da += (x - ma) ** 2; db += (b[i] - mb) ** 2; });
  return da && db ? num / Math.sqrt(da * db) : 0;
}

export default function Narratives({ data }: { data: AllData }) {
  const T = data.topics;
  const shown = T.topics.filter((t) => t.show);
  const hidden = T.topics.filter((t) => !t.show);
  const races = racesInOrder(data);
  const [sel, setSel] = useState(shown.find((t) => t.kind === "theme")!.id);
  const [kind, setKind] = useState<"all" | "theme" | "reaction">("all");
  const prev = useMemo(() => {
    const m = new Map<string, number>();
    for (const p of T.prevalence) m.set(`${p.gp_key}|${p.video_type}|${p.topic}`, p.share);
    return (gp: string, vt: string, id: number) => m.get(`${gp}|${vt}|${id}`) ?? 0;
  }, [T]);
  const series = (id: number) => races.map((r) => mean(VIDEO_TYPES.map((vt) => prev(r.gp_key, vt, id))));
  const byType = (id: number, vt: string) => mean(races.map((r) => prev(r.gp_key, vt, id)));
  const topic = T.topics.find((t) => t.id === sel)!;
  const s = series(sel);
  const peak = s.indexOf(Math.max(...s));
  const related = shown.filter((t) => t.id !== sel).map((t) => ({ t, r: corr(s, series(t.id)) })).sort((x, y) => y.r - x.r).slice(0, 3);
  const list = shown.filter((t) => kind === "all" || t.kind === kind);
  const heatRows = shown.map((t) => ({ key: String(t.id), label: t.name }));
  const heatMax = Math.max(...shown.flatMap((t) => VIDEO_TYPES.map((vt) => byType(t.id, vt))));

  return (
    <div className="wrap page">
      <div className="kicker">RQ2 · Narrative evolution</div>
      <h1>Narrative Explorer</h1>
      <p className="lede">An archive of what commenters talk about. Topics come from word patterns (TF-IDF + NMF) after removing driver and team names, so they
        describe <em>what</em> is discussed rather than <em>who</em>.</p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "18px 0 6px" }}>
        <Status kind="available">{shown.length} stable topics · 24 races</Status>
        <Status kind="experimental">Labels: AI-proposed, owner-approved, not validated</Status>
        <Status kind="unavailable">Driver &amp; team associations: pending</Status>
      </div>

      <div className="split section-sm" style={{ gridTemplateColumns: "minmax(0,4fr) minmax(0,8fr)", marginTop: 28 }}>
        {/* archive list */}
        <div>
          <div className="seg" style={{ marginBottom: 14 }} role="group" aria-label="Topic kind">
            {(["all", "theme", "reaction"] as const).map((k) => <button key={k} aria-pressed={kind === k} onClick={() => setKind(k)}>
              {k === "all" ? "All" : k === "theme" ? "Themes" : "Reactions"}</button>)}
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {list.map((t) => (
              <button key={t.id} className="topic" aria-pressed={t.id === sel} onClick={() => setSel(t.id)}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <h4>{t.name}</h4><span className={`tag ${t.kind}`}>{t.kind}</span>
                </div>
                <div className="num small muted" style={{ marginTop: 4 }}>{pct(t.overall_share, 1)} of comments · stability {t.stability.toFixed(2)}</div>
              </button>
            ))}
          </div>
          <p className="small muted" style={{ marginTop: 14 }}>{pct(T.unassigned_share)} of comments fit no topic (mostly short cheering once names are removed).</p>
        </div>

        {/* topic dossier */}
        <div>
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
              <div className="label">Topic dossier · #{topic.id}</div><span className={`tag ${topic.kind}`}>{topic.kind}</span>
            </div>
            <h2 style={{ margin: "8px 0 6px" }}>{topic.name}</h2>
            <p className="muted" style={{ marginBottom: 6 }}>{TOPIC_DESC[topic.name] ?? "—"}</p>
            <p className="small muted">Description written by AI from the top words; approved by the project owner. A statistical grouping of words, not a verified narrative.</p>
            <div className="grid-3" style={{ gap: 12, margin: "16px 0" }}>
              <div><div className="label">Prevalence</div><div className="num" style={{ fontSize: "1.5rem" }}>{pct(topic.overall_share, 1)}</div></div>
              <div><div className="label">Coverage</div><div className="num" style={{ fontSize: "1.5rem" }}>{s.filter((v) => v > 0).length}/24</div><div className="small muted">races present</div></div>
              <div><div className="label">Stability</div><div className="num" style={{ fontSize: "1.5rem" }}>{topic.stability.toFixed(2)}</div>
                <div className="meter"><b style={{ width: `${topic.stability * 100}%` }} /></div></div>
            </div>
            <div className="label">Top words (why it has this label)</div>
            <div className="words">{topic.top_words.map((w) => <span key={w}>{w}</span>)}</div>
            {topic.note && <p className="small muted" style={{ margin: "12px 0 0" }}>Note: {topic.note}</p>}
          </div>

          <div style={{ marginTop: 20 }}>
            <ChartFrame title="Topic timeline" sub={`Share of comments per race (four core videos averaged). Peak: R${races[peak].round} ${raceName(races[peak].gp_key)}. Dashed = season mean.`}>
              <Line ariaLabel={`${topic.name} share by race`} points={s} xLabels={races.map((r) => `R${r.round}`)} yMax={Math.max(...s) * 1.2 || 0.01}
                fmt={(v) => pct(v, 1)} color="var(--series)" highlight={peak} band={mean(s)} />
            </ChartFrame>
          </div>
          <div className="card" style={{ marginTop: 20 }}>
            <p className="chart-title">Topics that rise and fall with this one</p>
            <p className="chart-sub">Correlation of per-race shares across the 24 races. Co-movement, not meaning.</p>
            <table><tbody>{related.map(({ t, r }) => <tr key={t.id}><td><button className="topic" style={{ padding: "6px 10px", border: 0 }} onClick={() => setSel(t.id)}>{t.name}</button></td>
              <td><span className={`tag ${t.kind}`}>{t.kind}</span></td><td className="n">r = {r.toFixed(2)}</td></tr>)}</tbody></table>
          </div>
        </div>
      </div>

      <section className="section">
        <ChartFrame title="Topic share by video format" sub="Average over 24 races of the share of comments assigned to each topic.">
          <Heatmap ariaLabel="topic share by video format" rows={heatRows}
            cols={VIDEO_TYPES.map((v) => ({ key: v, label: VIDEO_LABEL[v].replace("Qualifying", "Quali").replace("driver ", "") }))}
            value={(r, c) => byType(+r, c)} fmt={(x) => pct(x, 1)} max={heatMax}
            tip={(r, c) => `${T.topics[+r].name}\n${VIDEO_LABEL[c]}: ${pct(byType(+r, c), 1)}`} />
        </ChartFrame>
      </section>

      <section className="section-sm split">
        <div className="prose">
          <h2 style={{ marginTop: 0 }}>Limits</h2>
          <ul>
            <li><strong>Missing themes.</strong> Team orders, tyre strategy and crashes do not form separate topics in short comments; absence here does not mean they were not discussed.</li>
            <li><strong>Mixed topics.</strong> "Car pace &amp; safety car" joins two ideas that share words.</li>
            {hidden.map((t) => <li key={t.id}><strong>Hidden:</strong> "{t.name}" ({t.note}).</li>)}
          </ul>
        </div>
        <Evidence items={[["Method", T.method], ["Stability", T.stability.method], ["Labels", T.labels_by], ["Unassigned", pct(T.unassigned_share)]]} />
      </section>
    </div>
  );
}
