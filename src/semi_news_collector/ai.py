from __future__ import annotations

import json
import re
from html import unescape

from .models import AISummary, FeedItem


_PROMPT = """你是半导体产业分析师。请用中文总结这条新闻，输出严格 JSON：
{
  "title_cn": "不超过35字的中文标题",
  "bullets_cn": ["3条要点，每条不超过45字"],
  "impact_cn": "一句话说明对半导体产业链/公司/投资观察的影响",
  "companies": ["相关公司或机构"],
  "tags": ["2到5个中文标签"]
}
不要输出 Markdown，不要编造原文不存在的事实。"""


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _fallback_summary(item: FeedItem) -> AISummary:
    summary = _strip_html(item.summary)
    first_sentence = re.split(r"(?<=[。.!?？])\s+", summary)[0] if summary else item.title
    bullets = [item.title]
    if first_sentence and first_sentence != item.title:
        bullets.append(first_sentence[:90])
    if item.matched_keywords:
        bullets.append("关键词：" + "、".join(item.matched_keywords[:6]))
    return AISummary(
        title_cn=item.title[:35],
        bullets_cn=bullets[:3],
        impact_cn="未配置 OpenAI API Key，已生成规则摘要；建议人工复核产业影响。",
        companies=[],
        tags=list(item.matched_keywords[:5]) or ["半导体"],
        raw_text="\n".join(bullets),
    )


def summarize_item(item: FeedItem, api_key: str | None, model: str, use_ai: bool = True) -> AISummary:
    if not use_ai or not api_key:
        return _fallback_summary(item)

    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install the openai package or run with --no-ai") from exc

    client = OpenAI(api_key=api_key)
    source_text = f"标题：{item.title}\n来源：{item.source}\n发布时间：{item.published.isoformat()}\n链接：{item.link}\n摘要：{_strip_html(item.summary)}"
    response = client.responses.create(
        model=model,
        input=[
            {"role": "developer", "content": _PROMPT},
            {"role": "user", "content": source_text},
        ],
        text={"format": {"type": "json_object"}},
    )
    raw = response.output_text
    data = json.loads(raw)
    return AISummary(
        title_cn=str(data.get("title_cn") or item.title)[:80],
        bullets_cn=[str(value) for value in data.get("bullets_cn", [])][:5] or [item.title],
        impact_cn=str(data.get("impact_cn") or "请人工复核产业影响。"),
        companies=[str(value) for value in data.get("companies", [])][:8],
        tags=[str(value) for value in data.get("tags", [])][:8] or list(item.matched_keywords[:5]),
        raw_text=raw,
    )
