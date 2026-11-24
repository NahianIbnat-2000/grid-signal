"""Daily quota bookkeeping for the YouTube Data API v3.

Costs from https://developers.google.com/youtube/v3/determine_quota_cost
(checked 2026-11-23). search.list has its own bucket of 100 calls/day,
separate from the 10,000-unit pool, so it is tracked separately.
Quotas reset at midnight Pacific Time.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

COSTS = {
    "commentThreads.list": 1,
    "comments.list": 1,
    "videos.list": 1,
    "channels.list": 1,
    "playlistItems.list": 1,
    "search.list": 1,  # charged to its own 100/day bucket
}
SEPARATE_BUCKETS = {"search.list": 100}
DEFAULT_DAILY_UNITS = 10_000
PT = ZoneInfo("America/Los_Angeles")


class QuotaExceeded(RuntimeError):
    pass


@dataclass
class QuotaTracker:
    path: Path
    daily_units: int = DEFAULT_DAILY_UNITS
    safety_margin: int = 500  # leave headroom for refresh/deletion checks
    state: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
        self._roll_day()

    @staticmethod
    def _today() -> str:
        return datetime.now(PT).date().isoformat()

    def _roll_day(self) -> None:
        if self.state.get("day") != self._today():
            self.state = {"day": self._today(), "units": 0, "buckets": {}}

    def charge(self, method: str) -> None:
        self._roll_day()
        cost = COSTS[method]
        if method in SEPARATE_BUCKETS:
            used = self.state["buckets"].get(method, 0)
            if used + 1 > SEPARATE_BUCKETS[method]:
                raise QuotaExceeded(f"{method} daily bucket exhausted")
            self.state["buckets"][method] = used + 1
        else:
            if self.state["units"] + cost > self.daily_units - self.safety_margin:
                raise QuotaExceeded(f"daily unit budget reached ({self.state['units']} used)")
            self.state["units"] += cost
        self.save()

    @property
    def units_used(self) -> int:
        return self.state.get("units", 0)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2))
