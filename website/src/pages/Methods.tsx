import { REPO } from "../App";
import { Status } from "../components/ui";
import { fmtInt, totalComments, type AllData } from "../data";

const SECTIONS = [
  ["q", "Research questions"], ["source", "Source & access terms"], ["sample", "Sampling"], ["pre", "Preprocessing"],
  ["missing", "Missing data"], ["labels", "Labels"], ["models", "Model architectures"], ["eval", "Evaluation"],
  ["correct", "Corrected shares"], ["contro", "Controversy measures"], ["topics", "Topics"], ["events", "Event studies"],
  ["privacy", "Privacy"], ["limits", "Limitations"], ["status", "Completed & pending"], ["refs", "References"],
] as const;

function H({ id }: { id: (typeof SECTIONS)[number][0] }) {
  const i = SECTIONS.findIndex((s) => s[0] === id);
  return <h2 id={id}><span className="sn">{String(i + 1).padStart(2, "0")}</span>{SECTIONS[i][1]}</h2>;
}

export default function Methods({ data }: { data: AllData }) {
  const lab = data.test.counts.labelled + data.dev.counts.labelled;
  return (
    <div className="wrap page">
      <div className="kicker">Research · Data &amp; methodology</div>
      <h1>How GRID SIGNAL measures the conversation</h1>
      <p className="lede">Everything needed to judge, reproduce or challenge the numbers on this site. Code, sampling rules and result files are in
        the <a href={REPO}>public repository</a>; comment text is not, by design.</p>

      <div className="doc" style={{ marginTop: 36 }}>
        <nav className="toc" aria-label="Contents"><div className="label" style={{ marginBottom: 12 }}>Contents</div>
          <ol>{SECTIONS.map(([id, t]) => <li key={id}><a href={`#${id}`} onClick={(e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView(); }}>{t}</a></li>)}</ol>
        </nav>
        <article className="prose">
          <H id="q" />
          <ol>
            <li><strong>Sentiment dynamics:</strong> how does expressed sentiment change across race weekends and video formats?</li>
            <li><strong>Narratives:</strong> which themes dominate discussion?</li>
            <li><strong>Controversy:</strong> which weekends split opinion, as distinct from simply attracting criticism?</li>
            <li><strong>Deep learning vs traditional NLP:</strong> do transformers beat lexicon and classical models on F1 language?</li>
            <li><strong>Media framing:</strong> pending (no licensed media corpus).</li>
          </ol>

          <H id="source" />
          <p>Public top-level comments from the official Formula 1 YouTube channel, collected with the YouTube Data API v3 under the YouTube API Services Terms and
            Developer Policies.<a className="fn" href="#fn1" id="r1">1</a> Comment text is kept for at most 30 days and then deleted or refreshed; only aggregates are
            published. Sentiment is a derived metric, labelled as a GRID SIGNAL estimate. Comments are not used to train any model. Race calendar: Jolpica-F1 (CC BY-NC-SA 4.0).</p>

          <H id="sample" />
          <p>The rule was fixed before any comment was read: every 2025 upload matching one of six per-weekend formats (qualifying and race highlights, driver
            reactions after qualifying and the race, sprint highlights and reactions). That yields {data.sentiment.rows.length} videos and {fmtInt(totalComments(data))} comments.
            One-off incident videos are excluded because they exist only when something controversial happened and would bias the controversy analysis. Comments were
            fetched in time order, not by YouTube's relevance ranking.</p>

          <H id="pre" />
          <p>Transformer inputs keep case, punctuation and emoji; URLs become a placeholder. Near-duplicates are found with a normalised text hash
            (emoji-only comments keep their symbols). Driver and team names are removed only for topic modelling.</p>

          <H id="missing" />
          <ul>
            <li>Comments deleted before collection are absent; they are likely harsher than average, so negativity is probably understated.</li>
            <li>The pool is a November 2026 snapshot of 2025 videos. Comments deleted later are removed at each 30-day refresh.</li>
          </ul>

          <H id="labels" />
          <p>{lab} comments were sampled for evaluation, stratified by race and format, with comments naming a driver or team over-sampled to about half; sampling
            weights correct for this. Races were split 6 development / 18 test.</p>
          <p><strong>Evaluation labels: AI-assisted annotation (Claude Opus 5.5)</strong> following the published guide (overall sentiment, sarcasm, up to three
            targets). No human validation round was completed, so scores measure agreement with these labels. About 30% of items were flagged uncertain.</p>

          <H id="models" />
          <div className="table-scroll"><table>
            <thead><tr><th>Model</th><th>Architecture</th><th>Training</th><th>Licence</th></tr></thead>
            <tbody>
              <tr><td>VADER</td><td>Rule-based lexicon</td><td>none</td><td>MIT</td></tr>
              <tr><td>TF-IDF + LogReg / Linear SVM</td><td>Word 1–2-grams + char 2–5-grams</td><td>DynaSent round 2</td><td>CC BY 4.0 data</td></tr>
              <tr><td>RoBERTa-Twitter</td><td>RoBERTa-base, 125M params, Twitter-pretrained</td><td>inference only</td><td>CC BY 4.0</td></tr>
              <tr><td>DistilBERT-SST2</td><td>DistilBERT, 67M params, binary</td><td>inference only; neutral band tuned on dev</td><td>Apache-2.0</td></tr>
            </tbody>
          </table></div>

          <H id="eval" />
          <p>Macro-F1 over three classes; mixed and off-topic items are excluded and counted. 95% intervals come from a cluster bootstrap over races (2,000
            resamples), because comments from one race are not independent. Model differences use paired bootstraps. The test races were scored once.</p>

          <H id="correct" />
          <p>The production model misses many negative comments, so counting its labels would understate negativity. With <em>M</em> the matrix of error rates
            (estimated per video format on the labelled set, weighted to the population) and <em>q</em> the observed shares, the true shares <em>p</em> solve:<a className="fn" href="#fn2" id="r2">2</a></p>
          <div className="eq">min ‖ M·p − q ‖²   subject to  p ≥ 0,  Σ p = 1</div>
          <p>The bootstrap resamples both the labelled set and each video's comments, so intervals include classifier uncertainty. {data.sentiment.correction}.</p>

          <H id="contro" />
          <p>Per race, the four core formats are weighted equally. Disagreement is the variance of a −1/0/+1 score:</p>
          <div className="eq">D = p<sub>pos</sub> + p<sub>neg</sub> − (p<sub>pos</sub> − p<sub>neg</sub>)²    D ∈ [0, 1]</div>
          <p>It was checked on controlled cases (all negative → 0; 50/50 → 1; 80% negative → 0.16). P(top 3) is the share of 1,000 resamples in which a race ranks
            in the top three. Stance is not measured.</p>

          <H id="topics" />
          <p>{data.topics.method}. Stability: {data.topics.stability.method}, matched by cosine similarity; topics below 0.7 are hidden. Weak assignments stay
            unassigned. Labels: {data.topics.labels_by}.</p>

          <H id="events" />
          <p><Status kind="unavailable">Not yet published</Status></p>
          <p>Comments arrive mostly within 24 hours of a video, and there is no pre-event period inside a video. Before/after comparisons across formats mix audiences,
            so no causal or event-study claims are made yet.</p>

          <H id="privacy" />
          <ul>
            <li>No usernames, channel IDs, profile data or comment text are published. Groups under 10 comments are suppressed. No commenter is profiled.</li>
            <li>For annotation, sampled comment text was processed by an AI service (Anthropic's Claude).</li>
          </ul>

          <H id="limits" />
          <ul>
            <li>One channel (official, moderated) and one season: findings describe this sample, not F1 fans.</li>
            <li>AI-assisted labels without human validation; best model macro-F1 about 0.6.</li>
            <li>Sentiment is not stance; disagreement is not polarization into camps.</li>
          </ul>

          <H id="status" />
          <div className="table-scroll"><table>
            <thead><tr><th>Component</th><th>Status</th></tr></thead>
            <tbody>
              {[["Sampling, collection, 30-day retention", "available"], ["Model benchmark (6 models, dev + test)", "available"],
                ["Corrected sentiment by race and format", "available"], ["Controversy measures with uncertainty", "available"],
                ["Topic model with stability check", "available"], ["Signal Monitor", "available"],
                ["Driver-level (target-aware) sentiment", "unavailable"], ["Event studies", "unavailable"],
                ["Human validation of labels", "unavailable"], ["Media framing (RQ5)", "unavailable"]].map(([c, s]) =>
                <tr key={c}><td>{c}</td><td><Status kind={s as "available" | "unavailable"}>{s === "available" ? "Done" : "Pending"}</Status></td></tr>)}
            </tbody>
          </table></div>

          <H id="refs" />
          <ul className="small">
            <li>Barbieri, F., Camacho-Collados, J., Espinosa-Anke, L., &amp; Neves, L. (2020). TweetEval: Unified benchmark and comparative evaluation for tweet classification. <em>Findings of EMNLP 2020</em>.</li>
            <li>Forman, G. (2008). Quantifying counts and costs via classification. <em>Data Mining and Knowledge Discovery</em>, 17(2), 164–206.</li>
            <li>Hutto, C. J., &amp; Gilbert, E. (2014). VADER: A parsimonious rule-based model for sentiment analysis of social media text. <em>Proceedings of ICWSM</em>.</li>
            <li>Lee, D. D., &amp; Seung, H. S. (1999). Learning the parts of objects by non-negative matrix factorization. <em>Nature</em>, 401, 788–791.</li>
            <li>Potts, C., Wu, Z., Geiger, A., &amp; Kiela, D. (2021). DynaSent: A dynamic benchmark for sentiment analysis. <em>Proceedings of ACL-IJCNLP 2021</em>.</li>
            <li>Sanh, V., Debut, L., Chaumond, J., &amp; Wolf, T. (2019). DistilBERT, a distilled version of BERT. <em>arXiv:1910.01108</em>.</li>
            <li>Socher, R., et al. (2013). Recursive deep models for semantic compositionality over a sentiment treebank. <em>Proceedings of EMNLP 2013</em>.</li>
          </ul>

          <div className="footnotes">
            <p id="fn1">1. YouTube API Services Developer Policies, section III.E.4 (data storage) and the derived-metrics policy for analytics use cases. <a href="#r1">↩</a></p>
            <p id="fn2">2. Adjusted classify-and-count (Forman 2008), solved as constrained least squares. <a href="#r2">↩</a></p>
          </div>
        </article>
      </div>
    </div>
  );
}
