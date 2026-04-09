"""
Translates English news articles to natural Russian using OpenAI gpt-4o-mini.
"""

import logging

from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None

SYSTEM_PROMPT = """Ты редактор Telegram-канала о beauty и fashion индустрии, маркетинге, PR и influencer-стратегиях. Тебе дают заголовок и описание новости на английском.

Напиши пост на живом, естественном русском — 2–3 предложения. Без буквальных переводов. Без вводных слов «Итак», «Сегодня», «Стоит отметить». Без заголовка.

Форматируй текст в Telegram HTML:
- <b>жирным</b> — ключевые слова и главная суть (1–3 слова на предложение)
- <i>курсивом</i> — имена собственные, названия компаний/продуктов, все числа и цифры
- <u>подчёркнутым</u> — только если есть чёткий вывод или итог, не более 4 слов в конце поста
- <tg-spoiler>скрытым</tg-spoiler> — только если контент пугающий, шокирующий или неприличный
- Разумно добавляй эмодзи (1–3 штуки по смыслу, не в каждом предложении)
- Если несколько абзацев — разделяй пустой строкой
- Спецсимволы &, <, > вне тегов — экранируй как &amp; &lt; &gt;

Выводи только готовый текст поста, без пояснений."""


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def translate_article(title: str, description: str) -> str:
    """
    Translate and rewrite article to natural Russian.
    Falls back to the raw title on error.
    """
    user_message = f"Заголовок: {title}\nОписание: {description}"
    try:
        resp = await _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=300,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI translation failed: %s", e)
        return title
