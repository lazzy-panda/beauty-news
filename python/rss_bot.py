"""
RSS News Bot
Fetches articles from RSS feeds, translates via OpenAI gpt-4o-mini,
and posts to the Telegram channel every 10 minutes with a photo.

Usage (via main.py):
  python main.py news
"""

import asyncio
import json
import logging
import random
from datetime import datetime, time as dtime, timedelta
from pathlib import Path

import httpx

import config
from rss_feeds import RSS_FEEDS
from rss_fetcher import find_article_with_image
from translator import translate_article
from wiki_linker import add_wiki_links

logger = logging.getLogger(__name__)

POSTED_URLS_FILE = Path(config.OUTPUT_DIR) / "rss_posted.json"
POST_INTERVAL = 110 * 60  # seconds — min gap between posts (~2h minus cron jitter)
TG_API = "https://api.telegram.org/bot{token}/{method}"
# Telegram caption limit is 1024 chars
CAPTION_LIMIT = 1024


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def _load_posted_data() -> dict:
    """Load {urls: [...], titles: [...], last_post_time: "ISO"} from disk."""
    if not POSTED_URLS_FILE.exists():
        return {"urls": [], "titles": []}
    try:
        raw = json.loads(POSTED_URLS_FILE.read_text(encoding="utf-8"))
        # Backwards compat: old format was a plain list of URLs
        if isinstance(raw, list):
            return {"urls": raw, "titles": []}
        return raw
    except Exception:
        return {"urls": [], "titles": []}


def load_posted_urls() -> set:
    return set(_load_posted_data()["urls"])


def _normalize_title(title: str) -> str:
    """Lowercase, strip punctuation and extra spaces for fuzzy matching."""
    import re
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def load_posted_titles() -> set:
    return {_normalize_title(t) for t in _load_posted_data()["titles"] if t}


def save_posted(url: str, title: str = "", update_time: bool = False) -> None:
    POSTED_URLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = _load_posted_data()
    if url not in data["urls"]:
        data["urls"].append(url)
    if title:
        norm = _normalize_title(title)
        if norm not in {_normalize_title(t) for t in data["titles"]}:
            data["titles"].append(title)
    if update_time:
        data["last_post_time"] = datetime.utcnow().isoformat()
    # keep last 3000 to avoid unbounded growth
    data["urls"] = data["urls"][-3000:]
    data["titles"] = data["titles"][-3000:]
    POSTED_URLS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _seconds_since_last_post() -> float | None:
    """Return seconds since the last successful post, or None if unknown."""
    data = _load_posted_data()
    ts = data.get("last_post_time")
    if not ts:
        return None
    try:
        last = datetime.fromisoformat(ts)
        return (datetime.utcnow() - last).total_seconds()
    except Exception:
        return None


def is_title_duplicate(title: str, posted_titles: set) -> bool:
    """Check if a title is too similar to an already posted one."""
    norm = _normalize_title(title)
    if not norm or len(norm) < 10:
        return False
    # Exact normalized match
    if norm in posted_titles:
        return True
    # Substring match (for titles ≥ 30 chars)
    for prev in posted_titles:
        if len(prev) >= 30 and (prev in norm or norm in prev):
            return True
    return False


# ---------------------------------------------------------------------------
# Caption builder
# ---------------------------------------------------------------------------

def format_russian_article(title: str, description: str) -> str:
    """
    Build a Telegram HTML post from a Russian-language RSS item
    without sending it to OpenAI. Title becomes bold; description
    is stripped of HTML and kept as plain text below.
    """
    import html
    import re

    def _strip(s: str) -> str:
        s = re.sub(r"<[^>]+>", "", s or "")
        s = html.unescape(s)
        return re.sub(r"\s+", " ", s).strip()

    clean_title = _strip(title)
    clean_desc = _strip(description)

    # Escape &, <, > in plain text for Telegram HTML parse mode
    def _esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    bold_title = f"<b>{_esc(clean_title)}</b>"
    if clean_desc and clean_desc != clean_title:
        return f"{bold_title}\n\n{_esc(clean_desc)}"
    return bold_title


def build_caption(text: str, url: str, hashtags: str) -> str:
    """
    Format:
        {translated text with HTML formatting}

        <a href="url">Читать далее →</a>

        #хэштеги
    """
    link_line = f'<a href="{url}">Читать далее →</a>'
    suffix = f"\n\n{link_line}\n\n{hashtags}"
    # text already contains Telegram HTML tags from the model — do not escape
    max_text = CAPTION_LIMIT - len(suffix)
    if len(text) > max_text:
        text = text[: max_text - 1] + "…"
    return text + suffix


# ---------------------------------------------------------------------------
# Telegram sender
# ---------------------------------------------------------------------------

