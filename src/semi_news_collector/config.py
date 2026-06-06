from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os

try:
    import yaml  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


DEFAULT_KEYWORDS = [
    "semiconductor",
    "chip",
    "foundry",
    "AI accelerator",
    "EUV",
    "HBM",
    "memory",
    "TSMC",
    "Samsung",
    "Intel",
    "Nvidia",
    "AMD",
    "ASML",
    "EDA",
    "wafer",
]

DEFAULT_FEEDS = [
    "https://www.semianalysis.com/feed",
    "https://www.anandtech.com/rss/",
    "https://www.tomshardware.com/feeds/all",
    "https://www.eetimes.com/feed/",
    "https://semiengineering.com/feed/",
    "https://www.digitimes.com/rss/supply_chain.xml",
]


@dataclass(frozen=True)
class AppConfig:
    feeds: list[str] = field(default_factory=lambda: list(DEFAULT_FEEDS))
    keywords: list[str] = field(default_factory=lambda: list(DEFAULT_KEYWORDS))
    max_items_per_feed: int = 8
    database_path: str = "data/seen.sqlite3"
    openai_model: str = "gpt-5.4-mini"
    notion_version: str = "2022-06-28"
    notion_parent_page_id: str | None = None
    notion_database_id: str | None = None
    request_timeout_seconds: int = 20

    @property
    def openai_api_key(self) -> str | None:
        return os.getenv("OPENAI_API_KEY")

    @property
    def notion_token(self) -> str | None:
        return os.getenv("NOTION_TOKEN")


def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _minimal_yaml(text: str) -> dict[str, Any]:
    """Parse the simple config.example.yaml shape when PyYAML is unavailable."""
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_map: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current_key = line[:-1].strip()
            result[current_key] = [] if current_key in {"feeds", "keywords"} else {}
            current_map = result[current_key] if isinstance(result[current_key], dict) else None
            continue
        if line.startswith("  - ") and current_key:
            result.setdefault(current_key, []).append(line[4:].strip().strip('"'))
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = _coerce_scalar(value.strip())
            current_key = None
            current_map = None
            continue
        if current_map is not None and ":" in line:
            key, value = line.strip().split(":", 1)
            current_map[key.strip()] = _coerce_scalar(value.strip())
    return result


def _coerce_scalar(value: str) -> Any:
    cleaned = value.strip().strip('"').strip("'")
    if cleaned == "":
        return ""
    if cleaned.isdigit():
        return int(cleaned)
    return cleaned


def _read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text) or {}
    else:
        loaded = _minimal_yaml(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return loaded


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    _load_dotenv()
    raw = _read_config(Path(config_path))

    notion = raw.get("notion") or {}
    openai = raw.get("openai") or {}
    if notion and not isinstance(notion, dict):
        raise ValueError("config.notion must be a mapping")
    if openai and not isinstance(openai, dict):
        raise ValueError("config.openai must be a mapping")

    return AppConfig(
        feeds=list(raw.get("feeds") or DEFAULT_FEEDS),
        keywords=list(raw.get("keywords") or DEFAULT_KEYWORDS),
        max_items_per_feed=int(raw.get("max_items_per_feed", 8)),
        database_path=str(raw.get("database_path", "data/seen.sqlite3")),
        openai_model=str(openai.get("model", "gpt-5.4-mini")),
        notion_version=str(notion.get("version", "2022-06-28")),
        notion_parent_page_id=notion.get("parent_page_id") or os.getenv("NOTION_PARENT_PAGE_ID"),
        notion_database_id=notion.get("database_id") or os.getenv("NOTION_DATABASE_ID"),
        request_timeout_seconds=int(raw.get("request_timeout_seconds", 20)),
    )
