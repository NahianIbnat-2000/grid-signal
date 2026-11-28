import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";

/* ---------------------------------------------------------------- shared */
export function useWidth<T extends HTMLElement>(fallback = 760) {
  const ref = useRef<T>(null);
  const [w, setW] = useState(fallback);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const set = () => setW(Math.max(260, Math.round(el.clientWidth)));
    set();
    const ro = new ResizeObserver(set);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return { ref, w };
}

interface TipState { x: number; y: number; text: string }
function useTip(container: React.RefObject<HTMLElement>) {
  const [tip, setTip] = useState<TipState | null>(null);
  const show = (e: React.MouseEvent | React.FocusEvent, text: string) => {
    const box = container.current?.getBoundingClientRect();
    if (!box) return;
    const t = (e.currentTarget as Element).getBoundingClientRect();
    const mx = "clientX" in e ? e.clientX : t.left + t.width / 2;
    const my = "clientY" in e ? e.clientY : t.top;
    const x = Math.min(mx - box.left + 14, box.width - 230);
    setTip({ x: Math.max(0, x), y: my - box.top - 12, text });
  };
  const node = tip ? <div className="tip" style={{ left: tip.x, top: tip.y }} role="status">{tip.text}</div> : null;
  return { node, show, hide: () => setTip(null) };
}
const hover = (t: ReturnType<typeof useTip>, text: string) => ({
  tabIndex: 0, "aria-label": text.replace(/\n/g, ", "),
  onMouseMove: (e: React.MouseEvent) => t.show(e, text), onFocus: (e: React.FocusEvent) => t.show(e, text),
  onMouseLeave: t.hide, onBlur: t.hide,
});
const ticks = (lo: number, hi: number, n = 5) => Array.from({ length: n + 1 }, (_, i) => lo + ((hi - lo) * i) / n);

export const SHAPE = { positive: "▲", neutral: "●", negative: "▼" } as const;

