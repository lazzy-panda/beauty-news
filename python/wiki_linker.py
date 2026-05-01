"""
Finds proper nouns in <i> tags of translated text,
checks Wikipedia (RU first, EN fallback), and wraps them
with <a href> links if an article exists.
"""

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# Only check Wikipedia for terms longer than this
MIN_NOUN_LEN = 3
# Max nouns to look up per post (avoid over-linking)
MAX_NOUNS = 6
# Seconds to wait between Wikipedia requests (be polite)
REQUEST_TIMEOUT = 5


def _noun_variants(noun: str) -> list[str]:
    """Generate dash/hyphen/em-dash variants for a multi-word noun.

    "Цермело-Френкеля" → ["Цермело-Френкеля", "Цермело—Френкеля",
                          "Цермело–Френкеля", "Цермело — Френкеля",
                          "Цермело Френкеля"]
    Wikipedia is inconsistent: "Аксиоматика Цермело — Френкеля" lives at one
    URL, "теория Цермело-Френкеля" redirects to another. Trying a few variants
    drastically improves hit rate without blowing up the request budget.
    """
    variants = [noun]
    seen = {noun}
    # Substitute each separator class with each other variant
    seps = ["-", "–", "—", " — ", " – ", " "]
    for sep_pattern in (r"[-–—]", r" [-–—] "):
        if re.search(sep_pattern, noun):
            for sep in seps:
                cand = re.sub(sep_pattern, sep, noun)
                if cand not in seen:
                    variants.append(cand)
                    seen.add(cand)
    return variants

# --- In-memory + disk cache for Wikipedia lookups ---
_CACHE_FILE = Path(__file__).parent / "output" / "wiki_cache.json"
_CACHE_TTL = 7 * 24 * 3600  # 7 days
_cache: dict[str, tuple[str | None, float]] = {}  # noun -> (url_or_None, timestamp)


def _load_cache() -> None:
    global _cache
    if _cache:
        return
    if _CACHE_FILE.exists():
        try:
            raw = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            _cache = {k: (v[0], v[1]) for k, v in raw.items()}
        except Exception:
            _cache = {}


def _save_cache() -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(
            json.dumps(_cache, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        logger.debug("Wiki cache save failed: %s", e)


def _cache_get(noun: str) -> tuple[bool, str | None]:
    """Return (hit, url_or_None). hit=False means not cached or expired."""
    _load_cache()
    key = noun.lower()
    if key in _cache:
        url, ts = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return True, url
    return False, None


def _cache_set(noun: str, url: str | None) -> None:
    _cache[noun.lower()] = (url, time.time())
    _save_cache()


def _extract_italic_nouns(text: str) -> list[str]:
    """Return unique non-numeric strings from <i>...</i> tags, longest first."""
    found = re.findall(r"<i>([^<]+)</i>", text)
    nouns = []
    seen = set()
    for n in found:
        n = n.strip()
        # Skip pure numbers, currencies, percentages
        if re.match(r"^[\d\s,.$€£%+\-×xX]+$", n):
            continue
        if len(n) < MIN_NOUN_LEN:
            continue
        if n.lower() not in seen:
            seen.add(n.lower())
            nouns.append(n)
    # longest first — reduces partial match issues
    return sorted(nouns, key=len, reverse=True)[:MAX_NOUNS]


async def _wiki_url(noun: str, client: httpx.AsyncClient) -> str | None:
    """Return Wikipedia article URL for noun, RU preferred, EN fallback.

    Tries dash/hyphen/em-dash variants of multi-part nouns to defeat the
    common case where Wikipedia article uses a different separator than
    the source text (e.g. "Цермело — Френкеля" vs "Цермело-Френкеля").
    """
    hit, cached_url = _cache_get(noun)
    if hit:
        return cached_url

    for variant in _noun_variants(noun):
        for lang in ("ru", "en"):
            try:
                url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(variant)}"
                resp = await client.get(url, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    data = resp.json()
                    page_url = data.get("content_urls", {}).get("desktop", {}).get("page")
                    _cache_set(noun, page_url)
                    return page_url
                if resp.status_code == 404:
                    continue
                if resp.status_code == 429:
                    return None
            except Exception as e:
                logger.debug("Wikipedia %s lookup failed for %r: %s", lang, variant, e)
                # Try the next variant rather than aborting on a single transient error.
                continue

    # Not found in any language / variant — cache the miss
    _cache_set(noun, None)
    return None


async def add_wiki_links(text: str) -> str:
    """
    Find proper nouns in <i> tags, look up Wikipedia,
    and wrap found ones with <a href>.
    Returns text with links added.
    """
    nouns = _extract_italic_nouns(text)
    if not nouns:
        return text

    async with httpx.AsyncClient(
        headers={"User-Agent": "BeautyNewsBot/1.0 (Telegram channel bot)"},
        follow_redirects=True,
    ) as client:
        tasks = [_wiki_url(noun, client) for noun in nouns]
        urls = await asyncio.gather(*tasks)

    for noun, wiki_url in zip(nouns, urls):
        if not wiki_url:
            continue
        # Replace <i>NOUN</i> → <a href="..."><i>NOUN</i></a>
        # Use re to avoid partial matches
        pattern = re.compile(re.escape(f"<i>{noun}</i>"))
        replacement = f'<a href="{wiki_url}"><i>{noun}</i></a>'
        text, count = pattern.subn(replacement, text, count=1)
        if count:
            logger.debug("Linked %r → %s", noun, wiki_url)

    return text
