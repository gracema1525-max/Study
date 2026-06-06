from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .models import AISummary, FeedItem


@dataclass(frozen=True)
class NotionTarget:
    token: str
    version: str = "2022-06-28"
    parent_page_id: str | None = None
    database_id: str | None = None

    def validate(self) -> None:
        if not self.token:
            raise ValueError("NOTION_TOKEN is required unless --dry-run is used")
        if not self.parent_page_id and not self.database_id:
            raise ValueError("Set NOTION_PARENT_PAGE_ID or notion.database_id in config.yaml")


class NotionClient:
    def __init__(self, target: NotionTarget, timeout_seconds: int = 20):
        target.validate()
        self.target = target
        self.timeout_seconds = timeout_seconds

    def create_page(self, item: FeedItem, summary: AISummary) -> str:
        payload = self._database_payload(item, summary) if self.target.database_id else self._page_payload(item, summary)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            "https://api.notion.com/v1/pages",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.target.token}",
                "Notion-Version": self.target.version,
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310 - Notion API endpoint is fixed.
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Notion API request failed: HTTP {exc.code} {detail}") from exc
        return str(data.get("url") or data.get("id"))

    def _parent(self) -> dict:
        if self.target.database_id:
            return {"database_id": self.target.database_id}
        return {"page_id": self.target.parent_page_id}

    def _blocks(self, item: FeedItem, summary: AISummary) -> list[dict]:
        children = [
            _paragraph(f"来源：{item.source}"),
            _paragraph(f"原文：{item.link}"),
            _heading("AI 摘要"),
        ]
        children.extend(_bulleted(bullet) for bullet in summary.bullets_cn)
        children.extend(
            [
                _heading("产业影响"),
                _paragraph(summary.impact_cn),
                _heading("标签 / 公司"),
                _paragraph("标签：" + "、".join(summary.tags)),
                _paragraph("公司：" + ("、".join(summary.companies) or "未识别")),
            ]
        )
        return children

    def _page_payload(self, item: FeedItem, summary: AISummary) -> dict:
        return {
            "parent": self._parent(),
            "properties": {"title": {"title": [{"text": {"content": summary.title_cn}}]}},
            "children": self._blocks(item, summary),
        }

    def _database_payload(self, item: FeedItem, summary: AISummary) -> dict:
        return {
            "parent": self._parent(),
            "properties": {
                "Name": {"title": [{"text": {"content": summary.title_cn}}]},
                "Source": {"rich_text": [{"text": {"content": item.source[:200]}}]},
                "URL": {"url": item.link or None},
                "Published": {"date": {"start": item.published.date().isoformat()}},
                "Tags": {"multi_select": [{"name": tag[:100]} for tag in summary.tags[:10]]},
            },
            "children": self._blocks(item, summary),
        }


def _text(content: str) -> list[dict]:
    return [{"type": "text", "text": {"content": content[:1900]}}]


def _paragraph(content: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _text(content)}}


def _heading(content: str) -> dict:
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": _text(content)}}


def _bulleted(content: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": _text(content)}}