export function ChartFrame({ title, sub, children, legend, dark, action }: {
  title: string; sub?: string; children: ReactNode; legend?: ReactNode; dark?: boolean; action?: ReactNode;
}) {
  return (
    <figure className={`chart${dark ? " dark-chart" : ""}`} style={{ margin: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start", flexWrap: "wrap" }}>
        <div><p className="chart-title">{title}</p>{sub && <p className="chart-sub">{sub}</p>}</div>
        {action}
      </div>
      {legend}
      {children}
    </figure>
  );
}

export function SentimentLegend() {
  return (
    <div className="legend" aria-label="legend">
      <span><span className="shape" style={{ color: "var(--neg)" }}>{SHAPE.negative}</span>Negative</span>
      <span><span className="shape" style={{ color: "var(--neu-ink)" }}>{SHAPE.neutral}</span>Neutral</span>
      <span><span className="shape" style={{ color: "var(--pos)" }}>{SHAPE.positive}</span>Positive</span>
    </div>
  );
}

/* marker in a given shape so sentiment is never colour-only */
function Mark({ x, y, r = 5.5, shape, fill }: { x: number; y: number; r?: number; shape?: "positive" | "negative" | "neutral" | "dot"; fill: string }) {
  if (shape === "positive") return <path d={`M${x},${y - r * 1.15} L${x + r},${y + r * .75} L${x - r},${y + r * .75} Z`} fill={fill} stroke="var(--white)" strokeWidth={1.5} />;
  if (shape === "negative") return <path d={`M${x},${y + r * 1.15} L${x + r},${y - r * .75} L${x - r},${y - r * .75} Z`} fill={fill} stroke="var(--white)" strokeWidth={1.5} />;
  return <circle cx={x} cy={y} r={r} fill={fill} stroke="var(--white)" strokeWidth={2} />;
}

/* ---------------------------------------------------------------- dot + interval */
export interface DotRow { key: string; label: string; value: number; lo?: number; hi?: number; color?: string; tip: string;
  muted?: boolean; group?: string; shape?: "positive" | "negative" | "neutral" | "dot" }
export function DotCI({ rows, domain, fmt, labelWidth = 150, refLine, ariaLabel }: {
  rows: DotRow[]; domain: [number, number]; fmt: (x: number) => string; labelWidth?: number;
  refLine?: { value: number; label: string }; ariaLabel: string;
}) {
  const { ref, w } = useWidth<HTMLDivElement>();
  const t = useTip(ref);
  const lw = Math.min(labelWidth, w * 0.42), rowH = w < 500 ? 30 : 28, top = 6, bottom = 30, right = 18;
  const H = top + rows.length * rowH + bottom;
  const x = (v: number) => lw + ((v - domain[0]) / (domain[1] - domain[0])) * (w - lw - right);
  const nT = w < 500 ? 4 : 5;
  let last: string | undefined;
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <svg width={w} height={H} role="img" aria-label={ariaLabel}>
        {ticks(domain[0], domain[1], nT).map((v) => <line key={v} className="gridline" x1={x(v)} x2={x(v)} y1={top} y2={H - bottom} />)}
        {refLine && <g><line x1={x(refLine.value)} x2={x(refLine.value)} y1={top} y2={H - bottom} stroke="var(--slate)" strokeDasharray="3 4" />
          <text className="ax" x={x(refLine.value) + 5} y={top + 11}>{refLine.label}</text></g>}
        {rows.map((r, i) => {
          const cy = top + i * rowH + rowH / 2;
          const newGroup = r.group !== undefined && r.group !== last && i > 0;
          last = r.group;
          const c = r.color ?? "var(--text)";
          return (
            <g key={r.key} opacity={r.muted ? 0.42 : 1}>
              {newGroup && <line x1={0} x2={w} y1={cy - rowH / 2} y2={cy - rowH / 2} stroke="var(--border-2)" />}
              <text className="rowlab" x={lw - 10} y={cy + 4} textAnchor="end">{r.label}</text>
              {r.lo !== undefined && r.hi !== undefined &&
                <line x1={x(r.lo)} x2={x(r.hi)} y1={cy} y2={cy} stroke={c} strokeWidth={2} strokeLinecap="round" opacity={0.5} />}
              <Mark x={x(r.value)} y={cy} shape={r.shape} fill={c} />
              <rect x={0} y={cy - rowH / 2} width={w} height={rowH} fill="transparent" {...hover(t, r.tip)} />
            </g>
          );
        })}
        {ticks(domain[0], domain[1], nT).map((v) => <text key={v} className="ax" x={x(v)} y={H - 9} textAnchor="middle">{fmt(v)}</text>)}
      </svg>
      {t.node}
    </div>
  );
}

/* ---------------------------------------------------------------- strip */
export function Strip({ groups, domain, fmt, color, shape, ariaLabel }: {
  groups: { label: string; points: { value: number; tip: string }[] }[];
  domain: [number, number]; fmt: (x: number) => string; color: string; shape?: "positive" | "negative" | "neutral"; ariaLabel: string;
}) {
  const { ref, w } = useWidth<HTMLDivElement>();
  const t = useTip(ref);
  const narrow = w < 560;
  const rowH = narrow ? 64 : 48, lw = narrow ? 0 : 200, top = 6, bottom = 30, right = 18;
  const H = top + groups.length * rowH + bottom;
  const x = (v: number) => (narrow ? 8 : lw) + ((v - domain[0]) / (domain[1] - domain[0])) * (w - (narrow ? 8 : lw) - right);
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <svg width={w} height={H} role="img" aria-label={ariaLabel}>
        {ticks(domain[0], domain[1], narrow ? 4 : 5).map((v) => <line key={v} className="gridline" x1={x(v)} x2={x(v)} y1={top} y2={H - bottom} />)}
        {groups.map((g, i) => {
          const cy = top + i * rowH + rowH / 2 + (narrow ? 8 : 0);
          const vals = g.points.map((p) => p.value).sort((a, b) => a - b);
          const med = vals[Math.floor(vals.length / 2)];
          return (
            <g key={g.label}>
              <text className="rowlab" x={narrow ? 8 : lw - 12} y={narrow ? cy - 18 : cy + 4} textAnchor={narrow ? "start" : "end"}>{g.label}</text>
              {g.points.map((p, j) => <g key={j} {...hover(t, p.tip)}>
                <Mark x={x(p.value)} y={cy + (((j * 37) % 11) - 5) * 1.4} r={4.3} shape={shape} fill={color} />
              </g>)}
              <line x1={x(med)} x2={x(med)} y1={cy - 14} y2={cy + 14} stroke="var(--text)" strokeWidth={2.5} />
            </g>
          );
        })}
        {ticks(domain[0], domain[1], narrow ? 4 : 5).map((v) => <text key={v} className="ax" x={x(v)} y={H - 9} textAnchor="middle">{fmt(v)}</text>)}
      </svg>
      {t.node}
    </div>
  );
}

