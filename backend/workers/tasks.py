# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Celery tasks for background video processing.
"""

from __future__ import annotations

import json
import logging
import os
import uuid

from celery import Task

from backend.workers.celery_app import celery_app
from backend.config import get_settings, ensure_storage_dirs
from backend.services.video import VideoDubPipeline, PipelineOptions

logger = logging.getLogger(__name__)


class DubbingTask(Task):
    """Base task with retry logic."""
    autoretry_for = (Exception,)
    retry_backoff = True
    max_retries = 2


@celery_app.task(
    base=DubbingTask,
    bind=True,
    name="dub_video",
    max_retries=2,
)
def dub_video(
    self,
    job_id: str,
    video_id: str,
    input_video: str,
    options_json: str = "{}",
) -> dict:
    """
    Main dubbing task — runs the full pipeline.
    
    This runs in the Celery worker process.
    For the MVP, we use FastAPI background tasks instead.
    This Celery version is for production deployments.
    """
    import asyncio

    ensure_storage_dirs()
    settings = get_settings()

    # Parse options
    opts = json.loads(options_json) if options_json else {}
    options = PipelineOptions(**opts)

    # Update job status
    asyncio.get_event_loop().run_until_complete(
        _update_job_status(job_id, "processing", "extracting_audio", 0)
    )

    async def on_progress(step: str, progress: float, message: str):
        asyncio.get_event_loop().run_until_complete(
            _update_job_status(job_id, "processing", step, progress)
        )

    try:
        pipeline = VideoDubPipeline()
        result = asyncio.get_event_loop().run_until_complete(
            pipeline.run(
                video_id=video_id,
                input_video=input_video,
                options=options,
                on_progress=on_progress,
            )
        )

        if result.success:
            asyncio.get_event_loop().run_until_complete(
                _update_job_status(job_id, "completed", "completed", 100.0)
            )
            return {
                "status": "completed",
                "output_video": result.output_video,
                "segments": len(result.segments),
            }
        else:
            asyncio.get_event_loop().run_until_complete(
                _update_job_failed(job_id, result.error)
            )
            return {"status": "failed", "error": result.error}

    except Exception as e:
        logger.error("Celery task failed: %s", e, exc_info=True)
        asyncio.get_event_loop().run_until_complete(
            _update_job_failed(job_id, str(e))
        )
        raise


async def _update_job_status(
    job_id: str, status: str, step: str | None, progress: float
) -> None:
    """Update job status in database."""
    from backend.models.database import init_db, async_session_factory, Job, JobStatus, JobStep
    import select

    init_db()
    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
        job = result.scalar_one_or_none()
        if job:
            job.status = JobStatus(status)
            if step:
                try:
                    job.current_step = JobStep(step)
                except ValueError:
                    pass
            job.progress = progress
            await db.commit()


async def _update_job_failed(job_id: str, error: str) -> None:
    """Mark job as failed."""
    await _update_job_status(job_id, "failed", None, 0)
    from backend.models.database import init_db, async_session_factory, Job
    import select

    init_db()
    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
        job = result.scalar_one_or_none()
        if job:
            job.error_message = error
            await db.commit()
