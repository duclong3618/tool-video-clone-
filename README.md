<!--
Author: DUC LONG
Year: 2026
Project: VideoDubAI
-->

# 🎬 VideoDubAI — Chinese → Vietnamese Video Dubbing

AI-powered web application that automatically translates Chinese videos into Vietnamese with dubbed audio, preserving background music and sound effects.

## ✨ Features

- **Upload & Process**: Upload Chinese videos and get Vietnamese dubbed output
- **WhisperX Transcription**: Industry-leading speech recognition with word-level timestamps
- **Intelligent Translation**: LLM-powered Chinese → Vietnamese translation with context awareness
- **Multi-Voice TTS**: Vietnamese text-to-speech with multiple voice options
- **Background Preservation**: Keeps original music and sound effects
- **Subtitle Generation**: SRT and ASS subtitle files with bilingual support
- **Speaker Diarization**: Optional speaker detection for multi-speaker videos
- **Real-time Progress**: WebSocket-powered live progress updates
- **Subtitle Editor**: Edit translations and regenerate individual segments
- **GPU Support**: Automatic CUDA detection with CPU fallback

## 🏗️ Architecture

```
frontend/          Next.js + TypeScript + TailwindCSS + shadcn/ui
├── app/           Pages: Upload, Job Progress, Subtitle Editor
├── components/    Reusable UI components
├── lib/           Utilities and API client
└── hooks/         Custom React hooks

backend/           Python FastAPI
├── api/           REST endpoints + WebSocket
├── services/      Core business logic
│   ├── video.py           Pipeline orchestrator
│   ├── ffmpeg.py          Video/audio processing
│   ├── transcription.py   WhisperX wrapper
│   ├── translation.py     Chinese→Vietnamese translation
│   ├── tts.py             Text-to-speech providers
│   ├── audio_mixer.py     Audio mixing
│   ├── subtitles.py       SRT/ASS generation
│   └── lipsync.py         Lip-sync (optional)
├── workers/       Celery background tasks
├── models/        SQLAlchemy database models
└── utils/         Helpers

docker/            Dockerfiles and compose
storage/           Temporary processing files
```

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys

# Start all services
cd docker
docker-compose up -d

# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Manual Setup

#### Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install WhisperX (optional, for best transcription)
pip install git+https://github.com/m-bain/whisperx.git

# Install Demucs (optional, for vocal separation)
pip install demucs

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Start the server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Option 3: Start Services

```bash
# Start PostgreSQL and Redis (if not using Docker)
# ...

# Backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Celery Worker (for background processing)
celery -A backend.workers.celery_app worker -l info -c 1

# Frontend
cd frontend && npm run dev
```

## 🔧 Configuration

### Required Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/videodub` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API key (for translation) | - |
| `TTS_PROVIDER` | TTS engine: `edge`, `elevenlabs`, `qwen3tts` | `edge` |

### Optional Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `WHISPER_MODEL` | Whisper model size | `large-v3` |
| `WHISPER_DEVICE` | Compute device: `auto`, `cuda`, `cpu` | `auto` |
| `TRANSLATION_PROVIDER` | Translation backend: `openai`, `ollama` | `openai` |
| `OLLAMA_MODEL` | Ollama model name | `qwen3:8b` |
| `PYANNOTE_AUTH_TOKEN` | HuggingFace token for diarization | - |
| `MAX_UPLOAD_SIZE_MB` | Maximum upload file size | `500` |

### TTS Providers

| Provider | Cost | Quality | Voice Cloning |
|----------|------|---------|---------------|
| **Edge TTS** | Free | Good | No |
| **ElevenLabs** | Paid | Excellent | Yes |
| **Qwen3-TTS** | Self-hosted | Good | Limited |

### Translation Providers

| Provider | Cost | Notes |
|----------|------|-------|
| **OpenAI** | Paid | Best quality, GPT-4o recommended |
| **Ollama** | Free (local) | Requires GPU, Qwen3-8B recommended |

## 📡 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/videos/upload` | Upload video file |
| `POST` | `/api/jobs` | Create dubbing job |
| `GET` | `/api/jobs/{job_id}` | Get job status |
| `GET` | `/api/videos/{video_id}` | Get video details |
| `GET` | `/api/videos/{video_id}/subtitles` | Get subtitles |
| `PUT` | `/api/videos/{video_id}/subtitles` | Update subtitles |
| `POST` | `/api/videos/{video_id}/segments/{segment_id}/regenerate` | Regenerate TTS |
| `GET` | `/api/videos/{video_id}/download` | Download dubbed video |
| `WS` | `/api/jobs/{job_id}/progress` | Real-time progress |

