"""Race calendar and results from the Jolpica-F1 API (Ergast successor).

Terms: free for non-commercial use; data under CC BY-NC-SA 4.0
(https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md).
Rate limits (unauthenticated): 4 req/s burst, 500 req/h sustained.
Any published file built from this data must carry the same licence.
"""
from __future__ import annotations

import argparse
import time
from collections import deque
from pathlib import Path

import pandas as pd
import requests

BASE = "https://api.jolpi.ca/ergast/f1"


class RateLimiter:
    def __init__(self, per_second: int = 4, per_hour: int = 500, clock=time.monotonic, sleep=time.sleep):
        self.per_second, self.per_hour = per_second, per_hour
        self.clock, self.sleep = clock, sleep
        self.calls: deque[float] = deque()

    def wait(self) -> None:
        now = self.clock()
        while self.calls and now - self.calls[0] > 3600:
            self.calls.popleft()
        if len(self.calls) >= self.per_hour:
            self.sleep(3600 - (now - self.calls[0]) + 0.1)
        recent = [t for t in self.calls if now - t < 1]
        if len(recent) >= self.per_second:
            self.sleep(1 - (now - recent[0]) + 0.01)
        self.calls.append(self.clock())


def races_to_frame(payload: dict) -> pd.DataFrame:
    rows = []
    for r in payload["MRData"]["RaceTable"]["Races"]:
        time_known = "time" in r
        start = pd.Timestamp(f"{r['date']}T{r.get('time', '00:00:00Z')}")
        rows.append({
            "season": int(r["season"]), "round": int(r["round"]), "race_name": r["raceName"],
            "circuit_id": r["Circuit"]["circuitId"], "race_start_utc": start,
            "start_time_known": time_known,  # False -> do not use hour-level event windows
        })
    return pd.DataFrame(rows)


def fetch_calendar(season: int, limiter: RateLimiter | None = None) -> pd.DataFrame:
    limiter = limiter or RateLimiter()
    limiter.wait()
    resp = requests.get(f"{BASE}/{season}.json", timeout=30)
    resp.raise_for_status()
    return races_to_frame(resp.json())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("season", type=int)
    a = ap.parse_args()
    df = fetch_calendar(a.season)
    out = Path(f"data/processed/calendar_{a.season}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"{len(df)} races -> {out} (CC BY-NC-SA 4.0, source: Jolpica-F1)")