/* ---------------------------------------------------------------- distribution bar */
export function DistBar({ neg, neu, pos, height = 16, labels = false }: { neg: number; neu: number; pos: number; height?: number; labels?: boolean }) {
  const total = neg + neu + pos || 1;
  const parts = [["negative", neg, "var(--neg)"], ["neutral", neu, "var(--neu)"], ["positive", pos, "var(--pos)"]] as const;
  return (
    <div>
      <div style={{ display: "flex", gap: 2, height, borderRadius: 3, overflow: "hidden" }} aria-hidden>
        {parts.map(([k, v, c]) => <div key={k} style={{ width: `${(v / total) * 100}%`, background: c, transition: "width .35s var(--ease)" }} />)}
      </div>
      {labels && <div className="num small" style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 12 }}>
        <span>{SHAPE.negative} {(neg * 100).toFixed(0)}%</span><span>{SHAPE.neutral} {(neu * 100).toFixed(0)}%</span><span>{SHAPE.positive} {(pos * 100).toFixed(0)}%</span>
      </div>}
    </div>
  );
}

/* ---------------------------------------------------------------- heatmap */
export function Heatmap({ rows, cols, value, fmt, tip, max, ariaLabel }: {
  rows: { key: string; label: string }[]; cols: { key: string; label: string }[];
  value: (r: string, c: string) => number; fmt: (x: number) => string; tip: (r: string, c: string) => string; max: number; ariaLabel: string;
}) {
  const { ref, w } = useWidth<HTMLDivElement>();
  const t = useTip(ref);
  const minW = 600, W = Math.max(w, minW);
  const lw = Math.min(230, W * 0.32), cw = (W - lw) / cols.length, rh = 32, top = 34;
  const H = top + rows.length * rh + 4;
  const fill = (v: number) => {
    const a = Math.min(v / max, 1);
    const m = (c1: number, c2: number) => Math.round(c1 + (c2 - c1) * a);
    return `rgb(${m(0xee, 0x1c)},${m(0xf6, 0x73)},${m(0xf6, 0x80)})`;
  };
  return (
    <div ref={ref} style={{ position: "relative" }}>
      {w < minW && <div className="scroll-hint">← scroll sideways →</div>}
      <div style={{ overflowX: "auto" }}>
        <svg width={W} height={H} role="img" aria-label={ariaLabel}>
          {cols.map((c, j) => <text key={c.key} className="ax" x={lw + j * cw + cw / 2} y={top - 12} textAnchor="middle">{c.label}</text>)}
          {rows.map((r, i) => (
            <g key={r.key}>
              <text className="rowlab" x={lw - 12} y={top + i * rh + rh / 2 + 4} textAnchor="end">{r.label}</text>
              {cols.map((c, j) => {
                const v = value(r.key, c.key), dark = v / max > 0.55;
                return <g key={c.key} {...hover(t, tip(r.key, c.key))}>
                  <rect x={lw + j * cw + 1} y={top + i * rh + 1} width={cw - 2} height={rh - 2} rx={3} fill={fill(v)} />
                  <text x={lw + j * cw + cw / 2} y={top + i * rh + rh / 2 + 4} textAnchor="middle" className="num"
                    style={{ fontSize: 12, fill: dark ? "#fff" : "var(--text-2)" }}>{fmt(v)}</text>
                </g>;
              })}
            </g>
          ))}
        </svg>
      </div>
      {t.node}
    </div>
  );
}