### Example: Upload & Process

```bash
# 1. Upload video
curl -X POST http://localhost:8000/api/videos/upload \
  -F "file=@chinese_video.mp4"

# Response: {"video_id": "abc-123", "filename": "chinese_video.mp4"}

# 2. Create job
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "abc-123",
    "source_language": "zh",
    "target_language": "vi",
    "tts_provider": "edge",
    "enable_subtitles": true,
    "preserve_background": true
  }'

# Response: {"job_id": "def-456", "status": "queued"}

# 3. Monitor progress via WebSocket
wscat -c ws://localhost:8000/api/jobs/def-456/progress

# 4. Download when complete
curl -O http://localhost:8000/api/videos/abc-123/download
```

## 🎯 Processing Pipeline

```
Chinese MP4
    │
    ├─→ FFmpeg: Extract audio (16kHz mono WAV)
    │
    ├─→ Demucs: Separate vocals from background (optional)
    │
    ├─→ WhisperX: Transcribe Chinese speech
    │   └─→ Word-level timestamps + sentence segmentation
    │
    ├─→ pyannote: Speaker diarization (optional)
    │
    ├─→ LLM: Translate Chinese → Vietnamese
    │   └─→ Context-aware, natural Vietnamese output
    │
    ├─→ TTS: Generate Vietnamese voices
    │   └─→ Speed adjustment to match original timing
    │
    ├─→ Audio Mixing: Combine Vietnamese + background
    │
    └─→ FFmpeg: Export final video
        └─→ Original video + Vietnamese audio + optional subtitles
```

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 3000 | Next.js web interface |
| `backend` | 8000 | FastAPI API server |
| `worker` | - | Celery background processor |
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis cache/broker |
| `minio` | 9000/9001 | S3-compatible file storage |

## 🛠️ Development

### Project Structure

```
videodub/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Settings (Pydantic)
│   ├── api/
│   │   ├── routes.py         # REST endpoints
│   │   └── websocket.py      # WebSocket handler
│   ├── services/
│   │   ├── video.py          # Pipeline orchestrator
│   │   ├── ffmpeg.py         # FFmpeg wrapper
│   │   ├── transcription.py  # WhisperX/faster-whisper
│   │   ├── translation.py    # LLM translation
│   │   ├── tts.py            # TTS providers
│   │   ├── audio_mixer.py    # Audio mixing
│   │   ├── subtitles.py      # Subtitle generation
│   │   └── lipsync.py        # Lip-sync (optional)
│   ├── workers/
│   │   ├── celery_app.py     # Celery config
│   │   └── tasks.py          # Background tasks
│   ├── models/
│   │   └── database.py       # SQLAlchemy models
│   └── utils/
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Upload page
│   │   ├── layout.tsx        # Root layout
│   │   ├── globals.css       # Global styles
│   │   └── jobs/
│   │       ├── page.tsx      # Jobs list
│   │       └── [jobId]/
│   │           └── page.tsx  # Job progress
│   ├── components/
│   ├── lib/
│   └── hooks/
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── storage/                  # Temp processing files
├── requirements.txt
├── .env.example
└── README.md
```

### Adding a New TTS Provider

1. Create a new class in `backend/services/tts.py`:

```python
class MyNewTTSProvider(BaseTTSProvider):
    async def synthesize(self, text: str, output_path: str, voice: str, speed: float) -> str:
        # Implementation
        return output_path

    def list_voices(self) -> list[dict]:
        return [{"id": "my_voice", "name": "My Voice", "provider": "my"}]
```

2. Register in `PROVIDERS` dict:

```python
PROVIDERS["my_tts"] = MyNewTTSProvider
```

3. Set `TTS_PROVIDER=my_tts` in `.env`

### Adding a New Translation Provider

1. Add a method to `TranslationService` in `backend/services/translation.py`:

```python
async def _translate_my_provider(self, user_prompt: str) -> str:
    # Implementation
    return translated_text
```

2. Add provider check in `translate_segment()`

3. Set `TRANSLATION_PROVIDER=my_provider` in `.env`

## 📝 License

MIT License

## 🙏 Acknowledgments

- [pyVideoTrans](https://github.com/jianchang512/pyvideotrans) — Pipeline inspiration
- [videoTranslator](https://github.com/Felixdiamond/videoTranslator) — Architecture reference
- [WhisperX](https://github.com/m-bain/whisperx) — Speech recognition
- [Edge TTS](https://github.com/rany2/edge-tts) — Free Vietnamese TTS
- [Demucs](https://github.com/facebookresearch/demucs) — Vocal separation
