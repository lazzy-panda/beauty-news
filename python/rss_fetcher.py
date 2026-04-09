"""
Fetches RSS feeds, extracts articles with images.
Image extraction order:
  1. media:content / media:thumbnail from RSS entry
  2. enclosure tag
  3. <img> in HTML summary
  4. og:image / twitter:image from article page (fallback)
"""

import asyncio
import logging
import re
from html import unescape

import feedparser
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; BeautyNewsBot/1.0)"
# Skip obvious tracking pixels / tiny placeholder images
_SKIP_IMAGE_PATTERNS = ("1x1", "pixel", "tracking", "analytics", "spacer", "blank", "logo", "avatar")


def _extract_image_from_entry(entry) -> str | None:
    """Try to get an image URL from RSS entry metadata."""

    # media:content
    for m in getattr(entry, "media_content", []):
        url = m.get("url", "")
        if url and not _is_junk_image(url):
            return url

    # media:thumbnail
    for t in getattr(entry, "media_thumbnail", []):
        url = t.get("url", "")
        if url and not _is_junk_image(url):
            return url

    # enclosures
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            url = enc.get("url", "")
            if url and not _is_junk_image(url):
                return url

    # First <img> in HTML content
    html = ""
    if hasattr(entry, "content") and entry.content:
        html = entry.content[0].get("value", "")
    if not html and hasattr(entry, "summary"):
        html = entry.summary or ""

    if html:
        m = re.search(r'<img[^>]+src=["\']([^"\']{20,})["\']', html)
        if m:
            url = m.group(1)
            if not _is_junk_image(url):
                return url

    return None


def _is_junk_image(url: str) -> bool:
    low = url.lower()
    return any(p in low for p in _SKIP_IMAGE_PATTERNS)


async def _fetch_og_image(article_url: str) -> str | None:
    """Fetch article page and extract og:image or twitter:image."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(article_url, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
            for attrs in [
                {"property": "og:image"},
                {"name": "og:image"},
                {"name": "twitter:image"},
                {"property": "twitter:image"},
            ]:
                tag = soup.find("meta", attrs=attrs)
                if tag and tag.get("content") and not _is_junk_image(tag["content"]):
                    return tag["content"]
    except Exception as e:
        logger.debug("og:image fetch failed for %s: %s", article_url, e)
    return None


async def download_image(url: str) -> bytes | None:
    """Download image and return bytes, or None if invalid/too small."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                return None
            ctype = resp.headers.get("content-type", "")
            if "image" not in ctype and "octet-stream" not in ctype:
                return None
            data = resp.content
            if len(data) < 5_000:  # skip images < 5 KB (likely placeholders)
                return None
            return data
    except Exception as e:
        logger.debug("Image download failed for %s: %s", url, e)
    return None


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


async def parse_feed(feed_config: dict) -> list[dict]:
    """Parse RSS feed URL, return list of article dicts."""
    loop = asyncio.get_event_loop()
    try:
        parsed = await asyncio.wait_for(
            loop.run_in_executor(None, feedparser.parse, feed_config["url"]),
            timeout=30,
        )
    except asyncio.TimeoutError:
        logger.warning("Feed parse timeout (%s)", feed_config["url"])
        return []
    except Exception as e:
        logger.warning("Feed parse failed (%s): %s", feed_config["url"], e)
        return []

    articles = []
    for entry in parsed.entries[:20]:
        url = entry.get("link", "")
        if not url:
            continue
        title = _strip_html(entry.get("title", ""))
        summary = _strip_html(
            entry.get("summary", "") or entry.get("description", "")
        )
        image_url = _extract_image_from_entry(entry)
        articles.append({
            "url": url,
            "title": title,
            "description": summary[:600],
            "image_url": image_url,
            "hashtags": feed_config["hashtags"],
        })
    return articles


async def find_article_with_image(feed_config: dict, posted_urls: set) -> dict | None:
    """
    Returns the first unposted article from the feed that has a downloadable image.
    image_data (bytes) is added to the returned dict.
    """
    articles = await parse_feed(feed_config)

    for article in articles:
        if article["url"] in posted_urls:
            continue
        if not article["title"]:
            continue

        image_url = article["image_url"]

        # Fallback: scrape og:image from the article page
        if not image_url:
            image_url = await _fetch_og_image(article["url"])

        if not image_url:
            continue

        image_data = await download_image(image_url)
        if not image_data:
            continue

        article["image_data"] = image_data
        return article

    return None
