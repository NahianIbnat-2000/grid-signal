"""Minimal YouTube Data API v3 client.

Uses plain HTTPS (a documented HTTP interface) so every request can be
quota-charged, retried and unit-tested. The API key is read from the
environment only; it is never written to disk or logged.
"""
from __future__ import annotations

import logging
import os
import random
import time
from typing import Callable, Iterator, Optional

import requests

from .quota import QuotaTracker

log = logging.getLogger(__name__)
BASE = "https://www.googleapis.com/youtube/v3"
RETRY_STATUS = {429, 500, 502, 503, 504}


class YouTubeError(RuntimeError):
    def __init__(self, status: int, reason: str, message: str):
        super().__init__(f"{status} {reason}: {message}")
        self.status, self.reason = status, reason


class YouTubeClient:
    def __init__(
        self,
        quota: QuotaTracker,
        api_key: Optional[str] = None,
        session: Optional[requests.Session] = None,
        max_retries: int = 5,
        base_delay: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            raise RuntimeError("Set YOUTUBE_API_KEY in your environment (see .env.example)")
        self.quota = quota
        self.session = session or requests.Session()
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.sleep = sleep

    # ---- core request with retry + exponential backoff -------------------
    def _get(self, method: str, params: dict) -> dict:
        resource, _ = method.split(".")
        url = f"{BASE}/{resource}"
        for attempt in range(self.max_retries + 1):
            self.quota.charge(method)  # every request costs quota, even failures
            resp = self.session.get(url, params={**params, "key": self.api_key}, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            reason, message = _error_reason(resp)
            # Comments disabled / video gone are expected, not retryable.
            if resp.status_code in (403, 404) and reason in {
                "commentsDisabled", "videoNotFound", "channelNotFound", "playlistNotFound",
            }:
                raise YouTubeError(resp.status_code, reason, message)
            if reason in {"quotaExceeded", "dailyLimitExceeded"}:
                raise YouTubeError(resp.status_code, reason, message)
            if resp.status_code in RETRY_STATUS or reason in {
                "rateLimitExceeded", "userRateLimitExceeded", "processingFailure", "backendError"}:
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    log.warning("retry %s in %.1fs (%s)", method, delay, reason)
                    self.sleep(delay)
                    continue
            raise YouTubeError(resp.status_code, reason, message)
        raise RuntimeError("unreachable")

    def _paginate(self, method: str, params: dict, max_pages: Optional[int] = None) -> Iterator[dict]:
        token, pages = None, 0
        while True:
            p = dict(params)
            if token:
                p["pageToken"] = token
            data = self._get(method, p)
            yield from data.get("items", [])
            pages += 1
            token = data.get("nextPageToken")
            if not token or (max_pages and pages >= max_pages):
                return

    # ---- endpoints used by the sampling design ---------------------------
    def channel_by_handle(self, handle: str) -> dict:
        data = self._get("channels.list", {"part": "id,snippet,contentDetails", "forHandle": handle})
        items = data.get("items", [])
        if not items:
            raise YouTubeError(404, "channelNotFound", handle)
        return items[0]

    def uploads(self, uploads_playlist_id: str, max_pages: Optional[int] = None) -> Iterator[dict]:
        """List a channel's uploads (1 unit/page) instead of search.list (100/day cap)."""
        yield from self._paginate(
            "playlistItems.list",
            {"part": "snippet,contentDetails", "playlistId": uploads_playlist_id, "maxResults": 50},
            max_pages,
        )

    def videos(self, ids: list[str]) -> list[dict]:
        out = []
        for i in range(0, len(ids), 50):
            data = self._get("videos.list", {"part": "snippet,statistics", "id": ",".join(ids[i:i + 50])})
            out.extend(data.get("items", []))
        return out

    def comment_threads(self, video_id: str, max_pages: Optional[int] = None) -> Iterator[dict]:
        """Top-level comments in time order (not 'relevance', which is ranked by YouTube)."""
        yield from self._paginate(
            "commentThreads.list",
            {"part": "snippet", "videoId": video_id, "maxResults": 100,
             "order": "time", "textFormat": "plainText"},
            max_pages,
        )

    def comments_by_id(self, ids: list[str]) -> list[dict]:
        """Used by the 30-day refresh to detect deleted comments."""
        out = []
        for i in range(0, len(ids), 50):
            data = self._get("comments.list", {"part": "snippet", "id": ",".join(ids[i:i + 50]),
                                               "textFormat": "plainText"})
            out.extend(data.get("items", []))
        return out


def _error_reason(resp: requests.Response) -> tuple[str, str]:
    try:
        err = resp.json().get("error", {})
        errs = err.get("errors") or [{}]
        return errs[0].get("reason", "unknown"), err.get("message", "")
    except ValueError:
        return "unknown", resp.text[:200]
