import { Link } from "react-router-dom";
import { PageHead, Status } from "../components/ui";

export default function Drivers() {
  return (
    <>
      <PageHead kicker="Driver storylines" title="Drivers" tagline="The story behind the signal.">
        <p className="lede">Profiles of how each driver and team is discussed across the season.</p>
        <div style={{ marginTop: 18 }}><Status kind="incomplete">Data pending: not yet published</Status></div>
      </PageHead>
      <div className="wrap page prose">
        <h2 style={{ marginTop: 0 }}>Why this page is empty</h2>
        <p>Driver pages need <strong>target-aware sentiment</strong>: knowing that "Amazing drive from Leclerc, but Ferrari ruined the strategy" is positive
          about Leclerc and negative about Ferrari. GRID SIGNAL has not yet built or validated that model.</p>
        <p>Assigning a whole comment's sentiment to every driver it names would mislead: the benchmark shows the current model is weakest exactly on comments that
          name a driver or team. Rather than publish numbers that look precise but are wrong, this page stays empty until the method is ready.</p>

        <h2>What will appear here</h2>
        <table>
          <thead><tr><th>Element</th><th>Needs</th><th>Status</th></tr></thead>
          <tbody>
            <tr><td>Driver and team identity, 2025 assignments</td><td>Race data (Jolpica-F1)</td><td><Status kind="available">Available</Status></td></tr>
            <tr><td>Mentions per race (volume)</td><td>Entity linker with nicknames, evaluated</td><td><Status kind="unavailable">Pending</Status></td></tr>
            <tr><td>Sentiment toward each driver</td><td>Target-aware model (AI-assisted target labels exist for evaluation)</td><td><Status kind="unavailable">Not built</Status></td></tr>
            <tr><td>Narrative themes per driver</td><td>Topic model × entity links</td><td><Status kind="unavailable">Not built</Status></td></tr>
            <tr><td>"The story behind the signal"</td><td>Verified race context per change</td><td><Status kind="unavailable">Not built</Status></td></tr>
          </tbody>
        </table>
        <p className="small muted" style={{ marginTop: 14 }}>Planned rules: no portraits or quotes without rights; observed patterns kept separate from interpretation; no personal or
          psychological judgements about drivers.</p>
        <p><Link to="/monitor">Meanwhile, explore race-level signals in the Signal Monitor →</Link></p>
      </div>
    </>
  );
}
