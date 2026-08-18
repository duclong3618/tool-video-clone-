# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Application configuration loaded from environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "VideoDubAI"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # ── Server ───────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/videodub"

    # ── Redis / Celery ───────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Storage ──────────────────────────────────────────
    UPLOAD_DIR: str = str(STORAGE_DIR / "uploads")
    AUDIO_DIR: str = str(STORAGE_DIR / "audio")
    VOCALS_DIR: str = str(STORAGE_DIR / "vocals")
    BACKGROUND_DIR: str = str(STORAGE_DIR / "background")
    TTS_DIR: str = str(STORAGE_DIR / "tts")
    OUTPUT_DIR: str = str(STORAGE_DIR / "output")
    MAX_UPLOAD_SIZE_MB: int = 500

    # ── WhisperX / ASR ───────────────────────────────────
    WHISPER_MODEL: str = "large-v3"
    WHISPER_DEVICE: str = "auto"  # auto | cuda | cpu
    WHISPER_COMPUTE_TYPE: str = "auto"  # auto | fp16 | int8

    # ── Translation ──────────────────────────────────────
    TRANSLATION_PROVIDER: str = "openai"  # openai | ollama
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    TRANSLATION_MODEL: str = "gpt-4o-mini"
    SOURCE_LANGUAGE: str = "zh"
    TARGET_LANGUAGE: str = "vi"

    # ── Supported Languages ──────────────────────────────
    SUPPORTED_SOURCE_LANGUAGES: list[str] = ["zh", "ja", "ko", "en", "auto"]
    SUPPORTED_TARGET_LANGUAGES: list[str] = ["vi", "en", "zh", "ja", "ko"]
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"

    # ── TTS ──────────────────────────────────────────────
    TTS_PROVIDER: str = "edge"  # edge | elevenlabs | qwen3tts
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_MODEL: str = "eleven_multilingual_v2"
    QWEN3_TTS_API_KEY: str = ""
    QWEN3_TTS_BASE_URL: str = ""

    # ── Diarization (pyannote) ───────────────────────────
    PYANNOTE_AUTH_TOKEN: str = ""

    # ── File limits ──────────────────────────────────────
    ALLOWED_VIDEO_EXTENSIONS: list[str] = [
        ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def ensure_storage_dirs() -> None:
    """Create storage directories if they don't exist."""
    s = get_settings()
    for d in [
        s.UPLOAD_DIR, s.AUDIO_DIR, s.VOCALS_DIR,
        s.BACKGROUND_DIR, s.TTS_DIR, s.OUTPUT_DIR,
    ]:
        os.makedirs(d, exist_ok=True)
