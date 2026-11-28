import { useState } from "react";
import { Link } from "react-router-dom";
import { DotCI, HeroWave, Scatter } from "../components/charts";
import { buildMonitor, SignalMonitor } from "../components/SignalMonitor";
import { SignalCard, Status } from "../components/ui";
import { fmtInt, lastUpdated, MODEL_LABEL, mean, pct, raceName, totalComments, VIDEO_LABEL, VIDEO_TYPES, type AllData } from "../data";

export default function Home({ data }: { data: AllData }) {
  const themes = data.topics.topics.filter((t) => t.show && t.kind === "theme");
  const reactions = data.topics.topics.filter((t) => t.show && t.kind === "reaction");
  const races = buildMonitor(data, themes[0]?.id ?? 0);
  const [sel, setSel] = useState(races[races.length - 1].gp);
  const best = data.test.models.roberta_twitter, vader = data.test.models.vader;
  const cmp = data.test.comparisons["roberta_twitter - vader"];
  const negBy = (vt: string) => mean(data.sentiment.rows.filter((r) => r.video_type === vt).map((r) => r.adj_negative));
  const hl = mean([negBy("qualifying_highlights"), negBy("race_highlights")]);
  const rx = mean([negBy("qualifying_reactions"), negBy("race_reactions")]);
  const dis = data.controversy.rows.map((r) => r.disagreement);
  const top = [...data.controversy.rows].sort((a, b) => b.p_top3_disagreement - a.p_top3_disagreement)[0];
  const vols = races.map((r) => r.volume);
  const models = Object.keys(data.test.models).sort((a, b) => data.test.models[b].sample.macro_f1 - data.test.models[a].sample.macro_f1);

  return (
    <>
      {/* ---------------- HERO ---------------- */}
      <section className="dark grid-bg hero">
        <div className="wrap" style={{ position: "relative" }}>
          <div className="kicker">The Signal Room · Formula 1 narrative intelligence</div>
          <h1>GRID <span className="sig">SIGNAL</span></h1>
          <div className="headline">Beyond the Race. Decode the Reaction.</div>
          <p className="desc">An independent Formula 1 narrative intelligence observatory exploring how fans, media, and online communities interpret the sport
            through natural language processing and deep learning.</p>
          <div className="actions">
            <Link className="btn btn-primary" to="/monitor">Explore the Signals →</Link>
            <Link className="btn btn-ghost" to="/methods">Read the Research</Link>
          </div>
        </div>
        <div className="wrap"><HeroWave values={races.map((r) => r.net)} /></div>

        {/* signal monitor preview */}
        <div className="wrap" style={{ paddingBottom: 56 }}>
          <div className="monitor">
            <div className="monitor-head">
              <span className="title"><span style={{ color: "var(--coral)" }}>◆</span> Signal Monitor · 2025 season</span>
              <span style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Status kind="available">{data.controversy.rows.length} races</Status>
                <Status kind="updated">Updated {lastUpdated(data)}</Status>
              </span>
            </div>
            <SignalMonitor compact races={races} selected={sel} onSelect={setSel} metric="net" topicName={themes[0]?.name ?? ""} />
            <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap", marginTop: 10 }}>
              <span className="small muted">Bars: comments per race weekend. Line: corrected net sentiment with 95% band. Click a round to select it.</span>
              <Link to={`/monitor?race=${encodeURIComponent(sel)}`} className="small">Open R{races.find((r) => r.gp === sel)?.round} {raceName(sel)} in the full monitor →</Link>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- 01 THE CONVERSATION ---------------- */}
      <section className="wrap section">
        <div className="split">
          <div>
            <div className="kicker">01 · The Conversation</div>
            <h2>Every race weekend starts a conversation</h2>
            <p className="lede">GRID SIGNAL follows the same four official videos for every Grand Prix, from qualifying highlights to the drivers' post-race
              reactions, and reads every public comment under them.</p>
            <p className="small muted">This is sampled discourse from one official channel. It is not the view of all Formula 1 fans.</p>
          </div>
          <div className="grid-2" style={{ gap: 16 }}>
            <SignalCard title="Comments analysed" value={fmtInt(totalComments(data))} period="2025 season" source="YouTube Data API" />
            <SignalCard title="Videos" value={data.sentiment.rows.length} context="Fixed per-weekend formats, no virality filter" />
            <SignalCard title="Busiest weekend" value={fmtInt(Math.max(...vols))}
              context={`comments · ${raceName(races[vols.indexOf(Math.max(...vols))].gp)}`} />
            <SignalCard title="Quietest weekend" value={fmtInt(Math.min(...vols))}
              context={`comments · ${raceName(races[vols.indexOf(Math.min(...vols))].gp)}`} />
          </div>
        </div>
      </section>

      {/* ---------------- 02 THE NARRATIVE ---------------- */}
      <section className="wrap section">
        <div className="kicker">02 · The Narrative</div>
        <div className="split" style={{ gridTemplateColumns: "minmax(0,7fr) minmax(0,5fr)" }}>
          <div className="card">
            <p className="chart-title">What people discuss, after removing driver names</p>
            <p className="chart-sub">Share of all comments per theme topic. {pct(data.topics.unassigned_share)} of comments fit no topic.</p>
            <div style={{ display: "grid", gap: 10, marginTop: 14 }}>
              {[...themes].sort((a, b) => b.overall_share - a.overall_share).map((t) => (
                <div key={t.id} style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 140px 48px", gap: 12, alignItems: "center" }}>
                  <span className="small">{t.name}</span>
                  <div className="meter" style={{ height: 8, marginTop: 0 }}><b style={{ width: `${(t.overall_share / 0.05) * 100}%` }} /></div>
                  <span className="num small" style={{ textAlign: "right" }}>{pct(t.overall_share, 1)}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h2>Most comments react. Few discuss.</h2>
            <p>Two-thirds of comments are short reactions with no theme at all. Among the stable topics, {themes.length} are real themes, from penalties to the
              title race, and {reactions.length} are ways of reacting: cheering, praise, memes.</p>
            <Link to="/narratives">Open the Narrative Explorer →</Link>
          </div>
        </div>
      </section>

      {/* ---------------- 03 THE DIVIDE ---------------- */}
      <section className="wrap section">
        <div className="panel-dark grid-bg">
          <div className="split">
            <div>
              <div className="kicker">03 · The Divide</div>
              <h2>Not every negative reaction is a divided opinion.</h2>
              <p>GRID SIGNAL measures negativity and disagreement separately. Comment sections split strongly almost everywhere (disagreement
                {" "}{Math.min(...dis).toFixed(2)}–{Math.max(...dis).toFixed(2)} on a 0–1 scale), so only a few rankings hold up:
                {" "}{raceName(top.gp_key)} lands in the top three in {pct(top.p_top3_disagreement)} of resamples.</p>
              <Link to="/controversy">Open the Controversy Radar →</Link>
            </div>
            <div className="chart" style={{ background: "var(--white)" }}>
              <p className="chart-title" style={{ color: "var(--text)" }}>Negativity vs disagreement, by race</p>
              <Scatter ariaLabel="Disagreement against negativity for each race" xd={[0.2, 0.65]} yd={[0.7, 1]} xlab="negativity" ylab="disagreement"
                fmt={(v) => v.toFixed(2)} points={data.controversy.rows.map((r) => ({
                  key: r.gp_key, x: r.negativity, y: r.disagreement, label: raceName(r.gp_key), highlight: r.p_top3_disagreement >= 0.5,
                  tip: `${raceName(r.gp_key)}\nnegativity ${pct(r.negativity)}\ndisagreement ${r.disagreement.toFixed(2)}` }))} />
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- 04 THE INTELLIGENCE ---------------- */}
      <section className="wrap section">
        <div className="split">
          <div>
            <div className="kicker">04 · The Intelligence</div>
            <h2>Can a model read F1 sarcasm?</h2>
            <p className="lede">Six sentiment models were scored on the same labelled comments from {data.test.races} held-out races.</p>
            <div className="insight" style={{ marginTop: 20 }}>
              <div className="n">FINDING</div>
              <p>RoBERTa-Twitter reaches macro-F1 {best.sample.macro_f1.toFixed(2)}, {cmp.diff >= 0 ? "+" : ""}{cmp.diff.toFixed(2)} over VADER
                ({vader.sample.macro_f1.toFixed(2)}; gain 95% CI {cmp.ci95[0].toFixed(2)} to {cmp.ci95[1].toFixed(2)}). Classical models trained on review text
                do no better than the word list. Domain matters more than architecture, and even the best model misses many negative comments.</p>
            </div>
            <Link to="/models">Enter the Model Arena →</Link>
          </div>
          <div className="card">
            <p className="chart-title">Macro-F1 on held-out races</p>
            <p className="chart-sub">95% intervals from resampling races. Labels: AI-assisted annotation (Claude).</p>
            <DotCI ariaLabel="macro-F1 by model" domain={[0.3, 0.7]} fmt={(x) => x.toFixed(1)} labelWidth={210}
              refLine={{ value: vader.sample.macro_f1, label: "VADER" }}
              rows={models.map((n) => {
                const m = data.test.models[n];
                return { key: n, label: MODEL_LABEL[n] ?? n, value: m.sample.macro_f1, lo: m.sample.macro_f1_ci95[0], hi: m.sample.macro_f1_ci95[1],
                  color: m.family === "transformer" ? "var(--coral)" : m.family === "classical_ml" ? "var(--series)" : "var(--neu-ink)",
                  tip: `${MODEL_LABEL[n]}\nmacro-F1 ${m.sample.macro_f1.toFixed(3)}` };
              })} />
          </div>
        </div>
      </section>

      {/* ---------------- format finding + method ---------------- */}
      <section className="wrap section">
        <div className="card" style={{ display: "grid", gap: 24, gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", alignItems: "center" }}>
          <div>
            <div className="label" style={{ marginBottom: 8 }}>Format effect</div>
            <h3 style={{ marginBottom: 6 }}>Reaction videos draw harsher comments</h3>
            <p className="small muted" style={{ margin: 0 }}>Average corrected negative share across 24 races.</p>
          </div>
          {VIDEO_TYPES.map((vt) => <div key={vt}>
            <div className="label">{VIDEO_LABEL[vt]}</div>
            <div className="num" style={{ fontSize: "1.6rem", marginTop: 4 }}><span style={{ color: "var(--neg)", fontSize: "1rem" }}>▼ </span>{pct(negBy(vt))}</div>
          </div>)}
        </div>
        <p className="small muted" style={{ marginTop: 10 }}>Driver-reaction videos average {pct(rx)} negative, highlights videos {pct(hl)}.
          {" "}<Link to="/observatory">See by race in the Sentiment Observatory →</Link></p>
      </section>
    </>
  );
}
