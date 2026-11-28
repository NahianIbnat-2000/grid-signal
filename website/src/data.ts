import { useEffect, useState } from "react";

export type CI = [number, number];

export interface SentimentRow {
  gp_key: string; video_type: string; n: number;
  raw_negative: number; raw_neutral: number; raw_positive: number;
  adj_negative: number; adj_negative_lo: number; adj_negative_hi: number;
  adj_neutral: number; adj_neutral_lo: number; adj_neutral_hi: number;
  adj_positive: number; adj_positive_lo: number; adj_positive_hi: number;
}
export interface ControversyRow {
  gp_key: string; attention: number; negativity: number; negativity_ci: CI;
  net_sentiment: number; net_sentiment_ci: CI; disagreement: number; disagreement_ci: CI;
  p_top3_disagreement: number; round: number; race_name: string; race_start_utc: string;
}
export interface Topic {
  id: number; name: string; kind: string; show: boolean; note: string;
  top_words: string[]; overall_share: number; stability: number;
}
export interface TopicsFile {
  generated_at: string; method: string; unassigned_share: number; labels_by: string;
  stability: { mean: number; method: string }; topics: Topic[];
  prevalence: { gp_key: string; video_type: string; topic: number; share: number }[];
}
export interface Metrics {
  n: number; accuracy: number; macro_f1: number; weighted_f1: number; macro_f1_ci95: CI;
  per_class: Record<string, { precision: number; recall: number; f1: number }>;
  confusion: { labels: string[]; matrix: number[][] };
}
export interface ModelResult {
  family: string; training: string; licence: string; ms_per_comment: number;
  sample: Metrics; population_weighted: Metrics; ece?: number;
  subgroups: Record<string, { n: number; macro_f1: number; accuracy: number }>;
  dynasent_test_macro_f1?: number; neutral_band?: number;
}
export interface BaselinesFile {
  split: string; generated_at: string; races: number; bootstrap: string; gold_labels_by: string[];
  counts: { labelled: number; scored_3class: number; label_distribution: Record<string, number> };
  models: Record<string, ModelResult>;
  comparisons: Record<string, { diff: number; ci95: CI; share_resamples_a_better: number }>;
}
export interface AllData {
  sentiment: { generated_at: string; correction: string; gold_labels_by: string[]; rows: SentimentRow[] };
  controversy: { generated_at: string; rows: ControversyRow[] };
  topics: TopicsFile;
  test: BaselinesFile;
  dev: BaselinesFile;
}

let cache: Promise<AllData> | null = null;
function load(): Promise<AllData> {
  const get = (f: string) => fetch(`./data/${f}.json`).then((r) => {
    if (!r.ok) throw new Error(`${f}: ${r.status}`);
    return r.json();
  });
  cache ??= Promise.all([get("sentiment_by_race"), get("controversy_by_race"), get("topics"),
    get("baselines_test"), get("baselines_dev")])
    .then(([sentiment, controversy, topics, test, dev]) => ({ sentiment, controversy, topics, test, dev }));
  return cache;
}

export function useData(): { data: AllData | null; error: string | null } {
  const [data, setData] = useState<AllData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { load().then(setData).catch((e) => setError(String(e))); }, []);
  return { data, error };
}

/* ---------- labels & helpers ---------- */
export const VIDEO_TYPES = ["qualifying_highlights", "qualifying_reactions", "race_highlights", "race_reactions"] as const;
export const VIDEO_LABEL: Record<string, string> = {
  qualifying_highlights: "Qualifying highlights",
  qualifying_reactions: "Qualifying driver reactions",
  race_highlights: "Race highlights",
  race_reactions: "Race driver reactions",
  sprint_highlights: "Sprint highlights",
  sprint_reactions: "Sprint driver reactions",
};
export const MODEL_LABEL: Record<string, string> = {
  vader: "VADER (lexicon)",
  vader_tuned: "VADER, threshold tuned",
  tfidf_logreg: "TF-IDF + Logistic Regression",
  tfidf_svm: "TF-IDF + Linear SVM",
  roberta_twitter: "RoBERTa-Twitter (transformer)",
  distilbert_sst2: "DistilBERT-SST2 (transformer)",
  distilbert_dynasent_ft: "DistilBERT fine-tuned on DynaSent",
};
export const FAMILY_LABEL: Record<string, string> = {
  lexicon: "Lexicon", classical_ml: "Classical ML", transformer: "Transformer",
};

export function raceName(gp: string): string {
  const base = gp.replace(/ grand prix$/, "").replace(/\b\w/g, (c) => c.toUpperCase()).replace("Sao Paulo", "São Paulo");
  return `${base} GP`;
}
export const pct = (x: number, d = 0) => `${(x * 100).toFixed(d)}%`;
export const f3 = (x: number) => x.toFixed(3);
export const fmtInt = (x: number) => x.toLocaleString("en-US");

export function roundOf(data: AllData): Record<string, number> {
  return Object.fromEntries(data.controversy.rows.map((r) => [r.gp_key, r.round]));
}
export function lastUpdated(data: AllData): string {
  const ts = [data.sentiment.generated_at, data.controversy.generated_at, data.topics.generated_at,
    data.test.generated_at].sort().at(-1)!;
  return new Date(ts).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}
export function totalComments(data: AllData): number {
  return data.sentiment.rows.reduce((s, r) => s + r.n, 0);
}
export function racesInOrder(data: AllData) {
  return [...data.controversy.rows].sort((a, b) => a.round - b.round);
}
export const TOPIC_DESC: Record<string, string> = {
  "Title race & predictions": "Who will win the championship; predictions for the next race.",
  "Boring races & calendar": "Complaints that races or tracks are dull, often Monaco; calendar talk.",
  "Car pace & safety car": "Which car is fastest, plus safety-car periods (two ideas that share words).",
  "Penalties & pit stops": "Penalties, pit stops and what happened on track.",
  "\"World champion\" talk": "Calling a driver a (future) world champion or champion material.",
  "Driver of the day / best driver": "Driver of the day votes and who drove best.",
  "Best driver & car of the season": "Season-level rankings of drivers and cars.",
  "Rookies": "The 2025 rookie class and first-season performances.",
  "\"Simply lovely\" catchphrase": "A recurring radio catchphrase used as a meme.",
  "\"Great job\" praise": "Short praise for a drive or for the video.",
  "\"Let's go\" cheering": "Cheering and hope for a driver or team.",
  "GOAT talk": "\"Greatest of all time\" claims and replies.",
  "Happy & sad reactions": "Emotional reactions: joy, sadness, relief.",
  "Pole laps & 'insane' moments": "Excitement about pole laps and spectacular moments.",
};
export const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / Math.max(xs.length, 1);
