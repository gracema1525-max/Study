from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .ai import summarize_item
from .config import load_config
from .notion import NotionClient, NotionTarget
from .rss import collect_all
from .store import SeenStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect semiconductor RSS news, summarize it, and publish to Notion.")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config file.")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads instead of writing to Notion or seen DB.")
    parser.add_argument("--no-ai", action="store_true", help="Use deterministic local summaries instead of OpenAI.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum new items to process in one run.")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    items = collect_all(config.feeds, config.keywords, max_items=config.max_items_per_feed)
    processed = 0

    notion: NotionClient | None = None
    if not args.dry_run:
        notion = NotionClient(
            NotionTarget(
                token=config.notion_token or "",
                version=config.notion_version,
                parent_page_id=config.notion_parent_page_id,
                database_id=config.notion_database_id,
            ),
            timeout_seconds=config.request_timeout_seconds,
        )

    with SeenStore(config.database_path) as store:
        for item in items:
            if processed >= args.limit:
                break
            if store.has_seen(item.id):
                continue
            summary = summarize_item(
                item,
                api_key=config.openai_api_key,
                model=config.openai_model,
                use_ai=not args.no_ai,
            )
            if args.dry_run:
                print(json.dumps({"item": asdict(item), "summary": asdict(summary)}, ensure_ascii=False, default=str, indent=2))
            else:
                assert notion is not None
                url = notion.create_page(item, summary)
                store.mark_seen(item.id, item.title, item.link)
                print(f"Published: {summary.title_cn} -> {url}")
            processed += 1

    print(f"Processed {processed} new item(s).", file=sys.stderr)
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
