import { Fragment, type ReactNode } from "react";

export function Glyph({ size = 26, dark = true }: { size?: number; dark?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="7" fill={dark ? "#17222c" : "#101820"} />
      <path d="M4 8 H28 M4 16 H28 M4 24 H28" stroke="#2a3946" strokeWidth="1" />
      <path d="M3.5 17.5 H9 L12 9 L16.5 24 L19.5 13 L22 18 H28.5" fill="none" stroke="#F05A59" strokeWidth="2.4"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Wordmark() {
  return <><Glyph /><span>GRID <span className="sig">SIGNAL</span></span></>;
}

export type StatusKind = "available" | "incomplete" | "unavailable" | "updated" | "experimental";
const STATUS_TEXT: Record<StatusKind, string> = {
  available: "Data available", incomplete: "Data incomplete", unavailable: "Not available yet",
  updated: "Analysis updated", experimental: "Experimental result",
};
export function Status({ kind, children }: { kind: StatusKind; children?: ReactNode }) {
  return <span className={`status ${kind}`}><i aria-hidden />{children ?? STATUS_TEXT[kind]}</span>;
}

export function Evidence({ title = "Evidence: where this comes from", items, children }: {
  title?: string; items?: [string, ReactNode][]; children?: ReactNode;
}) {
  return (
    <details className="evidence">
      <summary>{title}</summary>
      <div>
        {items && <dl>{items.map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{v}</dd></Fragment>)}</dl>}
        {children}
      </div>
    </details>
  );
}

export function SignalCard({ title, value, period, context, source }: {
  title: string; value: ReactNode; period?: string; context?: ReactNode; source?: string;
}) {
  return (
    <div className="signal-card">
      <span className="t">{title}</span>
      <span className="v">{value}</span>
      {context && <span className="c">{context}</span>}
      {(period || source) && <span className="src">{[period, source].filter(Boolean).join(" · ")}</span>}
    </div>
  );
}

export function PageHead({ kicker, title, tagline, children }: { kicker: string; title: string; tagline?: string; children?: ReactNode }) {
  return (
    <header className="dark grid-bg page-head">
      <div className="wrap">
        <div className="kicker">{kicker}</div>
        <h1>{title}</h1>
        {tagline && <div className="tagline">{tagline}</div>}
        {children}
      </div>
    </header>
  );
}
