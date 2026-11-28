import { useState } from "react";
import { ChartFrame, Confusion, DotCI } from "../components/charts";
import { Evidence, SignalCard, Status } from "../components/ui";
import { FAMILY_LABEL, MODEL_LABEL, pct, VIDEO_LABEL, type AllData } from "../data";

const FAMILY_COLOR: Record<string, string> = { lexicon: "var(--neu-ink)", classical_ml: "var(--series)", transformer: "var(--coral)" };
const FAMILY_SHAPE: Record<string, "dot" | "positive" | "negative"> = { lexicon: "dot", classical_ml: "negative", transformer: "positive" };

export default function Models({ data }: { data: AllData }) {
  const [split, setSplit] = useState<"test" | "dev">("test");
  const B = split === "test" ? data.test : data.dev;
  const names = Object.keys(B.models).sort((a, b) => B.models[b].sample.macro_f1 - B.models[a].sample.macro_f1);
  const [sel, setSel] = useState("roberta_twitter");
  const M = B.models[sel] ?? B.models[names[0]];
  const vader = B.models.vader.sample.macro_f1;
  const dist = B.counts.label_distribution;
  const cm = data.test.models.roberta_twitter.sample.confusion.matrix;
  const negToNeu = cm[0][1] / (cm[0].reduce((a, b) => a + b, 0) || 1);

  return (
    <div className="wrap page">
      <div className="kicker">RQ4 · The research lab</div>
      <h1>Model Arena</h1>
      <p className="lede">Six sentiment models scored on the same labelled F1 comments, split by race so no event appears in both development and test.
        Deep learning is not assumed to win.</p>

      <div className="grid-4" style={{ marginTop: 28 }}>
        <SignalCard title="Evaluation sample" value={B.counts.scored_3class} context={`comments · ${B.races} races (${split})`} />
        <SignalCard title="Best macro-F1" value={B.models[names[0]].sample.macro_f1.toFixed(2)} context={MODEL_LABEL[names[0]]} />
        <SignalCard title="VADER baseline" value={vader.toFixed(2)} context="Lexicon, no training" />
        <SignalCard title="Test runs" value="1" context="Logged in the repository" />
      </div>

      <div className="controls">
        <div className="control"><span>Evaluation set</span>
          <div className="seg">
            <button aria-pressed={split === "test"} onClick={() => setSplit("test")}>Test · {data.test.races} races</button>
            <button aria-pressed={split === "dev"} onClick={() => setSplit("dev")}>Development · {data.dev.races} races</button>
          </div></div>
        <Status kind="available">Real evaluation artifacts</Status>
        {split === "dev" && <Status kind="experimental">Optimistic: used for tuning</Status>}
      </div>
      {split === "dev" && <p className="note warn">The development set was used to choose models and settings. DistilBERT looked +0.10 better than VADER here and only
        +0.03 on the untouched test races.</p>}

      <ChartFrame title="Macro-F1 with 95% interval" sub="Higher is better. Intervals come from resampling whole races."
        legend={<div className="legend">{Object.entries(FAMILY_LABEL).map(([f, l]) =>
          <span key={f}><span className="shape" style={{ color: FAMILY_COLOR[f] }}>{f === "transformer" ? "▲" : f === "classical_ml" ? "▼" : "●"}</span>{l}</span>)}</div>}>
        <DotCI ariaLabel="macro-F1 by model" domain={[0.2, 0.8]} fmt={(x) => x.toFixed(1)} labelWidth={240} refLine={{ value: vader, label: "VADER" }}
          rows={names.map((n) => { const m = B.models[n]; return {
            key: n, label: MODEL_LABEL[n] ?? n, value: m.sample.macro_f1, lo: m.sample.macro_f1_ci95[0], hi: m.sample.macro_f1_ci95[1],
            color: FAMILY_COLOR[m.family], shape: FAMILY_SHAPE[m.family],
            tip: `${MODEL_LABEL[n]}\nmacro-F1 ${m.sample.macro_f1.toFixed(3)} [${m.sample.macro_f1_ci95[0].toFixed(2)}–${m.sample.macro_f1_ci95[1].toFixed(2)}]\naccuracy ${pct(m.sample.accuracy, 1)}` }; })} />
      </ChartFrame>

      <section className="section-sm">
        <div className="table-scroll card" style={{ padding: 0 }}><table>
          <thead><tr><th>Model</th><th>Family</th><th>Training</th><th className="n">Macro-F1</th><th className="n">Accuracy</th><th className="n">Weighted-F1</th>
            <th className="n">vs VADER [95% CI]</th><th className="n">Calib. error</th><th className="n">ms / comment</th></tr></thead>
          <tbody>{names.map((n) => { const m = B.models[n], c = B.comparisons[`${n} - vader`]; return (
            <tr key={n}><td><strong>{MODEL_LABEL[n]}</strong></td><td>{FAMILY_LABEL[m.family]}</td>
              <td className="small">{m.training.replace(/rounds \((\d),?\)/, "round $1")}</td>
              <td className="n">{m.sample.macro_f1.toFixed(3)}</td><td className="n">{pct(m.sample.accuracy, 1)}</td><td className="n">{m.sample.weighted_f1.toFixed(3)}</td>
              <td className="n">{c ? `${c.diff >= 0 ? "+" : ""}${c.diff.toFixed(3)} [${c.ci95[0].toFixed(2)}, ${c.ci95[1].toFixed(2)}]` : "—"}</td>
              <td className="n">{m.ece !== undefined ? m.ece.toFixed(2) : "—"}</td><td className="n">{m.ms_per_comment.toFixed(1)}</td></tr>); })}</tbody>
        </table></div>
      </section>

      <section className="section">
        <div className="controls"><div className="control"><label htmlFor="m">Inspect model</label>
          <select id="m" value={sel} onChange={(e) => setSel(e.target.value)}>{names.map((n) => <option key={n} value={n}>{MODEL_LABEL[n]}</option>)}</select></div></div>
        <div className="split">
          <ChartFrame title="Where it goes wrong" sub="Rows = label, columns = prediction.">
            <Confusion labels={M.sample.confusion.labels} matrix={M.sample.confusion.matrix} />
            <table style={{ marginTop: 12 }}>
              <thead><tr><th>Class</th><th className="n">Precision</th><th className="n">Recall</th><th className="n">F1</th></tr></thead>
              <tbody>{Object.entries(M.sample.per_class).map(([c, v]) =>
                <tr key={c}><td>{c}</td><td className="n">{v.precision.toFixed(2)}</td><td className="n">{v.recall.toFixed(2)}</td><td className="n">{v.f1.toFixed(2)}</td></tr>)}</tbody>
            </table>
          </ChartFrame>
          <ChartFrame title="Performance by subgroup" sub="Macro-F1. Faded rows have fewer than 20 comments.">
            <DotCI ariaLabel="macro-F1 by subgroup" domain={[0, 1]} fmt={(x) => x.toFixed(1)} labelWidth={200}
              rows={Object.entries(M.subgroups).map(([g, v]) => ({ key: g, label: g.startsWith("video: ") ? VIDEO_LABEL[g.slice(7)] ?? g : g,
                value: v.macro_f1, color: "var(--series)", muted: v.n < 20, tip: `${g}\nmacro-F1 ${v.macro_f1.toFixed(3)} · n = ${v.n}` }))} />
          </ChartFrame>
        </div>
      </section>

      <section className="section split">
        <div className="panel-dark">
          <div className="kicker">Why F1 language is hard</div>
          <h3>Generic sentiment models meet the paddock</h3>
          <ul style={{ paddingLeft: 18, color: "var(--on-dark-2)" }}>
            <li><strong style={{ color: "#fff" }}>Sarcasm and irony.</strong> Ironic praise such as "great job, another masterpiece" after a bad pit stop reads as positive to a word counter.</li>
            <li><strong style={{ color: "#fff" }}>Nicknames.</strong> Mocking nicknames ("Slowson") carry the negativity without any negative word.</li>
            <li><strong style={{ color: "#fff" }}>Entity attribution.</strong> One comment can praise a driver and attack the team; a single label cannot hold both.</li>
            <li><strong style={{ color: "#fff" }}>Racing terms.</strong> "Box", "undercut", "DNF" or "binned it" are neutral or negative in ways general models never learned.</li>
          </ul>
          <p>On the test races, the best model labels {pct(negToNeu)} of negative comments as neutral. Published shares are corrected for this.</p>
        </div>
        <div>
          <h3>Research evidence</h3>
          <Evidence title="Dataset & evaluation sample" items={[
            ["Data", "Official F1 YouTube channel, 2025 season, 108 videos"],
            ["Split", `${data.dev.races} development races / ${data.test.races} test races, no overlap`],
            ["Sample", `${B.counts.labelled} labelled (${split}); ${B.counts.scored_3class} scored on 3 classes`],
            ["Label mix", Object.entries(dist).map(([k, v]) => `${k} ${v}`).join(" · ")],
            ["Uncertainty", B.bootstrap]]} />
          <Evidence title="Label definitions" items={[
            ["Annotation", "AI-assisted (Claude Opus 5.5), following the published guide; no human validation round"],
            ["Classes", "positive · negative · neutral · mixed · off-topic; mixed and off-topic excluded from scoring"],
            ["Also labelled", "sarcasm, up to 3 driver/team targets with target sentiment, uncertainty flag"]]} />
          <Evidence title="Model provenance" items={[
            ["VADER", "vaderSentiment, MIT"], ["TF-IDF models", "scikit-learn; trained on DynaSent round 2 (CC BY 4.0)"],
            ["RoBERTa-Twitter", "cardiffnlp/twitter-roberta-base-sentiment-latest, CC BY 4.0, inference only"],
            ["DistilBERT-SST2", "distilbert-base-uncased-finetuned-sst-2-english, Apache-2.0, inference only"],
            ["Fine-tuning on F1 data", "none"]]} />
        </div>
      </section>
    </div>
  );
}