/* ---------------------------------------------------------------- scatter */
export function Scatter({ points, xd, yd, xlab, ylab, fmt, ariaLabel }: {
  points: { key: string; x: number; y: number; label: string; tip: string; highlight?: boolean }[];
  xd: [number, number]; yd: [number, number]; xlab: string; ylab: string; fmt: (v: number) => string; ariaLabel: string;
}) {
  const { ref, w } = useWidth<HTMLDivElement>();
  const t = useTip(ref);
  const H = Math.min(420, Math.max(300, w * 0.62)), l = 52, r = 18, tp = 14, b = 46;
  const x = (v: number) => l + ((v - xd[0]) / (xd[1] - xd[0])) * (w - l - r);
  const y = (v: number) => H - b - ((v - yd[0]) / (yd[1] - yd[0])) * (H - tp - b);
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <svg width={w} height={H} role="img" aria-label={ariaLabel}>
        {ticks(xd[0], xd[1], 4).map((v) => <line key={"x" + v} className="gridline" x1={x(v)} x2={x(v)} y1={tp} y2={H - b} />)}
        {ticks(yd[0], yd[1], 4).map((v) => <line key={"y" + v} className="gridline" x1={l} x2={w - r} y1={y(v)} y2={y(v)} />)}
        {ticks(xd[0], xd[1], 4).map((v) => <text key={"x" + v} className="ax" x={x(v)} y={H - b + 18} textAnchor="middle">{fmt(v)}</text>)}
        {ticks(yd[0], yd[1], 4).map((v) => <text key={"y" + v} className="ax" x={l - 8} y={y(v) + 4} textAnchor="end">{fmt(v)}</text>)}
        <text className="ax" x={(l + w - r) / 2} y={H - 6} textAnchor="middle">{xlab}</text>
        <text className="ax" x={13} y={(tp + H - b) / 2} textAnchor="middle" transform={`rotate(-90 13 ${(tp + H - b) / 2})`}>{ylab}</text>
        {points.map((p) => <g key={p.key} {...hover(t, p.tip)}>
          <circle cx={x(p.x)} cy={y(p.y)} r={13} fill="transparent" />
          <circle cx={x(p.x)} cy={y(p.y)} r={p.highlight ? 6.5 : 5} fill={p.highlight ? "var(--coral)" : "var(--series)"} stroke="var(--white)" strokeWidth={2} />
          {p.highlight && <text className="ax" x={x(p.x) + 10} y={y(p.y) + 4} style={{ fill: "var(--text)" }}>{p.label}</text>}
        </g>)}
      </svg>
      {t.node}
    </div>
  );
}

/* ---------------------------------------------------------------- confusion */
export function Confusion({ labels, matrix }: { labels: string[]; matrix: number[][] }) {
  const ref = useRef<HTMLDivElement>(null);
  const t = useTip(ref);
  const cell = 76, lw = 90, top = 44, W = lw + labels.length * cell + 6, H = top + labels.length * cell + 28;
  const totals = matrix.map((r) => r.reduce((a, b) => a + b, 0));
  return (
    <div ref={ref} style={{ position: "relative", maxWidth: W }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }} role="img" aria-label="confusion matrix, rows are labels, columns are predictions">
        <text className="ax" x={lw + (labels.length * cell) / 2} y={13} textAnchor="middle">predicted</text>
        {labels.map((l, j) => <text key={l} className="ax" x={lw + j * cell + cell / 2} y={top - 9} textAnchor="middle">{SHAPE[l as keyof typeof SHAPE]} {l.slice(0, 3)}</text>)}
        {labels.map((l, i) => <g key={l}>
          <text className="ax" x={lw - 8} y={top + i * cell + cell / 2 + 4} textAnchor="end">label {l.slice(0, 3)}</text>
          {labels.map((p, j) => {
            const s = matrix[i][j] / (totals[i] || 1);
            const text = `label ${l} → predicted ${p}\n${matrix[i][j]} of ${totals[i]} (${(s * 100).toFixed(0)}%)`;
            return <g key={p} {...hover(t, text)}>
              <rect x={lw + j * cell + 1} y={top + i * cell + 1} width={cell - 2} height={cell - 2} rx={5}
                fill={`rgb(${Math.round(238 - 210 * s)},${Math.round(246 - 131 * s)},${Math.round(246 - 118 * s)})`}
                stroke={i === j ? "var(--text)" : "none"} strokeWidth={1.5} />
              <text x={lw + j * cell + cell / 2} y={top + i * cell + cell / 2 + 5} textAnchor="middle" className="num"
                style={{ fontSize: 14, fill: s > 0.5 ? "#fff" : "var(--text)" }}>{(s * 100).toFixed(0)}%</text>
            </g>;
          })}
        </g>)}
        <text className="ax" x={lw} y={H - 6}>row % · outlined = correct</text>
      </svg>
      {t.node}
    </div>
  );
}

