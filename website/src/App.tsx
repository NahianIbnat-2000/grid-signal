import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { lastUpdated, useData } from "./data";
import { Wordmark } from "./components/ui";
import Home from "./pages/Home";
import Monitor from "./pages/Monitor";
import Observatory from "./pages/Observatory";
import Controversy from "./pages/Controversy";
import Narratives from "./pages/Narratives";
import Drivers from "./pages/Drivers";
import Models from "./pages/Models";
import Methods from "./pages/Methods";
import About from "./pages/About";

export const REPO = "https://github.com/NahianIbnat-2000/grid-signal";

const NAV = [
  ["/monitor", "Signal Monitor"], ["/observatory", "Sentiment"], ["/controversy", "Controversy Radar"],
  ["/narratives", "Narratives"], ["/drivers", "Drivers"], ["/models", "Model Arena"], ["/methods", "Research"],
] as const;

export default function App() {
  const { data, error } = useData();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  useEffect(() => { window.scrollTo(0, 0); setOpen(false); }, [loc.pathname]);
  return (
    <>
      <a href="#main" className="skip">Skip to content</a>
      <header className="site-header">
        <div className="wrap">
          <Link to="/" className="wordmark" aria-label="GRID SIGNAL home"><Wordmark /></Link>
          <button className="menu-btn" aria-expanded={open} aria-controls="nav" onClick={() => setOpen(!open)}>{open ? "Close" : "Menu"}</button>
          <nav id="nav" className={`nav${open ? " open" : ""}`} aria-label="Main">
            {NAV.map(([to, label]) => <NavLink key={to} to={to}>{label}</NavLink>)}
          </nav>
        </div>
      </header>
      <main id="main">
        {error && <div className="wrap page"><p className="note warn">Could not load the result files ({error}).</p></div>}
        {!data && !error && <div className="wrap page"><p className="muted">Loading results…</p></div>}
        {data && (
          <Routes>
            <Route path="/" element={<Home data={data} />} />
            <Route path="/monitor" element={<Monitor data={data} />} />
            <Route path="/observatory" element={<Observatory data={data} />} />
            <Route path="/controversy" element={<Controversy data={data} />} />
            <Route path="/narratives" element={<Narratives data={data} />} />
            <Route path="/drivers" element={<Drivers />} />
            <Route path="/models" element={<Models data={data} />} />
            <Route path="/methods" element={<Methods data={data} />} />
            <Route path="/about" element={<About />} />
            <Route path="*" element={<div className="wrap page"><h1>Not found</h1><Link to="/">Back to GRID SIGNAL</Link></div>} />
          </Routes>
        )}
      </main>
      <footer className="site-footer">
        <div className="wrap cols">
          <div>
            <div className="wordmark" style={{ marginBottom: 14 }}><Wordmark /></div>
            <p>The Signal Room: where the noise of Formula 1 becomes measurable insight.</p>
            <p>An independent research project. Not affiliated with or endorsed by Formula 1, the FIA, any team, YouTube or Google.
              Sentiment figures are GRID SIGNAL model estimates, not YouTube data.</p>
          </div>
          <div>
            <h4>Explore</h4>
            <ul>{NAV.map(([to, label]) => <li key={to}><Link to={to}>{label}</Link></li>)}<li><Link to="/about">About</Link></li></ul>
          </div>
          <div>
            <h4>Provenance</h4>
            <ul>
              <li>{data ? `Results generated ${lastUpdated(data)}` : "Static results"}</li>
              <li>No live data · no tracking</li>
              <li><a href={REPO}>Code on GitHub</a></li>
              <li>Race data: Jolpica-F1 (CC BY-NC-SA 4.0)</li>
            </ul>
          </div>
        </div>
      </footer>
    </>
  );
}
