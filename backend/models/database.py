# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Database models using SQLAlchemy async.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from backend.config import get_settings


class Base(DeclarativeBase):
    pass


# ── Enums ────────────────────────────────────────────────

class JobStatus(str, PyEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStep(str, PyEnum):
    UPLOADING = "uploading"
    EXTRACTING_AUDIO = "extracting_audio"
    SEPARATING_VOCALS = "separating_vocals"
    TRANSCRIBING = "transcribing"
    DETECTING_SPEAKERS = "detecting_speakers"
    TRANSLATING = "translating"
    GENERATING_VOICES = "generating_voices"
    SYNCHRONIZING_AUDIO = "synchronizing_audio"
    MIXING_AUDIO = "mixing_audio"
    RENDERING_VIDEO = "rendering_video"
    COMPLETED = "completed"


class SegmentStatus(str, PyEnum):
    PENDING = "pending"
    TRANSLATED = "translated"
    TTS_GENERATED = "tts_generated"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Models ───────────────────────────────────────────────

class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(512), nullable=False)
    original_path = Column(String(1024), nullable=False)
    output_path = Column(String(1024), nullable=True)
    source_language = Column(String(10), default="zh")
    target_language = Column(String(10), default="vi")
    duration = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    jobs = relationship("Job", back_populates="video", cascade="all, delete-orphan")
    segments = relationship("Segment", back_populates="video", cascade="all, delete-orphan")
    speakers = relationship("Speaker", back_populates="video", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED)
    current_step = Column(Enum(JobStep), nullable=True)
    progress = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    options = Column(Text, nullable=True)  # JSON string for job options
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    video = relationship("Video", back_populates="jobs")


class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
    label = Column(String(50), nullable=False)  # e.g., "speaker_01"
    voice_id = Column(String(256), nullable=True)
    voice_name = Column(String(256), nullable=True)

    video = relationship("Video", back_populates="speakers")
    segments = relationship("Segment", back_populates="speaker")


class Segment(Base):
    __tablename__ = "segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
    speaker_id = Column(UUID(as_uuid=True), ForeignKey("speakers.id"), nullable=True)
    index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=True)
    audio_path = Column(String(1024), nullable=True)
    status = Column(Enum(SegmentStatus), default=SegmentStatus.PENDING)

    video = relationship("Video", back_populates="segments")
    speaker = relationship("Speaker", back_populates="segments")


# ── Database setup ───────────────────────────────────────

engine = None
async_session_factory = None


def init_db(url: str | None = None):
    global engine, async_session_factory
    settings = get_settings()
    db_url = url or settings.DATABASE_URL
    # Fallback to SQLite if PostgreSQL is unavailable
    if "postgresql" in db_url:
        db_url = "sqlite+aiosqlite:///./videodub.db"
    engine = create_async_engine(db_url, echo=settings.DEBUG)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    if async_session_factory is None:
        init_db()
    async with async_session_factory() as session:
        yield session


async def create_tables():
    if engine is None:
        init_db()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
