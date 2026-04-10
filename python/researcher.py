"""
Core NotebookLM automation using notebooklm-py.
Handles: research -> source import -> audio/video generation -> download.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from notebooklm import (
    NotebookLMClient,
    AudioFormat,
    AudioLength,
    VideoFormat,
    VideoStyle,
    RPCTimeoutError,
    NetworkError,
    RateLimitError,
)

import config
import news_log
import telegram_sender

logger = logging.getLogger(__name__)


def _get_audio_format(name: str) -> AudioFormat:
    return getattr(AudioFormat, name.upper(), AudioFormat.DEEP_DIVE)


def _get_audio_length(name: str) -> AudioLength:
    return getattr(AudioLength, name.upper(), AudioLength.DEFAULT)


def _get_video_format(name: str) -> VideoFormat:
    return getattr(VideoFormat, name.upper(), VideoFormat.EXPLAINER)


def _get_video_style(name: str) -> VideoStyle:
    return getattr(VideoStyle, name.upper(), VideoStyle.AUTO_SELECT)


async def run_research_session() -> dict:
    """
    Full pipeline: create notebook -> deep research -> generate audio+video -> download.
    Returns a dict with paths to downloaded files and the notebook id.
    """
    output_dir = Path(config.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    notebook_name = f"Beauty News — {date_str}"

    logger.info("Starting session: %s", notebook_name)

    async with await NotebookLMClient.from_storage() as client:
        # 1. Create notebook
        logger.info("Creating notebook: %s", notebook_name)
        nb = await client.notebooks.create(notebook_name)
        notebook_id = nb.id
        logger.info("Notebook created: %s", notebook_id)

        # 2. Build prompt with "already covered" context
        avoid_section = news_log.build_avoid_section()
        prompt = config.RESEARCH_PROMPT + avoid_section
        if avoid_section:
            logger.info("Injected %d chars of covered-topics context into prompt.", len(avoid_section))

        # 3. Start deep research (with retry on timeout/network errors)
        logger.info("Starting deep research (mode=%s)...", config.RESEARCH_MODE)
        research_status = await _start_research_with_retry(client, notebook_id, prompt)
        logger.info("Research started: task_id=%s", research_status.get("task_id") if research_status else None)

        # 4. Poll until research is done
        try:
            research_result = await _wait_for_research(client, notebook_id)
        except TimeoutError:
            logger.warning("Research timed out — proceeding with audio generation anyway.")
            research_result = {}
        sources = research_result.get("sources", [])
        logger.info("Research complete. Found %d sources.", len(sources))

        # Hard-filter sources already covered in recent sessions
        sources = news_log.filter_sources(sources)

        # Save to news log so future runs skip these topics
        summary = research_result.get("summary", "")
        source_titles = [s.get("title", "") for s in sources if s.get("title")]
        news_log.save_entry(notebook_id, summary, source_titles)

        # 5. Import research sources into the notebook
        task_id = (research_status or {}).get("task_id") or research_result.get("task_id")
        if task_id and sources:
            logger.info("Importing %d sources...", len(sources))
            try:
                imported = await client.research.import_sources(notebook_id, task_id, sources)
                logger.info("Imported %d sources.", len(imported))
            except Exception as exc:
                logger.warning("Source import failed (non-fatal): %s", exc)
        else:
            logger.warning("No sources to import (task_id=%s, sources=%d).", task_id, len(sources))

        # 6. Wait for sources to be indexed in the notebook
        await _wait_for_sources(client, notebook_id)

        # 7. Generate artifacts
        results = {"notebook_id": notebook_id, "notebook_name": notebook_name}

        # Audio (with retry on rate limit)
        logger.info("Generating audio...")
        try:
            audio_task = await _generate_audio_with_retry(client, notebook_id)
            logger.info("Waiting for audio completion (task_id=%s)...", audio_task.task_id)
            await client.artifacts.wait_for_completion(
                notebook_id, audio_task.task_id, timeout=float(config.GENERATION_TIMEOUT)
            )
            audio_path = output_dir / f"audio_{date_str}.mp3"
            await client.artifacts.download_audio(notebook_id, str(audio_path))
            logger.info("Audio saved: %s", audio_path)
            results["audio"] = str(audio_path)

            # Send to Telegram
            caption = f"<b>{notebook_name}</b>"
            await telegram_sender.send_audio(str(audio_path), caption=caption)
        except Exception as exc:
            logger.error("Audio failed: %s", exc, exc_info=True)

        # Video (optional)
        if getattr(config, "GENERATE_VIDEO", True):
            logger.info("Generating video...")
            try:
                video_task = await _generate_video(client, notebook_id)
                logger.info("Waiting for video completion (task_id=%s)...", video_task.task_id)
                await client.artifacts.wait_for_completion(
                    notebook_id, video_task.task_id, timeout=float(config.GENERATION_TIMEOUT)
                )
                video_path = output_dir / f"video_{date_str}.mp4"
                await client.artifacts.download_video(notebook_id, str(video_path))
                logger.info("Video saved: %s", video_path)
                results["video"] = str(video_path)
            except Exception as exc:
                logger.error("Video failed: %s", exc, exc_info=True)
        else:
            logger.info("Video generation skipped (GENERATE_VIDEO=False).")

        # 8. Clean up: delete the notebook to avoid accumulation
        try:
            await client.notebooks.delete(notebook_id)
            logger.info("Notebook deleted: %s", notebook_id)
        except Exception as exc:
            logger.warning("Notebook deletion failed (non-fatal): %s", exc)

        logger.info("Session complete. Results: %s", results)
        return results


async def _start_research_with_retry(client, notebook_id: str, prompt: str) -> dict:
    """Start research with retry. Falls back to 'fast' mode if 'deep' is rate-limited."""
    modes_to_try = [config.RESEARCH_MODE]
    if config.RESEARCH_MODE == "deep":
        modes_to_try.append("fast")  # fallback

    for mode in modes_to_try:
        if mode != config.RESEARCH_MODE:
            logger.warning("Deep research rate-limited — falling back to fast research.")

        delays = [30, 60]  # retry delays within the same mode
        last_exc = None
        rate_limited = False

        for attempt, delay in enumerate([0] + delays, start=1):
            if delay:
                logger.warning("Retrying in %ds (attempt %d)...", delay, attempt)
                await asyncio.sleep(delay)
            try:
                result = await client.research.start(
                    notebook_id,
                    query=prompt,
                    source=config.RESEARCH_SOURCE,
                    mode=mode,
                )
                logger.info("Research started with mode='%s'.", mode)
                return result or {}
            except RateLimitError as exc:
                logger.warning("Rate limit on mode='%s', attempt %d: %s", mode, attempt, exc)
                last_exc = exc
                rate_limited = True
                break  # no point retrying same mode — switch mode instead
            except (RPCTimeoutError, NetworkError) as exc:
                logger.warning("Transient error attempt %d: %s", attempt, exc)
                last_exc = exc
            except Exception as exc:
                raise

        if not rate_limited and last_exc:
            raise last_exc  # transient errors exhausted

    raise last_exc  # all modes rate-limited


async def _wait_for_research(client, notebook_id: str) -> dict:
    """Poll research.poll() until status == 'completed'."""
    deadline = asyncio.get_event_loop().time() + config.RESEARCH_TIMEOUT
    while asyncio.get_event_loop().time() < deadline:
        result = await client.research.poll(notebook_id)
        status = result.get("status", "")
        logger.debug("Research poll: status=%s", status)
        if status == "completed":
            return result
        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"Research failed with status: {status}")
        await asyncio.sleep(10)
    raise TimeoutError("Research did not complete within the timeout period.")


async def _wait_for_sources(client, notebook_id: str, timeout: int = 120) -> None:
    """Wait until the notebook has at least one indexed source."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            sources = await client.sources.list(notebook_id)
            if sources:
                logger.info("Sources ready: %d source(s) in notebook.", len(sources))
                return
        except Exception as exc:
            logger.debug("Waiting for sources: %s", exc)
        await asyncio.sleep(5)
    logger.warning("No sources appeared after %ds — proceeding anyway.", timeout)


