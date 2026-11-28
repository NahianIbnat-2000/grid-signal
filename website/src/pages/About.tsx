import { REPO } from "../App";

export default function About() {
  return (
    <div className="wrap page prose">
      <div className="kicker">About</div>
      <h1>About GRID SIGNAL</h1>
      <p className="lede">An independent NLP research observatory exploring sentiment, narratives, and disagreement in Formula 1.</p>

      <h2>Motivation</h2>
      <p>A race result tells us who won. Lap timing tells us who was faster. Neither tells us how people interpreted what happened. GRID SIGNAL asks what
        language can reveal about the way Formula 1 is understood and argued over, and whether deep learning can measure that reliably.</p>

      <h2>Academic objectives</h2>
      <ul>
        <li>Benchmark lexicon, classical and transformer sentiment models on F1-specific language, with honest uncertainty.</li>
        <li>Separate attention, negativity and disagreement instead of treating negativity as controversy.</li>
        <li>Practise transparent, reproducible computational social science on platform data under its access terms.</li>
      </ul>

      <h2>Researcher</h2>
      {/* EDIT: replace the placeholders below with your own details. */}
      <p><strong>Nahian Ibnat</strong></p>
      <p className="muted">[Credentials and affiliation: to be added]</p>
      <p className="muted">[Contact / LinkedIn: to be added]</p>

      <h2>Code &amp; data</h2>
      <p>Source code, sampling rules, the annotation guide and all published result files: <a href={REPO}>{REPO.replace("https://", "")}</a>.
        Raw comments are not published, in line with the YouTube API terms.</p>

      <h2>Independence</h2>
      <p>GRID SIGNAL is not affiliated with, endorsed by or connected to Formula 1, the FIA, any Formula 1 team, YouTube or Google. Formula 1 and related marks
        belong to their owners. All sentiment figures are model estimates produced by this project.</p>
    </div>
  );
}
