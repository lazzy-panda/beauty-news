"""
Morning scheduler: runs the research pipeline every day at SCHEDULE_TIME.
Uses asyncio + a lightweight polling loop — no extra dependencies needed.
"""

import asyncio
import logging
from datetime import datetime, time as dtime

import config
from researcher import run_research_session

logger = logging.getLogger(__name__)


def _parse_schedule_time() -> dtime:
    h, m = config.SCHEDULE_TIME.split(":")
    return dtime(int(h), int(m))


def _seconds_until(target: dtime) -> float:
    now = datetime.now()
    run_at = datetime.combine(now.date(), target)
    if run_at <= now:
        # Already passed today — schedule for tomorrow
        from datetime import timedelta
        run_at += timedelta(days=1)
    return (run_at - now).total_seconds()


async def run_once() -> dict:
    """Run the pipeline once and return results."""
    return await run_research_session()


async def run_scheduler():
    """
    Infinite loop: waits until SCHEDULE_TIME, runs the pipeline, then waits again.
    Press Ctrl+C to stop.
    """
    target = _parse_schedule_time()
    logger.info("Scheduler started. Daily run at %s.", config.SCHEDULE_TIME)

    last_run_date = None

    while True:
        wait_sec = _seconds_until(target)
        run_at = datetime.now().timestamp() + wait_sec
        logger.info(
            "Next run in %.0f minutes (at %s).",
            wait_sec / 60,
            datetime.fromtimestamp(run_at).strftime("%Y-%m-%d %H:%M"),
        )

        # Sleep in short intervals so macOS sleep/wake doesn't skip the target
        while True:
            remaining = _seconds_until(target)
            if remaining > 23 * 3600:
                break
            await asyncio.sleep(min(remaining, 60))

        today = datetime.now().date()
        if last_run_date == today:
            await asyncio.sleep(60)
            continue
        last_run_date = today

        logger.info("=== Scheduled run starting ===")
        try:
            results = await run_research_session()
            logger.info("Scheduled run finished: %s", results)
        except Exception as exc:
            logger.error("Scheduled run failed: %s", exc, exc_info=True)