async def send_photo(image_data: bytes, caption: str) -> bool:
    url = TG_API.format(token=config.TELEGRAM_BOT_TOKEN, method="sendPhoto")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                data={"chat_id": config.TELEGRAM_CHANNEL_ID, "caption": caption, "parse_mode": "HTML"},
                files={"photo": ("photo.jpg", image_data, "image/jpeg")},
            )
        if resp.status_code == 200 and resp.json().get("ok"):
            return True
        logger.error("Telegram error: %s", resp.text)
        return False
    except Exception as e:
        logger.error("Telegram exception: %s", e)
        return False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def _leading_tag(hashtags: str) -> str:
    """Return the first hashtag as a rough category key."""
    return hashtags.split()[0] if hashtags else ""


async def _post_one(posted_urls: set, posted_titles: set, recent_tags: list) -> bool:
    """Try each feed (shuffled) until we post one article. Returns True on success.

    Feeds whose leading hashtag matches one of the last 3 posted categories
    are moved to the end so topics naturally alternate.
    """
    feeds = RSS_FEEDS.copy()
    random.shuffle(feeds)

    # Deprioritise recently-used categories
    recent = set(recent_tags[-3:])
    feeds.sort(key=lambda f: 1 if _leading_tag(f["hashtags"]) in recent else 0)

    for feed in feeds:
        article = await find_article_with_image(feed, posted_urls)
        if not article:
            continue

        # Skip if title too similar to an already-posted article
        if is_title_duplicate(article["title"], posted_titles):
            logger.info("Skipped duplicate title: %s", article["title"])
            posted_urls.add(article["url"])
            save_posted(article["url"])
            continue

        try:
            if feed.get("lang") == "ru":
                # Russian-language feed: skip OpenAI translation, format locally.
                text = format_russian_article(article["title"], article["description"])
            else:
                text = await translate_article(article["title"], article["description"])
                text = await add_wiki_links(text)
            caption = build_caption(text, article["url"], article["hashtags"])
            ok = await send_photo(article["image_data"], caption)
            # Always mark as seen to avoid infinite retry on bad images
            posted_urls.add(article["url"])
            posted_titles.add(_normalize_title(article["title"]))
            save_posted(article["url"], article["title"], update_time=ok)
            if ok:
                logger.info("Posted: %s", article["title"])
                recent_tags.append(_leading_tag(feed["hashtags"]))
                return True
            logger.warning("Skipped (Telegram rejected): %s", article["title"])
        except Exception as e:
            logger.error("Error posting %s: %s", article.get("url"), e)

    logger.warning("No new articles with images found across all feeds.")
    return False


def _parse_time(t: str) -> dtime:
    h, m = t.split(":")
    return dtime(int(h), int(m))


def _quiet_sleep_seconds() -> float | None:
    """Return seconds to sleep if we're in quiet hours, else None."""
    now = datetime.now()
    quiet_start = _parse_time(config.QUIET_START)
    quiet_end   = _parse_time(config.QUIET_END)

    current = now.time().replace(second=0, microsecond=0)

    # Quiet window spans midnight (e.g. 22:00 – 08:00)
    in_quiet = (
        current >= quiet_start or current < quiet_end
        if quiet_start > quiet_end
        else quiet_start <= current < quiet_end
    )

    if not in_quiet:
        return None

    # Sleep until quiet_end today or tomorrow
    resume = datetime.combine(now.date(), quiet_end)
    if resume <= now:
        resume += timedelta(days=1)
    return (resume - now).total_seconds()


async def post_once() -> bool:
    """Post a single news item and exit. For use with GitHub Actions cron."""
    # Enforce minimum interval between posts (GitHub Actions cron is imprecise)
    elapsed = _seconds_since_last_post()
    if elapsed is not None and elapsed < POST_INTERVAL:
        logger.info(
            "news-once: only %d sec since last post (min %d). Skipping.",
            int(elapsed), POST_INTERVAL,
        )
        return False

    posted_urls = load_posted_urls()
    posted_titles = load_posted_titles()
    recent_tags: list = []
    ok = await _post_one(posted_urls, posted_titles, recent_tags)
    if ok:
        logger.info("news-once: posted successfully.")
    else:
        logger.warning("news-once: no article posted.")
    return ok


async def run_news_bot() -> None:
    """Infinite loop: post one news item every 5 minutes (paused during quiet hours)."""
    logger.info("RSS News Bot started. Posting every %d minutes.", POST_INTERVAL // 60)
    logger.info("Quiet hours: %s – %s", config.QUIET_START, config.QUIET_END)
    posted_urls = load_posted_urls()
    posted_titles = load_posted_titles()
    recent_tags: list = []

    while True:
        sleep_sec = _quiet_sleep_seconds()
        if sleep_sec is not None:
            logger.info(
                "Quiet hours — pausing until %s.",
                config.QUIET_END,
            )
            # Sleep in short intervals to survive macOS sleep/wake
            while _quiet_sleep_seconds() is not None:
                await asyncio.sleep(30)
            logger.info("Quiet hours ended, resuming.")
            continue

        try:
            await _post_one(posted_urls, posted_titles, recent_tags)
        except Exception as e:
            logger.error("Unexpected bot error: %s", e)
        await asyncio.sleep(POST_INTERVAL)
