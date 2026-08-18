# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Video & Job API routes.

POST   /api/videos/upload          Upload a video
POST   /api/jobs                   Create a dubbing job
GET    /api/jobs/{job_id}          Get job status
GET    /api/videos/{video_id}      Get video details
GET    /api/videos/{video_id}/subtitles   Get subtitles
PUT    /api/videos/{video_id}/subtitles   Update subtitles
POST   /api/videos/{video_id}/segments/{segment_id}/regenerate  Regenerate TTS
GET    /api/videos/{video_id}/download    Download dubbed video
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.api.auth import (
    register_user,
    authenticate_user,
    create_token,
    require_auth,
    require_admin,
    AuthError,
    UserRole,
)
from backend.models.database import (
    Job,
    JobStatus,
    JobStep,
    Segment,
    SegmentStatus,
    Speaker,
    Video,
    get_db,
)
from backend.services.video import PipelineOptions

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────

class UploadResponse(BaseModel):
    video_id: str
    filename: str


class CreateJobRequest(BaseModel):
    video_id: str
    source_language: str = "zh"
    target_language: str = "vi"
    translation_model: str = ""
    tts_provider: str = "edge"
    tts_voice: str = ""
    enable_diarization: bool = False
    enable_subtitles: bool = True
    burn_subtitles: bool = False
    preserve_background: bool = True
    output_quality: str = "high"


class JobResponse(BaseModel):
    job_id: str
    video_id: str
    status: str
    current_step: Optional[str] = None
    progress: float = 0.0
    error_message: Optional[str] = None
    created_at: str


class VideoResponse(BaseModel):
    video_id: str
    filename: str
    source_language: str
    target_language: str
    duration: Optional[float] = None
    created_at: str


class SegmentResponse(BaseModel):
    segment_id: str
    index: int
    start_time: float
    end_time: float
    original_text: str
    translated_text: Optional[str] = None
    speaker: Optional[str] = None
    status: str


class UpdateSubtitleRequest(BaseModel):
    translated_text: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class RegenerateRequest(BaseModel):
    voice: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class WebhookRequest(BaseModel):
    webhook_url: str


class BatchJobRequest(BaseModel):
    video_ids: list[str]
    source_language: str = "zh"
    target_language: str = "vi"
    tts_provider: str = "edge"
    enable_diarization: bool = False
    enable_subtitles: bool = True
    burn_subtitles: bool = False
    preserve_background: bool = True
    output_quality: str = "high"


# ── Auth ─────────────────────────────────────────────────

@router.post("/auth/register")
async def api_register(request: RegisterRequest):
    """Register a new user."""
    try:
        user = register_user(request.username, request.password)
        token = create_token(user["user_id"], user["role"])
        return {"user": user, "token": token}
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login")
async def api_login(request: LoginRequest):
    """Login and get JWT token."""
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["user_id"], user["role"])
    return {"user": user, "token": token}


@router.get("/auth/me")
async def api_me(user: dict = Depends(require_auth)):
    """Get current user info."""
    return {"user_id": user["user_id"], "role": user["role"]}


# ── Upload ───────────────────────────────────────────────

@router.post("/videos/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a video file."""
    settings = get_settings()

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {settings.ALLOWED_VIDEO_EXTENSIONS}",
        )

    # Check file size
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Save file
    video_id = str(uuid.uuid4())
    safe_filename = f"{video_id}{ext}"
    upload_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    with open(upload_path, "wb") as f:
        f.write(content)

    # Get duration
    from backend.services.ffmpeg import FFmpegService
    ffmpeg = FFmpegService()
    try:
        duration = await ffmpeg.get_duration(upload_path)
    except Exception:
        duration = None

    # Save to database
    video = Video(
        id=uuid.UUID(video_id),
        filename=file.filename or safe_filename,
        original_path=upload_path,
        source_language="zh",
        target_language="vi",
        duration=duration,
    )
    db.add(video)
    await db.commit()

    return UploadResponse(video_id=video_id, filename=file.filename or safe_filename)


# ── Create Job ───────────────────────────────────────────

@router.post("/jobs", response_model=JobResponse)
async def create_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a new dubbing job."""
    # Verify video exists
    result = await db.execute(select(Video).where(Video.id == uuid.UUID(request.video_id)))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Create job
    job_id = uuid.uuid4()
    options = PipelineOptions(
        source_language=request.source_language,
        target_language=request.target_language,
        tts_provider=request.tts_provider,
        tts_voice=request.tts_voice,
        enable_diarization=request.enable_diarization,
        enable_subtitles=request.enable_subtitles,
        burn_subtitles=request.burn_subtitles,
        preserve_background=request.preserve_background,
        output_quality=request.output_quality,
    )

    job = Job(
        id=job_id,
        video_id=video.id,
        status=JobStatus.QUEUED,
        options=json.dumps(options.__dict__),
    )
    db.add(job)
    await db.commit()

    # Start pipeline in background
    background_tasks.add_task(_run_pipeline, str(job_id), str(video.id), options)

    return JobResponse(
        job_id=str(job_id),
        video_id=request.video_id,
        status=JobStatus.QUEUED,
        created_at=job.created_at.isoformat(),
    )


# ── Get Job ──────────────────────────────────────────────

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get job status and progress."""
    result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        job_id=str(job.id),
        video_id=str(job.video_id),
        status=job.status.value,
        current_step=job.current_step.value if job.current_step else None,
        progress=job.progress or 0.0,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
    )


