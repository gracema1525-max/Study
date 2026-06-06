from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from typing import Iterable
from urllib.request import urlopen
from xml.etree import ElementTree

try:
    import feedparser  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - exercised when optional dependency is absent
    feedparser = None

from .models import FeedItem, utc_now


def _parse_datetime(entry: dict) -> datetime:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
    return utc_now()


def _entry_id(entry: dict, link: str, title: str) -> str:
    stable = entry.get("id") or entry.get("guid") or link or title
    return sha256(stable.encode("utf-8")).hexdigest()


def _matches(text: str, keywords: Iterable[str]) -> tuple[str, ...]:
    lowered = text.lower()
    return tuple(keyword for keyword in keywords if keyword.lower() in lowered)


def _node_text(node: ElementTree.Element, path: str) -> str:
    found = node.find(path)
    return "" if found is None or found.text is None else found.text.strip()


def _parse_with_stdlib(feed_url: str) -> tuple[str, list[dict]]:
    with urlopen(feed_url, timeout=20) as response:  # nosec B310 - user-configured RSS URLs are expected input.
        root = ElementTree.fromstring(response.read())
    channel = root.find("channel") if root.tag.lower().endswith("rss") else root
    if channel is None:
        channel = root
    source = _node_text(channel, "title") or feed_url
    entries: list[dict] = []
    for item in channel.findall("item"):
        entries.append(
            {
                "title": _node_text(item, "title"),
                "link": _node_text(item, "link"),
                "summary": _node_text(item, "description"),
                "published": _node_text(item, "pubDate"),
                "guid": _node_text(item, "guid"),
            }
        )
    return source, entries


def _load_feed(feed_url: str) -> tuple[str, list[dict]]:
    if feedparser is not None:
        parsed = feedparser.parse(feed_url)
        return parsed.feed.get("title") or feed_url, list(parsed.entries)
    return _parse_with_stdlib(feed_url)


def collect_feed(feed_url: str, keywords: Iterable[str], max_items: int = 8) -> list[FeedItem]:
    source, entries = _load_feed(feed_url)
    items: list[FeedItem] = []
    for entry in entries[:max_items]:
        title = entry.get("title", "Untitled").strip()
        link = entry.get("link", "").strip()
        summary = (entry.get("summary") or entry.get("description") or "").strip()
        haystack = "\n".join([title, summary, source])
        matched = _matches(haystack, keywords)
        if keywords and not matched:
            continue
        items.append(
            FeedItem(
                id=_entry_id(entry, link, title),
                title=title,
                link=link,
                published=_parse_datetime(entry),
                source=source,
                summary=summary,
                matched_keywords=matched,
            )
        )
    return items


def collect_all(feeds: Iterable[str], keywords: Iterable[str], max_items: int = 8) -> list[FeedItem]:
    all_items: list[FeedItem] = []
    for feed in feeds:
        all_items.extend(collect_feed(feed, keywords, max_items=max_items))
    return sorted(all_items, key=lambda item: item.published, reverse=True)
