import { useMemo, useRef, useState } from "react";
import { useWidth } from "./charts";
import { mean, pct, raceName, VIDEO_TYPES, type AllData } from "../data";

export type SentMetric = "net" | "negative";

export interface MonitorRace {
  gp: string; round: number; date: string; volume: number;
  net: number; netCI: [number, number]; neg: number; negCI: [number, number];
  dis: number; disCI: [number, number]; topic: number;
}

export function buildMonitor(data: AllData, topicId: number): MonitorRace[] {
  const prev = new Map<string, number>();
  for (const p of data.topics.prevalence) prev.set(`${p.gp_key}|${p.video_type}|${p.topic}`, p.share);
  return [...data.controversy.rows].sort((a, b) => a.round - b.round).map((r) => ({
    gp: r.gp_key, round: r.round, date: r.race_start_utc?.slice(0, 10) ?? "", volume: r.attention,
    net: r.net_sentiment, netCI: r.net_sentiment_ci, neg: r.negativity, negCI: r.negativity_ci,
    dis: r.disagreement, disCI: r.disagreement_ci,
    topic: mean(VIDEO_TYPES.map((vt) => prev.get(`${r.gp_key}|${vt}|${topicId}`) ?? 0)),
  }));
}

/**
 * THE SIGNAL MONITOR: four coordinated lanes on one race-weekend axis.
 * Every value comes from the committed result files; nothing is interpolated.
 */
