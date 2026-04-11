"""
Sends generated audio to a Telegram channel via Bot API.
Uses httpx (already a dependency of notebooklm-py).
"""

import logging
from pathlib import Path

import httpx

import config

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}/{method}"


COVER_PATH = Path(__file__).parent.parent / "assets" / "freepik_minimalist-luxury-logo-fo_2761976520.png"


async def send_photo(image_path: Path, caption: str = "") -> bool:
    """Send a photo to the Telegram channel. Used as a cover before audio."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHANNEL_ID:
        return False

    url = API_BASE.format(token=config.TELEGRAM_BOT_TOKEN, method="sendPhoto")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            with open(image_path, "rb") as f:
                response = await client.post(
                    url,
                    data={
                        "chat_id": config.TELEGRAM_CHANNEL_ID,
                        "caption": caption,
                        "parse_mode": "HTML",
                    },
                    files={"photo": (image_path.name, f, "image/png")},
                )
        if response.status_code == 200 and response.json().get("ok"):
            logger.info("Cover photo sent to Telegram.")
            return True
        else:
            logger.error("Telegram sendPhoto error: %s", response.text)
            return False
    except Exception as exc:
        logger.error("Failed to send cover photo: %s", exc)
        return False


async def send_audio(audio_path: str, caption: str = "") -> bool:
    """Upload audio file to the configured Telegram channel.

    Returns True on success, False on failure.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHANNEL_ID:
        logger.warning("Telegram not configured — skipping upload.")
        return False

    path = Path(audio_path)
    if not path.exists():
        logger.error("Audio file not found: %s", audio_path)
        return False

    url = API_BASE.format(token=config.TELEGRAM_BOT_TOKEN, method="sendAudio")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            with open(path, "rb") as f:
                response = await client.post(
                    url,
                    data={
                        "chat_id": config.TELEGRAM_CHANNEL_ID,
                        "caption": caption,
                        "parse_mode": "HTML",
                    },
                    files={"audio": (path.name, f, "audio/mpeg")},
                )

        if response.status_code == 200 and response.json().get("ok"):
            logger.info("Audio sent to Telegram channel %s.", config.TELEGRAM_CHANNEL_ID)
            return True
        else:
            logger.error("Telegram API error: %s", response.text)
            return False

    except Exception as exc:
        logger.error("Failed to send audio to Telegram: %s", exc)
        return False
