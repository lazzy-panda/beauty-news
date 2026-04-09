"""
Configuration for the NotebookLM Deep Research automation.
Edit this file to customize categories, schedule time, and output settings.
"""

import os
from pathlib import Path

# --- Research Settings ---

RESEARCH_PROMPT = """Проведи глубокое исследование и найди самые свежие новости за последние 24 часа. \
Обязательно покрой ВСЕ перечисленные разделы — ни один пропускать нельзя:

РАЗДЕЛ 1 — beauty and fashion: новости индустрии, громкие запуски, события, рекламные кампании, коллаборации.
РАЗДЕЛ 2 — beauty и fashion в России: рекламные запуски, коллаборации, рекламные кампании, мероприятия. Конкретные примеры и ссылки.
РАЗДЕЛ 3 — PR кейсы в beauty и fashion в России и в мире.
РАЗДЕЛ 4 — новые технологии в маркетинге, сбор и аналитика данных, таргетинг, поиск клиентов, GEO оптимизация для AI.
РАЗДЕЛ 5 — influencer marketing: свежие кейсы, статистика по размещениям, оптимизация рекламных кампаний, подборка блогеров.
РАЗДЕЛ 6 — креаторы и фабрики креаторов: компании, которые запускают фабрики креаторов, кейсы, результаты.
РАЗДЕЛ 7 — Стратегия: маркетинговые стратегии beauty и fashion брендов, особенности выстраивания коммуникации, использование новых и инновационных технологий.

Для каждого раздела:
- 2–3 конкретные новости с названиями, цифрами, ссылками
- Почему это важно и интересно

В конце: краткое резюме из 12 пунктов — по одному на самую важную новость."""

RESEARCH_MODE = "deep"   # "fast" or "deep"
RESEARCH_SOURCE = "web"  # "web" or "drive"

# --- Audio Settings ---
# AudioFormat: DEEP_DIVE, BRIEF, CRITIQUE, DEBATE
AUDIO_FORMAT = "DEEP_DIVE"
# AudioLength: SHORT, DEFAULT, LONG
AUDIO_LENGTH = "DEFAULT"
AUDIO_LANGUAGE = "ru"
AUDIO_INSTRUCTIONS = "Говорите живо и увлекательно, выделяйте самые неожиданные и важные находки."

# --- Video Settings ---
GENERATE_VIDEO = False  # отключено — генерируется слишком долго
# VideoFormat: EXPLAINER, BRIEF
VIDEO_FORMAT = "EXPLAINER"
# VideoStyle: AUTO_SELECT, CLASSIC, WHITEBOARD, KAWAII, ANIME, WATERCOLOR, RETRO_PRINT, HERITAGE, PAPER_CRAFT
VIDEO_STYLE = "AUTO_SELECT"
VIDEO_LANGUAGE = "ru"

# --- OpenAI Settings ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# --- Telegram Settings ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")

# --- Schedule Settings ---
# Time to run every morning (24-hour format)
SCHEDULE_TIME = "07:00"

# --- Quiet Hours (news feed paused) ---
QUIET_START = "21:00"  # stop posting at this time
QUIET_END   = "07:00"  # resume posting at this time

# --- Output Settings ---
OUTPUT_DIR = Path(__file__).parent / "output"

# How long to wait for research completion (seconds)
RESEARCH_TIMEOUT = 20 * 60  # 20 minutes

# How long to wait for audio/video generation (seconds)
GENERATION_TIMEOUT = 60 * 60  # 60 minutes
