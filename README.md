# Semiconductor News Collector

一个可运行的半导体资讯采集器：从 RSS 抓取新闻，筛选半导体关键词，调用 OpenAI 生成中文摘要，并把摘要写入 Notion 页面或数据库。

## 功能

- RSS 聚合：默认内置 SemiAnalysis、AnandTech、Tom's Hardware、EE Times、Semiconductor Engineering 等源。
- 关键词筛选：只处理命中半导体关键词的条目。
- 去重：用 SQLite 记录已发布条目，避免重复写入 Notion。
- AI 摘要：使用 OpenAI Responses API 生成中文标题、要点、产业影响、公司和标签。
- Notion 输出：支持写入父页面，或写入带 `Name`、`Source`、`URL`、`Published`、`Tags` 属性的数据库。
- 安全试跑：`--dry-run --no-ai` 不需要任何 API Key，可先验证 RSS 流程。

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp config.example.yaml config.yaml
cp .env.example .env
```

### 本地试跑（无需 API Key）

```bash
semi-news --dry-run --no-ai --limit 3
```

### 启用 AI 摘要

在 `.env` 中设置：

```bash
OPENAI_API_KEY=sk-...
```

然后运行：

```bash
semi-news --dry-run --limit 3
```

### 发布到 Notion

1. 在 Notion 创建 integration，并把目标页面或数据库分享给该 integration。
2. 在 `.env` 中设置 `NOTION_TOKEN`。
3. 在 `config.yaml` 的 `notion.parent_page_id` 或 `notion.database_id` 填入目标 ID；也可以用环境变量 `NOTION_PARENT_PAGE_ID` 或 `NOTION_DATABASE_ID`。
4. 如果使用数据库，建议创建以下属性：
   - `Name`：Title
   - `Source`：Text
   - `URL`：URL
   - `Published`：Date
   - `Tags`：Multi-select
5. 执行：

```bash
semi-news --limit 5
```

## 配置说明

`config.example.yaml` 包含全部可配置项：

- `feeds`：RSS URL 列表。
- `keywords`：大小写不敏感的关键词列表；命中标题、摘要或来源才会处理。
- `max_items_per_feed`：每个 RSS 源最多读取多少条。
- `database_path`：SQLite 去重数据库路径。
- `openai.model`：OpenAI 模型名。
- `notion.parent_page_id`：写入某个页面的子页面。
- `notion.database_id`：写入某个 Notion 数据库。

## 定时运行

Linux/macOS 可以用 cron 每天早上运行：

```cron
0 8 * * * cd /path/to/Study && /path/to/Study/.venv/bin/semi-news --limit 10 >> collector.log 2>&1
```

GitHub Actions 或其他 CI 中运行时，请把 `OPENAI_API_KEY`、`NOTION_TOKEN`、`NOTION_PARENT_PAGE_ID`/`NOTION_DATABASE_ID` 配成 secret。

## 开发与测试

```bash
pip install -e '.[dev]'
pytest
```
