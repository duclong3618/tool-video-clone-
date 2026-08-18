# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Analytics dashboard — track usage metrics and job statistics.

Provides endpoints for:
- Total jobs processed
- Success/failure rates
- Average processing time
- Language pair distribution
- TTS provider usage
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import Job, JobStatus, Video, get_db
from backend.api.auth import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class AnalyticsSummary(BaseModel):
    total_videos: int
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    processing_jobs: int
    success_rate: float
    avg_processing_time: float | None
    total_segments: int
    total_duration_hours: float


class DailyStats(BaseModel):
    date: str
    count: int
    successful: int
    failed: int


class LanguageStats(BaseModel):
    source_language: str
    target_language: str
    count: int


class ProviderStats(BaseModel):
    provider: str
    count: int


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Get analytics summary."""
    # Total videos
    result = await db.execute(select(func.count(Video.id)))
    total_videos = result.scalar() or 0

    # Total jobs
    result = await db.execute(select(func.count(Job.id)))
    total_jobs = result.scalar() or 0

    # Jobs by status
    result = await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.COMPLETED)
    )
    completed = result.scalar() or 0

    result = await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.FAILED)
    )
    failed = result.scalar() or 0

    result = await db.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.PROCESSING)
    )
    processing = result.scalar() or 0

    success_rate = (completed / total_jobs * 100) if total_jobs > 0 else 0

    return AnalyticsSummary(
        total_videos=total_videos,
        total_jobs=total_jobs,
        completed_jobs=completed,
        failed_jobs=failed,
        processing_jobs=processing,
        success_rate=round(success_rate, 1),
        avg_processing_time=None,  # TODO: calculate from timestamps
        total_segments=0,  # TODO: sum from segments table
        total_duration_hours=0.0,  # TODO: sum video durations
    )


@router.get("/daily", response_model=list[DailyStats])
async def get_daily_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Get daily job stats for the last N days."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(Job).where(Job.created_at >= since).order_by(Job.created_at)
    )
    jobs = result.scalars().all()

    # Group by date
    daily: dict[str, dict] = {}
    for job in jobs:
        date_str = job.created_at.strftime("%Y-%m-%d")
        if date_str not in daily:
            daily[date_str] = {"count": 0, "successful": 0, "failed": 0}
        daily[date_str]["count"] += 1
        if job.status == JobStatus.COMPLETED:
            daily[date_str]["successful"] += 1
        elif job.status == JobStatus.FAILED:
            daily[date_str]["failed"] += 1

    return [
        DailyStats(date=k, **v)
        for k, v in sorted(daily.items())
    ]


@router.get("/languages")
async def get_language_stats(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Get language pair distribution."""
    result = await db.execute(
        select(Video.source_language, Video.target_language, func.count(Video.id))
        .group_by(Video.source_language, Video.target_language)
    )
    rows = result.all()

    return [
        {"source_language": r[0], "target_language": r[1], "count": r[2]}
        for r in rows
    ]


@router.get("/providers")
async def get_provider_stats(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Get TTS provider usage stats."""
    result = await db.execute(select(Job.options))
    jobs = result.scalars().all()

    providers: dict[str, int] = {}
    for options_json in jobs:
        if options_json:
            try:
                opts = json.loads(options_json)
                provider = opts.get("tts_provider", "unknown")
                providers[provider] = providers.get(provider, 0) + 1
            except json.JSONDecodeError:
                pass

    return [{"provider": k, "count": v} for k, v in providers.items()]
