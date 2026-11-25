"""Pydantic schemas for GRID SIGNAL.

Three separate entities, as required by the research design:
  SourceRecord   - one video (or document) and where it came from
  TextRecord     - one comment; text is kept only while retention is authorized
  AnalysisRecord - model output for one TextRecord (a derived metric)

No author names, channel IDs of commenters, or profile fields are stored.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Platform = Literal["youtube"]
ChannelCategory = Literal[
    "official", "journalism", "analysis", "independent_commentary", "team_or_driver", "unassigned"
]

# YouTube Developer Policies III.E.4.d: non-authorized data at most 30 days.
TEXT_RETENTION_DAYS = 30


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceRecord(BaseModel):
    platform: Platform = "youtube"
    source_id: str = Field(description="Channel ID of the publisher (a public channel, not a commenter)")
    video_id: str
    channel_category: ChannelCategory
    title: Optional[str] = None  # API data: subject to the 30-day refresh rule
    published_at: datetime
    collected_at: datetime = Field(default_factory=utcnow)
    sampling_rule: str = Field(description="Which rule in sampling_frame.yaml selected this video")
    video_type: Optional[str] = None  # e.g. race_highlights, qualifying_reactions
    gp_key: Optional[str] = None      # normalized Grand Prix name, joins to the race calendar


class TextRecord(BaseModel):
    record_id: str = Field(description="YouTube comment ID")
    video_id: str
    parent_id: Optional[str] = None  # set for replies
    published_at: datetime
    updated_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=utcnow)
    language: Optional[str] = None
    text: Optional[str] = Field(default=None, description="None once retention window has passed")
    like_count: int = 0
    reply_count: int = 0
    text_hash: Optional[str] = Field(default=None, description="sha256 of normalized text, for dedup")

    @field_validator("published_at", "collected_at", "updated_at")
    @classmethod
    def _tz_aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware (UTC)")
        return v

    def retention_expired(self, now: Optional[datetime] = None) -> bool:
        now = now or utcnow()
        return now - self.collected_at > timedelta(days=TEXT_RETENTION_DAYS)


class AnalysisRecord(BaseModel):
    record_id: str
    model_id: str
    model_version: str
    inference_mode: Literal["lexicon", "classical_ml", "pretrained_zero_shot", "fine_tuned"]
    label: Literal["positive", "neutral", "negative"]
    probs: dict[str, float] = Field(default_factory=dict)
    target_entity: Optional[str] = None  # None = whole-comment sentiment
    created_at: datetime = Field(default_factory=utcnow)


# Fields that must never appear in any exported artifact.
FORBIDDEN_EXPORT_FIELDS = {
    "authorDisplayName", "authorChannelId", "authorProfileImageUrl",
    "authorChannelUrl", "author", "text", "textDisplay", "textOriginal",
}
