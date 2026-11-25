"""Offline tests: no network, no API key needed."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from pipelines import collect, export, retention
from pipelines.events import RateLimiter, races_to_frame
from pipelines.preprocess import dedup_key, normalize_for_model
from pipelines.quota import QuotaExceeded, QuotaTracker
from pipelines.schemas import TextRecord
from pipelines.youtube_client import YouTubeClient, YouTubeError

UTC = timezone.utc


# ---------- fakes --------------------------------------------------------
class FakeResp:
    def __init__(self, status, payload):
        self.status_code, self._p, self.text = status, payload, str(payload)

    def json(self):
        return self._p


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return self.responses.pop(0)


def err(status, reason):
    return FakeResp(status, {"error": {"message": reason, "errors": [{"reason": reason}]}})


def thread(cid, text, ts="2025-03-16T07:00:00Z", vid="v1"):
    return {"snippet": {"videoId": vid, "totalReplyCount": 0, "topLevelComment": {"id": cid, "snippet": {
        "videoId": vid, "textOriginal": text, "publishedAt": ts, "likeCount": 3,
        "authorDisplayName": "SHOULD_NOT_SURVIVE", "authorChannelId": {"value": "UCxxx"}}}}}


@pytest.fixture
def quota(tmp_path):
    return QuotaTracker(tmp_path / "q.json")


def client(quota, responses):
    return YouTubeClient(quota, api_key="TEST", session=FakeSession(responses), sleep=lambda s: None)


# ---------- API handling -------------------------------------------------
def test_pagination_follows_tokens_and_charges_quota(quota):
    yt = client(quota, [
        FakeResp(200, {"items": [thread("a", "x")], "nextPageToken": "p2"}),
        FakeResp(200, {"items": [thread("b", "y")]}),
    ])
    items = list(yt.comment_threads("v1"))
    assert [i["snippet"]["topLevelComment"]["id"] for i in items] == ["a", "b"]
    assert quota.units_used == 2
    assert yt.session.calls[1][1]["pageToken"] == "p2"
    assert yt.session.calls[0][1]["order"] == "time"


def test_retry_with_backoff_then_success(quota):
    yt = client(quota, [err(503, "backendError"), err(429, "rateLimitExceeded"),
                        FakeResp(200, {"items": []})])
    assert list(yt.comment_threads("v1")) == []
    assert quota.units_used == 3  # failed calls still cost quota


def test_comments_disabled_not_retried(quota):
    yt = client(quota, [err(403, "commentsDisabled")])
    with pytest.raises(YouTubeError) as e:
        list(yt.comment_threads("v1"))
    assert e.value.reason == "commentsDisabled" and quota.units_used == 1


def test_quota_budget_stops_collection(tmp_path):
    q = QuotaTracker(tmp_path / "q.json", daily_units=3, safety_margin=1)
    q.charge("videos.list"); q.charge("videos.list")
    with pytest.raises(QuotaExceeded):
        q.charge("videos.list")


def test_search_has_separate_bucket(quota):
    for _ in range(100):
        quota.charge("search.list")
    assert quota.units_used == 0
    with pytest.raises(QuotaExceeded):
        quota.charge("search.list")


def test_missing_key_raises(quota, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        YouTubeClient(quota)


# ---------- parsing / privacy -------------------------------------------
def test_parse_thread_drops_author_fields():
    recs = collect.parse_thread(thread("c1", "Great drive from Leclerc"))
    d = recs[0].model_dump()
    assert "SHOULD_NOT_SURVIVE" not in str(d) and "UCxxx" not in str(d)
    assert d["record_id"] == "c1" and d["published_at"].tzinfo is not None


def test_naive_timestamp_rejected():
    with pytest.raises(ValueError):
        TextRecord(record_id="x", video_id="v", published_at=datetime(2025, 1, 1))


def _up(vid, title, ts="2025-03-16T10:00:00Z"):
    return {"snippet": {"title": title, "publishedAt": ts},
            "contentDetails": {"videoId": vid, "videoPublishedAt": ts}}



def _types():
    import yaml
    from pathlib import Path
    f = yaml.safe_load(Path("data/manifests/sampling_frame.yaml").read_text())
    return collect.compile_types(f)


def test_select_videos_uses_fixed_formats_only():
    ups = [
        _up("race", "Race Highlights | 2025 Australian Grand Prix"),
        _up("qrx", "Driver Reactions After Qualifying | 2025 Emilia-Romagna Grand Prix"),
        _up("rrx", "Drivers React To The Race | 2025 Sao Paulo Grand Prix"),
        _up("spr", "F1 Sprint Highlights | 2025 Chinese Grand Prix"),
        _up("f2", "F2 Sprint Race Highlights | 2025 Australian Grand Prix"),
        _up("hist", "Extended Race Highlights | 2008 Australian Grand Prix"),
        _up("pen", "Max Verstappen's 10-Second Penalty For George Russell Collision | 2025 Spanish Grand Prix"),
        _up("short", "F1's Hottest Race Ever! 😱"),
        _up("old", "Race Highlights | 2025 Australian Grand Prix", ts="2024-03-16T10:00:00Z"),
    ]
    sel = collect.select_videos(ups, datetime(2025, 1, 1, tzinfo=UTC),
                                datetime(2025, 12, 31, tzinfo=UTC), _types())
    got = {v["video_id"]: v["video_type"] for v in sel}
    assert got == {"race": "race_highlights", "qrx": "qualifying_reactions",
                   "rrx": "race_reactions", "spr": "sprint_highlights"}


def test_gp_key_matches_calendar_names():
    # YouTube titles vs Jolpica race names
    assert collect.gp_key("Sao Paulo Grand Prix") == collect.gp_key("São Paulo Grand Prix")
    assert collect.gp_key("Emilia-Romagna Grand Prix") == collect.gp_key("Emilia Romagna Grand Prix")


# ---------- dedup / preprocessing ---------------------------------------
def test_near_duplicates_share_key():
    assert dedup_key("Box box! https://x.co/a") == dedup_key("box BOX")
    assert dedup_key("Box box") != dedup_key("Stay out")


def test_model_text_keeps_case_and_emoji():
    s = normalize_for_model("NOT  great 🙄  https://a.b")
    assert s == "NOT great 🙄 <url>"


# ---------- retention ---------------------------------------------------
def _texts(now):
    return pd.DataFrame([
        {"record_id": "old", "video_id": "v", "published_at": now, "text": "a",
         "collected_at": now - timedelta(days=31), "like_count": 0, "text_hash": "h"},
        {"record_id": "new", "video_id": "v", "published_at": now, "text": "b",
         "collected_at": now - timedelta(days=2), "like_count": 0, "text_hash": "h"},
    ])


def test_purge_removes_only_expired_text():
    now = datetime(2025, 6, 1, tzinfo=UTC)
    out, n = retention.purge(_texts(now), now)
    assert n == 1
    assert pd.isna(out.set_index("record_id").loc["old", "text"])
    assert out.set_index("record_id").loc["new", "text"] == "b"


def test_refresh_detects_deletions_and_resets_clock():
    now = datetime(2025, 6, 1, tzinfo=UTC)
    fetched = [{"id": "new", "snippet": {"textOriginal": "edited", "likeCount": 9}}]
    kept, deleted = retention.apply_refresh(_texts(now), fetched, now)
    assert list(deleted["record_id"]) == ["old"]
    assert kept.loc[0, "text"] == "edited" and kept.loc[0, "collected_at"] == now


# ---------- export ------------------------------------------------------
def test_export_blocks_text_and_small_cells(tmp_path):
    now = datetime(2025, 6, 1, tzinfo=UTC)
    texts = pd.DataFrame({"record_id": [f"r{i}" for i in range(13)],
                          "video_id": ["big"] * 11 + ["small"] * 2, "published_at": [now] * 13})
    analysis = pd.DataFrame({"record_id": texts["record_id"],
                             "label": ["positive"] * 6 + ["negative"] * 5 + ["neutral"] * 2})
    out = export.sentiment_by_group(analysis, texts, ["video_id"])
    assert list(out["video_id"]) == ["big"]  # 'small' (n=2) suppressed
    assert out.loc[0, "share_positive"] == pytest.approx(6 / 11)
    with pytest.raises(export.UnsafeExport):
        export.write_artifact(pd.DataFrame({"text": ["leak"]}), tmp_path / "x.json", {})


# ---------- events ------------------------------------------------------
def test_races_to_frame_parses_utc_and_flags_missing_time():
    payload = {"MRData": {"RaceTable": {"Races": [
        {"season": "2025", "round": "1", "raceName": "Australian Grand Prix", "date": "2025-03-16",
         "time": "04:00:00Z", "Circuit": {"circuitId": "albert_park"}},
        {"season": "1950", "round": "1", "raceName": "British Grand Prix", "date": "1950-05-13",
         "Circuit": {"circuitId": "silverstone"}}]}}}
    df = races_to_frame(payload)
    assert str(df.loc[0, "race_start_utc"]) == "2025-03-16 04:00:00+00:00"
    assert bool(df.loc[1, "start_time_known"]) is False


def test_rate_limiter_sleeps_on_burst():
    t = [0.0]
    slept = []
    rl = RateLimiter(per_second=2, per_hour=100, clock=lambda: t[0], sleep=lambda s: slept.append(s))
    rl.wait(); rl.wait(); rl.wait()
    assert slept and slept[0] > 0
