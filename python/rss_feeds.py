"""
RSS feed loader.
Источник истины — rss_feeds.json рядом с этим файлом.
Редактируй JSON, чтобы добавлять/убирать фиды без изменения кода.
"""

import json
from pathlib import Path

_FEEDS_PATH = Path(__file__).parent / "rss_feeds.json"

with _FEEDS_PATH.open(encoding="utf-8") as f:
    RSS_FEEDS = json.load(f)