RATE_LIMIT_RETRY_DELAYS = [300, 600, 900]  # seconds: 5 min, 10 min, 15 min


async def _generate_audio_with_retry(client, notebook_id: str):
    """Generate audio with retry on rate limit errors."""
    for attempt, delay in enumerate([0] + RATE_LIMIT_RETRY_DELAYS, start=1):
        if delay:
            logger.warning("Rate limit hit. Retrying in %ds (attempt %d)...", delay, attempt)
            await asyncio.sleep(delay)
        task = await _generate_audio(client, notebook_id)
        if task and task.task_id:
            return task
        if task and task.is_rate_limited:
            logger.warning("Rate limited: %s", task.error)
            continue
        raise RuntimeError(f"generate_audio returned invalid task: {task}")
    raise RuntimeError("Audio generation failed after all retries (rate limit).")


async def _generate_audio(client, notebook_id: str):
    return await client.artifacts.generate_audio(
        notebook_id,
        instructions=config.AUDIO_INSTRUCTIONS,
        audio_format=_get_audio_format(config.AUDIO_FORMAT),
        audio_length=_get_audio_length(config.AUDIO_LENGTH),
        language=config.AUDIO_LANGUAGE,
    )


async def _generate_video(client, notebook_id: str):
    return await client.artifacts.generate_video(
        notebook_id,
        video_format=_get_video_format(config.VIDEO_FORMAT),
        video_style=_get_video_style(config.VIDEO_STYLE),
        language=config.VIDEO_LANGUAGE,
    )
