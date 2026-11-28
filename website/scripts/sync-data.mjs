// Copy the committed, aggregate-only result files into the site bundle.
// The site never reads raw comments: only research/results/*.json.
import { copyFileSync, mkdirSync, existsSync, readFileSync } from "node:fs";
const files = ["sentiment_by_race", "controversy_by_race", "topics", "baselines_test", "baselines_dev"];
mkdirSync("public/data", { recursive: true });
for (const f of files) {
  const src = `../research/results/${f}.json`;
  if (!existsSync(src)) { console.error(`missing ${src}`); process.exit(1); }
  const txt = readFileSync(src, "utf8");
  if (/"text"\s*:|AIza[0-9A-Za-z_-]{20,}/.test(txt)) { console.error(`refusing ${f}: looks like raw text or a key`); process.exit(1); }
  copyFileSync(src, `public/data/${f}.json`);
}
console.log(`synced ${files.length} result files`);
