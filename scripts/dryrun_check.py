"""Dry-run check: does the scan reach the window start, and is every race covered?

Run:  python -m scripts.dryrun_check
Costs about 1 + max_upload_pages units per channel. Writes only to data/restricted/.
"""
from pathlib import Path

import pandas as pd
import yaml

from pipelines.collect import _ts, compile_types, select_videos
from pipelines.quota import QuotaTracker
from pipelines.youtube_client import YouTubeClient

f = yaml.safe_load(Path("data/manifests/sampling_frame.yaml").read_text())
yt = YouTubeClient(QuotaTracker(Path("data/restricted/quota_state.json")))
types = compile_types(f)
s, e = _ts(f["window"]["start"]), _ts(f["window"]["end"])

out = []
for c in f["channels"]:
    ch = yt.channel_by_handle(c["handle"])
    ups = list(yt.uploads(ch["contentDetails"]["relatedPlaylists"]["uploads"],
                          max_pages=c.get("max_upload_pages", 20)))
    oldest = min(_ts(u["contentDetails"].get("videoPublishedAt") or u["snippet"]["publishedAt"]) for u in ups)
    print(f"{c['handle']}: scanned {len(ups)} | oldest {oldest:%Y-%m-%d} | "
          f"reached window start: {'YES' if oldest <= s else 'NO - raise max_upload_pages'}")
    sel = pd.DataFrame(select_videos(ups, s, e, types))
    sel["channel"] = c["handle"]
    out.append(sel)

sel = pd.concat(out).sort_values("published_at")
print(f"selected: {len(sel)}")
print(sel.video_type.value_counts().to_string())

cal_path = Path("data/processed/calendar_2025.csv")
if cal_path.exists():
    from pipelines.collect import gp_key
    cal = pd.read_csv(cal_path)
    cal["gp_key"] = cal["race_name"].map(gp_key)
    grid = sel.pivot_table(index="gp_key", columns="video_type", values="video_id", aggfunc="count")
    core = ["qualifying_highlights", "qualifying_reactions", "race_highlights", "race_reactions"]
    missing = [(g, t) for g in cal.gp_key for t in core
               if g not in grid.index or t not in grid.columns or pd.isna(grid.loc[g, t])]
    unmatched = sorted(set(sel.gp_key.dropna()) - set(cal.gp_key))
    print("races missing a core video:", missing or "none")
    print("titles not matching a calendar race:", unmatched or "none")

Path("data/restricted").mkdir(parents=True, exist_ok=True)
sel.to_csv("data/restricted/dryrun_selected.csv", index=False)
print("saved data/restricted/dryrun_selected.csv")
