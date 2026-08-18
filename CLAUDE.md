# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

# CLAUDE.md — VideoDubAI

## Quick Start

```bash
# Backend
source venv/Scripts/activate
uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

## Architecture

See `CONTEXT.md` for domain glossary and architecture overview.
See `docs/adr/` for architecture decision records.

## Key Files

- `backend/services/video.py` — Pipeline orchestrator (most important)
- `backend/services/ffmpeg.py` — All FFmpeg operations
- `backend/services/tts.py` — TTS abstraction (3 providers)
- `backend/services/translation.py` — LLM translation with caching
- `backend/api/routes.py` — All REST endpoints
- `frontend/app/page.tsx` — Main upload UI

## Commands

```bash
# Type check backend
python -m py_compile backend/main.py

# Type check frontend
cd frontend && npx tsc --noEmit

# Build frontend
cd frontend && npx next build

# Run tests (when available)
pytest
```

## Conventions

- Python: type hints, async/await, snake_case
- TypeScript: strict mode, React hooks, TailwindCSS
- API: REST endpoints under /api/, WebSocket for real-time
- Files: snake_case for Python, kebab-case for API routes
- Author header: All files start with `# Author: DUC LONG`

## Domain Language

Use terms from CONTEXT.md consistently:
- "segment" not "subtitle entry"
- "pipeline" not "workflow"
- "job" not "task"
- "speaker" not "voice profile"
- "diarization" not "speaker detection"

## Testing

- Backend: pytest with async support
- Frontend: Next.js build validation
- Integration: Test full pipeline with sample video

## Common Tasks

### Add new TTS provider
1. Create class in `backend/services/tts.py` extending `BaseTTSProvider`
2. Register in `PROVIDERS` dict
3. Add env var in `backend/config.py`
4. Update `.env.example`

### Add new API endpoint
1. Add route in `backend/api/routes.py`
2. Add schema in same file
3. Update OpenAPI docs (auto)

### Add new pipeline step
1. Add step in `backend/services/video.py` Pipeline class
2. Add to PipelineProgress.STEPS
3. Update frontend step display