/* ---------------------------------------------------------------- line (topic timeline) */
export function Line({ points, xLabels, yMax, fmt, color, highlight, ariaLabel, band }: {
  points: number[]; xLabels: string[]; yMax: number; fmt: (v: number) => string; color: string;
  highlight?: number; ariaLabel: string; band?: number;
}) {
  const { ref, w } = useWidth<HTMLDivElement>();
  const t = useTip(ref);
  const H = 220, l = 46, r = 14, tp = 12, b = 30;
  const x = (i: number) => l + (i / Math.max(points.length - 1, 1)) * (w - l - r);
  const y = (v: number) => H - b - (v / yMax) * (H - tp - b);
  const d = points.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ");
  const step = w < 560 ? 4 : 2;
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <svg width={w} height={H} role="img" aria-label={ariaLabel}>
        {ticks(0, yMax, 4).map((v) => <g key={v}><line className="gridline" x1={l} x2={w - r} y1={y(v)} y2={y(v)} />
          <text className="ax" x={l - 8} y={y(v) + 4} textAnchor="end">{fmt(v)}</text></g>)}
        {band !== undefined && <line x1={l} x2={w - r} y1={y(band)} y2={y(band)} stroke="var(--slate)" strokeDasharray="3 4" />}
        <path d={d} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
        {points.map((v, i) => <g key={i} {...hover(t, `${xLabels[i]}\n${fmt(v)}`)}>
          <rect x={x(i) - 12} y={tp} width={24} height={H - tp - b} fill="transparent" />
          <circle cx={x(i)} cy={y(v)} r={i === highlight ? 6 : 3.5} fill={i === highlight ? "var(--coral)" : color} stroke="var(--white)" strokeWidth={1.5} />
        </g>)}
        {xLabels.map((s, i) => i % step === 0 && <text key={i} className="ax" x={x(i)} y={H - 8} textAnchor="middle">{s}</text>)}
      </svg>
      {t.node}
    </div>
  );
}

/* ---------------------------------------------------------------- hero ambient waveform (real data, decorative motion) */
export function HeroWave({ values }: { values: number[] }) {
  const { ref, w } = useWidth<HTMLDivElement>(1200);
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0, start = performance.now();
    const tick = (now: number) => { setPhase(((now - start) / 9000) % 1); raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);
  const H = 120, mx = Math.max(...values.map(Math.abs), 0.05);
  const pts = values.map((v, i) => [(i / (values.length - 1)) * w, H / 2 - (v / mx) * (H / 2 - 10)]);
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  return (
    <div ref={ref} aria-hidden style={{ opacity: 0.9 }}>
      <svg width={w} height={H}>
        <defs><linearGradient id="fade" x1="0" x2="1"><stop offset="0" stopColor="#f05a59" stopOpacity=".15" />
          <stop offset={Math.max(0.01, phase).toFixed(3)} stopColor="#f05a59" stopOpacity="1" />
          <stop offset={Math.min(1, phase + 0.25).toFixed(3)} stopColor="#f05a59" stopOpacity=".35" /></linearGradient></defs>
        <line x1={0} x2={w} y1={H / 2} y2={H / 2} stroke="var(--ink-line)" strokeDasharray="2 6" />
        <path d={d} fill="none" stroke="url(#fade)" strokeWidth={2} strokeLinejoin="round" />
      </svg>
    </div>
  );
}
