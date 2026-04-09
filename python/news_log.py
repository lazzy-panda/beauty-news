"""
Persistent log of covered news topics.
Saves summaries after each research session so future runs can avoid repeats.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import config

logger = logging.getLogger(__name__)

LOG_FILE = Path(config.OUTPUT_DIR) / "news_log.json"
# How many past days to include in the "avoid repeating" context
LOOKBACK_DAYS = 5


def load_entries() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    try:
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read news log: %s", exc)
        return []


def save_entry(notebook_id: str, summary: str, source_titles: list[str]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entries = load_entries()
    entries.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "notebook_id": notebook_id,
        "summary": summary,
        "source_titles": source_titles[:30],  # cap to avoid huge files
    })
    try:
        LOG_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("News log updated (%d entries total).", len(entries))
    except Exception as exc:
        logger.warning("Could not write news log: %s", exc)


def _extract_proper_phrases(title: str) -> list[str]:
    """Extract multi-word proper nouns from a title (e.g. 'Open Claw', 'Meta Quest')."""
    import re
    # Clean separators
    title = title.replace("—", " ").replace("–", " ").replace(":", " ").replace("|", " ")
    words = title.split()
    phrases = []
    current = []
    for word in words:
        clean = re.sub(r"[^\w]", "", word)
        if not clean:
            if current:
                phrases.append(" ".join(current))
                current = []
            continue
        # Capitalized word (not a short filler like "The", "And", "For")
        is_proper = (
            len(clean) >= 2
            and clean[0].isupper()
            and clean not in {"The", "And", "For", "With", "From", "That", "This", "Its", "Are", "Has", "Was", "New"}
        )
        if is_proper:
            current.append(clean)
        else:
            if current:
                phrases.append(" ".join(current))
                current = []
    if current:
        phrases.append(" ".join(current))
    # Keep phrases with 2+ words, or single words 4+ chars
    return [p for p in phrases if len(p.split()) >= 2 or len(p) >= 4]


def build_avoid_section() -> str:
    """Return a text block listing previously covered topics for injection into the prompt."""
    entries = load_entries()
    if not entries:
        return ""

    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    recent = []
    for e in reversed(entries):
        try:
            entry_date = datetime.strptime(e["date"], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if entry_date < cutoff:
            break
        recent.append(e)

    if not recent:
        return ""

    # Collect product/project names as multi-word phrases from titles
    seen_terms = set()
    for e in recent:
        for title in e.get("source_titles", []):
            # Extract consecutive capitalized words as phrases (e.g. "Open Claw")
            phrases = _extract_proper_phrases(title)
            seen_terms.update(phrases)

    lines = [
        "\n\nCRITICAL REQUIREMENT — The following topics, products, and projects were ALREADY covered. "
        "You MUST NOT mention them again, even briefly. Find DIFFERENT news instead:",
    ]
    if seen_terms:
        lines.append("BANNED terms (do NOT mention): " + ", ".join(sorted(seen_terms)[:80]))

    lines.append("\nPreviously covered sessions:")
    for e in reversed(recent):  # chronological order
        titles = e.get("source_titles", [])
        summary = e.get("summary", "").strip()
        lines.append(f"\n[{e['date']}]")
        if summary:
            lines.append(f"  Summary: {summary[:200]}{'...' if len(summary) > 200 else ''}")
        if titles:
            lines.append("  Topics: " + "; ".join(titles[:15]))

    return "\n".join(lines)


def get_seen_titles(lookback_days: int = LOOKBACK_DAYS) -> set[str]:
    """Return a set of lowercased source titles from recent sessions."""
    entries = load_entries()
    if not entries:
        return set()
    cutoff = datetime.now() - timedelta(days=lookback_days)
    seen = set()
    for e in reversed(entries):
        try:
            entry_date = datetime.strptime(e["date"], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if entry_date < cutoff:
            break
        for title in e.get("source_titles", []):
            seen.add(_normalize(title))
    return seen


def _normalize(title: str) -> str:
    """Lowercase, strip trailing junk like ' - SiteName'."""
    t = title.lower().strip()
    # Remove common "- Source Name" suffixes for better matching
    for sep in (" - ", " | ", " — ", " – "):
        if sep in t:
            t = t[:t.rfind(sep)]
    return t


def filter_sources(sources: list[dict]) -> list[dict]:
    """Remove sources whose titles closely match previously seen ones."""
    seen = get_seen_titles()
    if not seen:
        return sources

    filtered = []
    for s in sources:
        title = s.get("title", "")
        norm = _normalize(title)
        # Exact match after normalization
        if norm in seen:
            logger.info("Filtered duplicate source: %s", title)
            continue
        # Substring match: skip if a seen title is contained or vice versa
        is_dup = False
        for prev in seen:
            if len(prev) >= 15 and (prev in norm or norm in prev):
                logger.info("Filtered similar source: %s (matches: %s)", title, prev)
                is_dup = True
                break
        if not is_dup:
            filtered.append(s)

    if len(filtered) < len(sources):
        logger.info("Source dedup: %d -> %d (removed %d duplicates).",
                     len(sources), len(filtered), len(sources) - len(filtered))
    return filtered
