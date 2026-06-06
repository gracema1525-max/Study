from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class FeedItem:
    id: str
    title: str
    link: str
    published: datetime
    source: str
    summary: str = ""
    matched_keywords: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AISummary:
    title_cn: str
    bullets_cn: list[str]
    impact_cn: str
    companies: list[str]
    tags: list[str]
    raw_text: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