export function SignalMonitor({ races, selected, compare, onSelect, metric, topicName, compact }: {
  races: MonitorRace[]; selected: string; compare?: string; onSelect: (gp: string) => void;
  metric: SentMetric; topicName: string; compact?: boolean;
}) {
  const { ref, w } = useWidth<HTMLDivElement>(1100);
  const box = useRef<HTMLDivElement>(null);
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  const narrow = w < 620;
  const lw = narrow ? 8 : 112, r = 14;
  const lanes = compact
    ? [{ key: "vol", h: 54 }, { key: "sent", h: 92 }]
    : [{ key: "vol", h: 64 }, { key: "sent", h: 110 }, { key: "dis", h: 82 }, { key: "topic", h: 64 }];
  const gap = 14, axisH = 30, labH = 18;
  let acc = 4;
  const laneY = lanes.map((l) => { const y0 = acc + labH; acc = y0 + l.h + gap; return { ...l, y0 }; });
  const H = acc - gap + axisH;
  const n = races.length;
  const x = (i: number) => lw + ((i + 0.5) / n) * (w - lw - r);
  const bw = Math.max(4, ((w - lw - r) / n) * 0.56);
  const idxSel = races.findIndex((d) => d.gp === selected), idxCmp = races.findIndex((d) => d.gp === compare);

  const vMax = Math.max(...races.map((d) => d.volume));
  const sVals = races.flatMap((d) => (metric === "net" ? d.netCI : d.negCI));
  const sLo = metric === "net" ? Math.min(-0.3, ...sVals) : 0, sHi = metric === "net" ? Math.max(0.3, ...sVals) : Math.max(0.7, ...sVals);
  const tMax = Math.max(0.01, ...races.map((d) => d.topic)) * 1.15;

  const ly = (lane: number, v: number, lo: number, hi: number) =>
    laneY[lane].y0 + laneY[lane].h - ((v - lo) / (hi - lo)) * laneY[lane].h;
  const path = (lane: number, vals: number[], lo: number, hi: number) =>
    vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${ly(lane, v, lo, hi).toFixed(1)}`).join(" ");
  const bandPath = (lane: number, ci: [number, number][], lo: number, hi: number) => {
    const up = ci.map((c, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${ly(lane, c[1], lo, hi).toFixed(1)}`).join(" ");
    const dn = [...ci].reverse().map((c, j) => `L${x(ci.length - 1 - j).toFixed(1)},${ly(lane, c[0], lo, hi).toFixed(1)}`).join(" ");
    return `${up} ${dn} Z`;
  };

  const tipFor = (d: MonitorRace) =>
    `R${d.round} ${raceName(d.gp)} · ${d.date}\nvolume ${d.volume.toLocaleString("en-US")} comments\n` +
    `net sentiment ${(d.net * 100).toFixed(0)} pts [${(d.netCI[0] * 100).toFixed(0)}, ${(d.netCI[1] * 100).toFixed(0)}]\n` +
    `negative ${pct(d.neg)} [${pct(d.negCI[0])}–${pct(d.negCI[1])}]\n` +
    `disagreement ${d.dis.toFixed(2)} [${d.disCI[0].toFixed(2)}–${d.disCI[1].toFixed(2)}]\n` +
    `${topicName}: ${pct(d.topic, 1)} of comments`;

  const show = (e: React.MouseEvent | React.FocusEvent, d: MonitorRace) => {
    const b = box.current?.getBoundingClientRect(); if (!b) return;
    const t = (e.currentTarget as Element).getBoundingClientRect();
    const mx = "clientX" in e ? e.clientX : t.left + t.width / 2;
    setTip({ x: Math.max(0, Math.min(mx - b.left + 14, b.width - 260)), y: 8, text: tipFor(d) });
  };
  const sentLane = laneY[1];
  const labels = useMemo(() => ({
    vol: "Discussion volume", sent: metric === "net" ? "Net sentiment" : "Negative share",
    dis: "Disagreement", topic: `Topic: ${topicName}`,
  }), [metric, topicName]);

  return (
    <div ref={box} style={{ position: "relative" }}>
      <div ref={ref}>
        <svg width={w} height={H} role="img"
          aria-label={`Signal Monitor: ${labels.vol}, ${labels.sent}${compact ? "" : `, ${labels.dis}, ${labels.topic}`} for each 2025 race. Use the table view for exact values.`}>
          {/* selection + comparison bands */}
          {idxCmp >= 0 && <rect x={x(idxCmp) - bw * .9} y={0} width={bw * 1.8} height={H - axisH + 4} fill="var(--cyan)" opacity={0.13} rx={4} />}
          {idxSel >= 0 && <rect x={x(idxSel) - bw * .9} y={0} width={bw * 1.8} height={H - axisH + 4} fill="var(--coral)" opacity={0.16} rx={4} />}

          {laneY.map((l) => (
            <g key={l.key}>
              <text className="lane-lab" x={narrow ? 8 : lw} y={l.y0 - 7}>{labels[l.key as keyof typeof labels]}</text>
              <line x1={lw} x2={w - r} y1={l.y0 + l.h} y2={l.y0 + l.h} stroke="var(--ink-line)" />
            </g>
          ))}

          {/* lane 0: volume bars */}
          {races.map((d, i) => {
            const h = (d.volume / vMax) * (laneY[0].h - 6);
            return <rect key={d.gp} x={x(i) - bw / 2} y={laneY[0].y0 + laneY[0].h - h} width={bw} height={h} rx={2}
              fill={i === idxSel ? "var(--coral)" : i === idxCmp ? "var(--cyan)" : "#3b5062"} />;
          })}
          {!narrow && <text className="ax" x={lw - 8} y={laneY[0].y0 + 12} textAnchor="end">{(vMax / 1000).toFixed(0)}k</text>}

          {/* lane 1: sentiment with 95% band */}
          {metric === "net" && <line x1={lw} x2={w - r} y1={ly(1, 0, sLo, sHi)} y2={ly(1, 0, sLo, sHi)} stroke="var(--on-dark-3)" strokeDasharray="2 5" />}
          <path d={bandPath(1, races.map((d) => (metric === "net" ? d.netCI : d.negCI)), sLo, sHi)} fill="#f05a59" opacity={0.13} />
          <path d={path(1, races.map((d) => (metric === "net" ? d.net : d.neg)), sLo, sHi)} fill="none" stroke="var(--coral)" strokeWidth={2} />
          {races.map((d, i) => <circle key={d.gp} cx={x(i)} cy={ly(1, metric === "net" ? d.net : d.neg, sLo, sHi)} r={i === idxSel ? 5 : 3}
            fill="var(--ink)" stroke="var(--coral)" strokeWidth={1.8} />)}
          {!narrow && <>
            <text className="ax" x={lw - 8} y={sentLane.y0 + 10} textAnchor="end">{metric === "net" ? `+${(sHi * 100).toFixed(0)}` : pct(sHi)}</text>
            <text className="ax" x={lw - 8} y={sentLane.y0 + sentLane.h} textAnchor="end">{metric === "net" ? (sLo * 100).toFixed(0) : "0%"}</text>
          </>}

          {!compact && <>
            {/* lane 2: disagreement dots + intervals */}
            {races.map((d, i) => <g key={d.gp}>
              <line x1={x(i)} x2={x(i)} y1={ly(2, d.disCI[0], 0.5, 1)} y2={ly(2, d.disCI[1], 0.5, 1)} stroke="var(--cyan)" strokeWidth={2} opacity={0.45} />
              <circle cx={x(i)} cy={ly(2, d.dis, 0.5, 1)} r={i === idxSel ? 5 : 3.5} fill="var(--cyan)" stroke="var(--ink-2)" strokeWidth={1.5} />
            </g>)}
            {!narrow && <><text className="ax" x={lw - 8} y={laneY[2].y0 + 10} textAnchor="end">1.0</text>
              <text className="ax" x={lw - 8} y={laneY[2].y0 + laneY[2].h} textAnchor="end">0.5</text></>}
            {/* lane 3: topic activity */}
            {races.map((d, i) => {
              const h = (d.topic / tMax) * (laneY[3].h - 4);
              return <rect key={d.gp} x={x(i) - bw / 2} y={laneY[3].y0 + laneY[3].h - h} width={bw} height={h} rx={2}
                fill={i === idxSel ? "var(--coral)" : "#2f7f8a"} opacity={0.9} />;
            })}
            {!narrow && <text className="ax" x={lw - 8} y={laneY[3].y0 + 12} textAnchor="end">{pct(tMax / 1.15, 1)}</text>}
          </>}

          {/* race-weekend markers on the shared axis */}
          {races.map((d, i) => (
            <g key={d.gp} style={{ cursor: "pointer" }} role="button" tabIndex={0}
              aria-label={`Select R${d.round} ${raceName(d.gp)}`} aria-pressed={i === idxSel}
              onClick={() => onSelect(d.gp)} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onSelect(d.gp))}
              onMouseMove={(e) => show(e, d)} onFocus={(e) => show(e, d)} onMouseLeave={() => setTip(null)} onBlur={() => setTip(null)}>
              <rect x={x(i) - (w - lw - r) / n / 2} y={0} width={(w - lw - r) / n} height={H} fill="transparent" />
              <path d={`M${x(i)},${H - axisH + 6} l4,6 l-4,6 l-4,-6 z`} fill={i === idxSel ? "var(--coral)" : i === idxCmp ? "var(--cyan)" : "var(--on-dark-3)"} />
              {(!narrow || i % 3 === 0 || i === idxSel) &&
                <text className="ax" x={x(i)} y={H - 2} textAnchor="middle" style={{ fill: i === idxSel ? "#fff" : undefined }}>{d.round}</text>}
            </g>
          ))}
        </svg>
      </div>
      {tip && <div className="tip" style={{ left: tip.x, top: tip.y }} role="status">{tip.text}</div>}
    </div>
  );
}
