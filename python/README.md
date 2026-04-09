# Beauty News — Python автоматизация

Каждое утро (или по запросу) запускает глубокое исследование в NotebookLM по 7 разделам beauty & fashion (индустрия, Россия, PR, martech, influencer marketing, креаторы, стратегия), генерирует аудио-подкаст и постит в Telegram. Подробности — в корневом `README.md`.

## Установка (один раз)

```bash
cd "/Users/kirill/MyApps/Beauty News/python"

pip install -r requirements.txt
playwright install chromium
```

## Авторизация (один раз)

```bash
notebooklm login
```

Откроется браузер Chromium — войдите в Google аккаунт, дождитесь главной страницы NotebookLM, вернитесь в терминал и нажмите **Enter**.

Учётные данные сохраняются в `~/.notebooklm/` и используются при каждом запуске.

## Запуск

### Прямо сейчас

```bash
cd "/Users/kirill/MyApps/Beauty News/python"
python3 main.py run
```

Скрипт:
1. Создаёт новый notebook с датой в названии
2. Запускает deep research (~5–15 минут)
3. Генерирует аудио и видео обзор (~15–30 минут)
4. Скачивает файлы в папку `output/`

### Каждое утро автоматически

```bash
cd "/Users/kirill/MyApps/Beauty News/python"
python3 main.py schedule
```

Запускается в фоне и выполняет `run` каждый день в 08:00. Остановить: **Ctrl+C**.

Чтобы процесс не умирал при закрытии терминала:

```bash
nohup python3 main.py schedule > output/schedule.log 2>&1 &
```

## Результаты

Файлы сохраняются в папку `output/` рядом со скриптом:

```
output/
  audio_2026-03-07_08-00.mp3
  video_2026-03-07_08-00.mp4
```

## Настройка

Все параметры в файле `config.py`:

| Параметр | По умолчанию | Описание |
|---|---|---|
| `RESEARCH_PROMPT` | AI/VR/Tech/Startups/KS | Промпт для deep research |
| `SCHEDULE_TIME` | `"08:00"` | Время ежедневного запуска |
| `AUDIO_FORMAT` | `DEEP_DIVE` | Формат аудио: `DEEP_DIVE`, `BRIEF`, `CRITIQUE`, `DEBATE` |
| `AUDIO_LENGTH` | `DEFAULT` | Длина: `SHORT`, `DEFAULT`, `LONG` |
| `VIDEO_FORMAT` | `EXPLAINER` | Формат видео: `EXPLAINER`, `BRIEF` |
| `VIDEO_STYLE` | `AUTO_SELECT` | Стиль: `CLASSIC`, `WHITEBOARD`, `ANIME`, `KAWAII` и др. |
| `OUTPUT_DIR` | `./output` | Папка для скачанных файлов |
| `RESEARCH_TIMEOUT` | 10 мин | Максимальное время ожидания research |
| `GENERATION_TIMEOUT` | 30 мин | Максимальное время генерации аудио/видео |

## Структура файлов

```
python/
  main.py          — точка входа (run / schedule / login)
  config.py        — все настройки
  researcher.py    — логика: research → генерация → скачивание
  scheduler.py     — планировщик ежедневных запусков
  requirements.txt — зависимости
  output/          — скачанные MP3 и MP4
```