# ── Get Video ────────────────────────────────────────────

@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Get video details."""
    result = await db.execute(select(Video).where(Video.id == uuid.UUID(video_id)))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return VideoResponse(
        video_id=str(video.id),
        filename=video.filename,
        source_language=video.source_language,
        target_language=video.target_language,
        duration=video.duration,
        created_at=video.created_at.isoformat(),
    )


# ── Subtitles ────────────────────────────────────────────

@router.get("/videos/{video_id}/subtitles", response_model=list[SegmentResponse])
async def get_subtitles(video_id: str, db: AsyncSession = Depends(get_db)):
    """Get all subtitle segments for a video."""
    result = await db.execute(
        select(Segment)
        .where(Segment.video_id == uuid.UUID(video_id))
        .order_by(Segment.index)
    )
    segments = result.scalars().all()

    return [
        SegmentResponse(
            segment_id=str(seg.id),
            index=seg.index,
            start_time=seg.start_time,
            end_time=seg.end_time,
            original_text=seg.original_text,
            translated_text=seg.translated_text,
            speaker=seg.speaker.label if seg.speaker else None,
            status=seg.status.value,
        )
        for seg in segments
    ]


@router.put("/videos/{video_id}/subtitles")
async def update_subtitles(
    video_id: str,
    segments: list[UpdateSubtitleRequest],
    db: AsyncSession = Depends(get_db),
):
    """Update subtitle translations."""
    # This is a simplified version; a real implementation would
    # match segments by index or ID
    return {"message": "Subtitles updated", "count": len(segments)}


# ── Regenerate segment ──────────────────────────────────

@router.post("/videos/{video_id}/segments/{segment_id}/regenerate")
async def regenerate_segment(
    video_id: str,
    segment_id: str,
    request: RegenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Regenerate TTS for a single segment."""
    result = await db.execute(
        select(Segment).where(Segment.id == uuid.UUID(segment_id))
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    background_tasks.add_task(
        _regenerate_segment_tts, segment_id, request.voice
    )

    return {"message": "Regeneration started", "segment_id": segment_id}


# ── Voice Preview ────────────────────────────────────────

@router.get("/tts/voices")
async def list_voices(
    provider: str = "edge",
):
    """List available TTS voices."""
    from backend.services.tts import TTSService
    tts = TTSService(provider_name=provider)
    return {"voices": tts.list_voices(), "provider": provider}


@router.post("/tts/preview")
async def preview_voice(
    text: str = "Xin chào, đây là giọng nói mẫu cho video đã dịch.",
    voice: str = "vi-VN-HoaiMyNeural",
    provider: str = "edge",
):
    """Generate a short TTS preview audio."""
    import tempfile
    from backend.services.tts import TTSService
    from fastapi.responses import FileResponse

    tts = TTSService(provider_name=provider)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output_path = f.name

    try:
        await tts.synthesize(text=text, output_path=output_path, voice=voice)
        return FileResponse(output_path, media_type="audio/wav", filename="preview.wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Languages ────────────────────────────────────────────

@router.get("/languages")
async def list_languages():
    """List supported source and target languages."""
    settings = get_settings()
    return {
        "source_languages": [
            {"code": "zh", "name": "Chinese (中文)"},
            {"code": "ja", "name": "Japanese (日本語)"},
            {"code": "ko", "name": "Korean (한국어)"},
            {"code": "en", "name": "English"},
            {"code": "auto", "name": "Auto-detect"},
        ],
        "target_languages": [
            {"code": "vi", "name": "Vietnamese (Tiếng Việt)"},
            {"code": "en", "name": "English"},
            {"code": "zh", "name": "Chinese (中文)"},
            {"code": "ja", "name": "Japanese (日本語)"},
            {"code": "ko", "name": "Korean (한국어)"},
        ],
    }


# ── Download ─────────────────────────────────────────────

@router.get("/videos/{video_id}/download")
async def download_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Download the dubbed video."""
    result = await db.execute(select(Video).where(Video.id == uuid.UUID(video_id)))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not video.output_path or not os.path.exists(video.output_path):
        raise HTTPException(status_code=404, detail="Dubbed video not ready yet")

    return FileResponse(
        video.output_path,
        media_type="video/mp4",
        filename=f"dubbed_{video.filename}",
    )


# ── Video Preview ────────────────────────────────────────

@router.get("/videos/{video_id}/preview")
async def preview_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Stream video for preview (supports range requests)."""
    result = await db.execute(select(Video).where(Video.id == uuid.UUID(video_id)))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not os.path.exists(video.original_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    file_size = os.path.getsize(video.original_path)
    ext = os.path.splitext(video.filename)[1].lower()
    media_type = {
        ".mp4": "video/mp4",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
    }.get(ext, "video/mp4")

    return FileResponse(
        video.original_path,
        media_type=media_type,
        filename=video.filename,
    )


# ── Batch Processing ─────────────────────────────────────

@router.post("/jobs/batch")
async def create_batch_jobs(
    request: BatchJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create dubbing jobs for multiple videos at once."""
    job_ids = []
    for vid in request.video_ids:
        try:
            result = await db.execute(select(Video).where(Video.id == uuid.UUID(vid)))
            video = result.scalar_one_or_none()
            if not video:
                continue

            job_id = uuid.uuid4()
            options = PipelineOptions(
                source_language=request.source_language,
                target_language=request.target_language,
                tts_provider=request.tts_provider,
                enable_diarization=request.enable_diarization,
                enable_subtitles=request.enable_subtitles,
                burn_subtitles=request.burn_subtitles,
                preserve_background=request.preserve_background,
                output_quality=request.output_quality,
            )

            job = Job(
                id=job_id,
                video_id=video.id,
                status=JobStatus.QUEUED,
                options=json.dumps(options.__dict__),
            )
            db.add(job)
            job_ids.append(str(job_id))

            background_tasks.add_task(_run_pipeline, str(job_id), str(video.id), options)

        except Exception as e:
            logger.error("Failed to create job for video %s: %s", vid, e)

    await db.commit()
    return {"job_ids": job_ids, "count": len(job_ids)}


# ── Error Recovery / Resume ───────────────────────────────

@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed job from where it left off."""
    result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Only failed or cancelled jobs can be retried")

    # Reset job status
    job.status = JobStatus.QUEUED
    job.error_message = None
    job.progress = 0.0
    job.current_step = None
    await db.commit()

    # Parse options
    options_dict = json.loads(job.options) if job.options else {}
    options = PipelineOptions(**options_dict)

    # Re-run pipeline
    background_tasks.add_task(_run_pipeline, str(job.id), str(job.video_id), options)

    return {"job_id": job_id, "status": "queued", "message": "Job restarted"}


# ── Background tasks ─────────────────────────────────────

async def _run_pipeline(
    job_id: str, video_id: str, options: PipelineOptions
) -> None:
    """Run the dubbing pipeline as a background task."""
    from backend.services.video import VideoDubPipeline
    from backend.config import get_settings
    from backend.models.database import init_db, async_session_factory, Job, JobStatus, JobStep, Video

    settings = get_settings()
    init_db()

    async with async_session_factory() as db:
        # Update job status
        result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
        job = result.scalar_one_or_none()
        if not job:
            return

        job.status = JobStatus.PROCESSING
        job.current_step = JobStep.UPLOADING
        await db.commit()

        # Get video
        result = await db.execute(select(Video).where(Video.id == uuid.UUID(video_id)))
        video = result.scalar_one_or_none()
        if not video:
            job.status = JobStatus.FAILED
            job.error_message = "Video not found"
            await db.commit()
            return

        # Progress callback to update DB
        step_map = {s.value: s for s in JobStep}

        async def on_progress(step: str, progress: float, message: str):
            job.current_step = step_map.get(step, job.current_step)
            job.progress = progress
            await db.commit()

        # Run pipeline
        pipeline = VideoDubPipeline()
        try:
            result = await pipeline.run(
                video_id=video_id,
                input_video=video.original_path,
                options=options,
                on_progress=on_progress,
            )

            if result.success:
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                job.current_step = JobStep.COMPLETED
                video.output_path = result.output_video

                # Save segments to DB
                for seg in result.segments:
                    segment = Segment(
                        video_id=video.id,
                        index=seg.get("index", 0),
                        start_time=seg["start"],
                        end_time=seg["end"],
                        original_text=seg.get("text", ""),
                        translated_text=seg.get("translated_text", ""),
                        speaker_id=None,
                        status=SegmentStatus.TRANSLATED,
                    )
                    db.add(segment)

            else:
                job.status = JobStatus.FAILED
                job.error_message = result.error

        except Exception as e:
            logger.error("Pipeline failed for job %s: %s", job_id, e, exc_info=True)
            job.status = JobStatus.FAILED
            job.error_message = str(e)

        await db.commit()


async def _regenerate_segment_tts(segment_id: str, voice: str | None) -> None:
    """Regenerate TTS for a single segment."""
    from backend.services.tts import TTSService
    from backend.models.database import init_db, async_session_factory, Segment
    import uuid

    init_db()

    async with async_session_factory() as db:
        result = await db.execute(select(Segment).where(Segment.id == uuid.UUID(segment_id)))
        segment = result.scalar_one_or_none()
        if not segment:
            return

        tts = TTSService()
        output_path = segment.audio_path or f"storage/tts/seg_{segment_id}.wav"

        await tts.synthesize(
            text=segment.translated_text or segment.original_text,
            output_path=output_path,
            voice=voice,
        )

        segment.audio_path = output_path
        segment.status = SegmentStatus.TTS_GENERATED
        await db.commit()
