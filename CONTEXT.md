# VideoDubAI — Shared Language & Domain Glossary

> Author: DUC LONG
> Year: 2026
> Project: VideoDubAI

## Overview

VideoDubAI là nền tảng web AI chuyển đổi và lồng tiếng video từ ngôn ngữ nguồn sang tiếng Việt.

## Core Concepts

| Term | Definition |
|------|-----------|
| **Pipeline** | Chuỗi xử lý end-to-end: upload → extract → transcribe → translate → TTS → mix → export |
| **Segment** | Một câu/dialog trong video, có start_time, end_time, original_text, translated_text |
| **Speaker** | Người nói được phát hiện qua diarization, mỗi speaker có voice riêng |
| **Job** | Một lần chạy pipeline trên một video, có status (queued → processing → completed/failed) |
| **Diarization** | Phân biệt người nói khác nhau trong audio |
| **TTS** | Text-to-Speech — chuyển text thành giọng nói |
| **Vocal Separation** | Tách giọng nói khỏi nhạc nền (sử dụng Demucs) |
| **Edge TTS** | Microsoft TTS miễn phí, giọng tiếng Việt chất lượng tốt |
| **Burn Subtitles** | Đốt phụ đề cứng vào video (hardcode) |
| **Lip-sync** | Đồng bộ môi với âm thanh (LatentSync — optional) |

## Architecture Layers

```
Frontend (Next.js)     → User Interface
    ↓ HTTP/WebSocket
API Routes (FastAPI)   → Request handling
    ↓
Services               → Business logic
    ├── VideoDubPipeline  → Orchestrator
    ├── FFmpegService     → Video/audio processing
    ├── TranscriptionService → WhisperX/faster-whisper
    ├── TranslationService → OpenAI/Ollama
    ├── TTSService        → Edge/ElevenLabs/Qwen3
    ├── AudioMixerService → Mix tracks
    ├── SubtitleService   → SRT/ASS generation
    └── TranslationCache  → Redis/disk cache
    ↓
Workers (Celery)       → Background jobs
    ↓
Database (SQLite/PostgreSQL) → State persistence
```

## Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Files | snake_case | `audio_mixer.py`, `video.py` |
| Classes | PascalCase | `FFmpegService`, `TTSService` |
| API endpoints | kebab-case | `/api/videos/{id}/subtitles` |
| Variables | snake_case | `total_duration`, `background_path` |
| Constants | UPPER_SNAKE | `SYSTEM_PROMPT`, `FFMPEG_BIN` |

## Key Decisions (ADRs)

See `docs/adr/` for architecture decision records.

### ADR-001: SQLite as Default Database
- **Decision**: Use SQLite fallback when PostgreSQL is unavailable
- **Reason**: Easier local development, no server required
- **Consequence**: Limited concurrency, not for production multi-user

### ADR-002: Edge TTS as Default Provider
- **Decision**: Edge TTS is the default TTS provider
- **Reason**: Free, no API key needed, good Vietnamese voices
- **Consequence**: Requires internet connection, rate limits

### ADR-003: Parallel TTS Generation
- **Decision**: Run TTS segments in parallel with semaphore(5)
- **Reason**: 3-5x speed improvement over sequential
- **Consequence**: Higher memory usage, potential rate limits

### ADR-004: Translation Caching
- **Decision**: Cache translations in Redis + memory + disk
- **Reason**: Avoid re-translating identical segments, save API costs
- **Consequence**: Stale translations possible if source text changes

## File Structure Reference

```
backend/
├── main.py              → FastAPI app entry
├── config.py            → Pydantic settings
├── api/
│   ├── routes.py        → REST endpoints (20 endpoints)
│   ├── websocket.py     → Real-time progress
│   ├── auth.py          → JWT authentication
│   └── analytics.py     → Dashboard analytics
├── services/
│   ├── video.py         → Pipeline orchestrator (core)
│   ├── ffmpeg.py        → All FFmpeg operations
│   ├── transcription.py → WhisperX wrapper
│   ├── translation.py   → LLM translation
│   ├── tts.py           → TTS abstraction
│   ├── audio_mixer.py   → Audio mixing
│   ├── subtitles.py     → SRT/ASS generation
│   ├── cache.py         → Translation cache
│   ├── lipsync.py       → Lip-sync provider
│   └── storage.py       → S3/local storage
├── models/
│   └── database.py      → SQLAlchemy models
└── workers/
    ├── celery_app.py    → Celery config
    └── tasks.py         → Background tasks

frontend/
├── app/
│   ├── page.tsx         → Upload page
│   ├── layout.tsx       → Root layout
│   └── jobs/
│       ├── page.tsx     → Jobs list
│       └── [jobId]/     → Progress tracking
├── components/          → UI components
├── hooks/               → React hooks
└── lib/                 → Utilities
```

## Quality Standards

- **TypeScript strict mode** for frontend
- **Python type hints** for backend
- **Async FastAPI** for all endpoints
- **Error handling** for all pipeline steps
- **GPU auto-detection** with CPU fallback
- **Docker support** for deployment
