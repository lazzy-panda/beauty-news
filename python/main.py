#!/usr/bin/env python3
"""
Beauty News — NotebookLM Deep Research Automation

Usage:
  python main.py run        Run the research pipeline immediately
  python main.py schedule   Start the daily morning scheduler
  python main.py news       Start the RSS news bot loop
  python main.py news-once  Post one RSS news item and exit
  python main.py start      Run RSS bot + daily research together
  python main.py login      Authenticate with Google (first-time setup)
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def cmd_run():
    from researcher import run_research_session

    results = asyncio.run(run_research_session())
    print("\n=== Done ===")
    for key, value in results.items():
        print(f"  {key}: {value}")


def cmd_schedule():
    from scheduler import run_scheduler
    import config

    print(f"Starting scheduler. Daily run at {config.SCHEDULE_TIME}.")
    print("Press Ctrl+C to stop.\n")
    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        print("\nScheduler stopped.")


def cmd_news():
    from rss_bot import run_news_bot

    print("Starting RSS News Bot. Press Ctrl+C to stop.\n")
    try:
        asyncio.run(run_news_bot())
    except KeyboardInterrupt:
        print("\nNews bot stopped.")


def cmd_news_once():
    from rss_bot import post_once

    ok = asyncio.run(post_once())
    print("Posted." if ok else "Nothing to post.")


def cmd_start():
    from rss_bot import run_news_bot
    from scheduler import run_scheduler

    print("Starting Beauty News (RSS bot + daily audio). Press Ctrl+C to stop.\n")
    try:
        async def _run_all():
            await asyncio.gather(run_news_bot(), run_scheduler())

        asyncio.run(_run_all())
    except KeyboardInterrupt:
        print("\nStopped.")


def cmd_login():
    """Run NotebookLM browser-based auth (first-time setup)."""
    import subprocess
    import shutil

    cli = shutil.which("notebooklm")
    if not cli:
        print("ERROR: notebooklm CLI not found. Run: pip install 'notebooklm-py[browser]'")
        return
    subprocess.run([cli, "login"], check=True)


COMMANDS = {
    "run": cmd_run,
    "schedule": cmd_schedule,
    "login": cmd_login,
    "news": cmd_news,
    "news-once": cmd_news_once,
    "start": cmd_start,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print(f"Available commands: {', '.join(COMMANDS)}")
        sys.exit(1)

    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
