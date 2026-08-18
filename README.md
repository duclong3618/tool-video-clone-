<!--
Author: DUC LONG
Year: 2026
Project: VideoDubAI
-->

# 🎬 VideoDubAI — Dịch & Lồng tiếng video Trung Quốc → Tiếng Việt

Nền tảng web AI tự động chuyển đổi và lồng tiếng video từ tiếng Trung sang tiếng Việt, giữ nguyên nhạc nền và âm thanh gốc.

## ✨ Tính năng

- **Upload & Xử lý**: Upload video tiếng Trung → nhận video lồng tiếng tiếng Việt
- **WhisperX**: Nhận diện giọng nói chính xác đến từng từ
- **Dịch thông minh**: LLM dịch Trung → Việt tự nhiên, giữ ngữ cảnh
- **Nhiều giọng TTS**: TTS tiếng Việt với nhiều giọng lựa chọn
- **Giữ nhạc nền**: Giữ nguyên nhạc và hiệu ứng âm thanh gốc
- **Tạo phụ đề**: File SRT và ASS với hỗ trợ song ngữ
- **Phân biệt người nói**: Tùy chọn phát hiện nhiều người nói
- **Tiến độ real-time**: WebSocket cập nhật tiến độ trực tiếp
- **Sửa phụ đề**: Chỉnh sửa bản dịch và tạo lại giọng từng đoạn
- **Hỗ trợ GPU**: Tự động detect CUDA, fallback CPU

## 🏗️ Kiến trúc

```
frontend/          Next.js + TypeScript + TailwindCSS
├── app/           Trang: Upload, Tiến độ, Sửa phụ đề
├── components/    UI components
├── lib/           Utilities
└── hooks/         React hooks

backend/           Python FastAPI
├── api/           REST endpoints + WebSocket
├── services/      Logic xử lý chính
│   ├── video.py           Pipeline orchestrator
│   ├── ffmpeg.py          Xử lý video/audio
│   ├── transcription.py   WhisperX wrapper
│   ├── translation.py     Dịch Trung → Việt
│   ├── tts.py             Text-to-speech
│   ├── audio_mixer.py     Trộn audio
│   ├── subtitles.py       Tạo SRT/ASS
│   └── lipsync.py         Lip-sync (tùy chọn)
├── workers/       Celery background tasks
├── models/        SQLAlchemy models
└── utils/         Helpers

docker/            Dockerfiles và compose
storage/           Files tạm thời
```

## 🚀 Bắt đầu nhanh

### Cách 1: Docker (Khuyến nghị)

```bash
# Clone và cấu hình
cp .env.example .env
# Chỉnh .env với API key của bạn

# Khởi chạy tất cả services
cd docker
docker-compose up -d

# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Cách 2: Cài thủ công

```bash
# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # hoặc venv\Scripts\activate trên Windows

# Cài dependencies
pip install -r requirements.txt

# Copy và cấu hình
cp .env.example .env
# Chỉnh .env với cài đặt của bạn

# Chạy backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal mới — chạy frontend
cd frontend
npm install
npm run dev
```

### Cách 3: Script 1 lệnh

```bash
# Windows
run.bat

# Mac/Linux
./run.sh
```

## 🔧 Cấu hình

### Biến môi trường bắt buộc

| Biến | Mô tả | Mặc định |
|------|--------|----------|
| `DATABASE_URL` | PostgreSQL connection | `sqlite+aiosqlite:///./videodub.db` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API key (dịch) | - |
| `TTS_PROVIDER` | Engine TTS: `edge`, `elevenlabs`, `qwen3tts` | `edge` |

### Cấu hình tùy chọn

| Biến | Mô tả | Mặc định |
|------|--------|----------|
| `WHISPER_MODEL` | Model Whisper | `large-v3` |
| `WHISPER_DEVICE` | Thiết bị: `auto`, `cuda`, `cpu` | `auto` |
| `TRANSLATION_PROVIDER` | Backend dịch: `openai`, `ollama` | `openai` |
| `OLLAMA_MODEL` | Model Ollama | `qwen3:8b` |
| `PYANNOTE_AUTH_TOKEN` | HuggingFace token | - |
| `MAX_UPLOAD_SIZE_MB` | Kích thước upload tối đa | `500` |

### So sánh TTS Providers

| Provider | Chi phí | Chất lượng | Voice Cloning |
|----------|---------|------------|---------------|
| **Edge TTS** | Miễn phí | Tốt | Không |
| **ElevenLabs** | Trả phí | Xuất sắc | Có |
| **Qwen3-TTS** | Self-hosted | Tốt | Giới hạn |

### So sánh Translation Providers

| Provider | Chi phí | Ghi chú |
|----------|---------|---------|
| **OpenAI** | Trả phí | Chất lượng tốt nhất, GPT-4o |
| **Ollama** | Miễn phí (local) | Cần GPU, Qwen3-8B |

## 📡 API Reference

### Danh sách endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/videos/upload` | Upload video |
| `POST` | `/api/jobs` | Tạo job lồng tiếng |
| `GET` | `/api/jobs/{job_id}` | Xem trạng thái job |
| `GET` | `/api/videos/{video_id}` | Xem thông tin video |
| `GET` | `/api/videos/{video_id}/subtitles` | Xem phụ đề |
| `PUT` | `/api/videos/{video_id}/subtitles` | Cập nhật phụ đề |
| `POST` | `/api/videos/{video_id}/segments/{segment_id}/regenerate` | Tạo lại giọng |
| `GET` | `/api/videos/{video_id}/download` | Tải video kết quả |
| `GET` | `/api/tts/voices` | Danh sách giọng TTS |
| `POST` | `/api/tts/preview` | Nghe mẫu giọng |
| `GET` | `/api/languages` | Danh sách ngôn ngữ |
| `POST` | `/api/jobs/batch` | Tạo nhiều job |
| `POST` | `/api/jobs/{job_id}/retry` | Retry job thất bại |
| `POST` | `/api/auth/register` | Đăng ký |
| `POST` | `/api/auth/login` | Đăng nhập |
| `GET` | `/api/auth/me` | Thông tin user |
| `GET` | `/api/analytics/summary` | Thống kê |
| `WS` | `/api/jobs/{job_id}/progress` | Tiến độ real-time |

### Ví dụ: Upload & Xử lý

```bash
# 1. Upload video
curl -X POST http://localhost:8000/api/videos/upload \
  -F "file=@video_trung.wav"

# 2. Tạo job
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "ID_TỪ_BƯỚC_1",
    "source_language": "zh",
    "target_language": "vi",
    "tts_provider": "edge",
    "enable_subtitles": true,
    "preserve_background": true
  }'

# 3. Tải video kết quả
curl -O http://localhost:8000/api/videos/VIDEO_ID/download
```

## 🎯 Pipeline xử lý

```
Video tiếng Trung
    │
    ├─→ FFmpeg: Trích xuất audio (16kHz mono WAV)
    │
    ├─→ Demucs: Tách giọng khỏi nhạc nền (tùy chọn)
    │
    ├─→ WhisperX: Nhận diện lời thoại tiếng Trung
    │   └─→ Timestamp từng từ + phân câu
    │
    ├─→ pyannote: Phân biệt người nói (tùy chọn)
    │
    ├─→ LLM: Dịch Trung → Việt
    │   └─→ Dịch tự nhiên, giữ ngữ cảnh
    │
    ├─→ TTS: Tạo giọng tiếng Việt
    │   └─→ Điều chỉnh tốc độ phù hợp timing gốc
    │
    ├─→ Trộn audio: Kết hợp giọng Việt + nhạc nền
    │
    └─→ FFmpeg: Xuất video cuối cùng
        └─→ Video gốc + audio tiếng Việt + phụ đề (tùy chọn)
```

## 🐳 Docker Services

| Service | Port | Mô tả |
|---------|------|-------|
| `frontend` | 3000 | Giao diện web Next.js |
| `backend` | 8000 | API server FastAPI |
| `worker` | - | Celery background processor |
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis cache/broker |
| `minio` | 9000/9001 | S3-compatible storage |

## 🛠️ Phát triển

### Cấu trúc project

```
videodub/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Settings (Pydantic)
│   ├── api/
│   │   ├── routes.py         # REST endpoints
│   │   ├── websocket.py      # WebSocket handler
│   │   ├── auth.py           # JWT authentication
│   │   └── analytics.py      # Dashboard analytics
│   ├── services/
│   │   ├── video.py          # Pipeline orchestrator
│   │   ├── ffmpeg.py         # FFmpeg wrapper
│   │   ├── transcription.py  # WhisperX/faster-whisper
│   │   ├── translation.py    # LLM translation
│   │   ├── tts.py            # TTS providers
│   │   ├── audio_mixer.py    # Audio mixing
│   │   ├── subtitles.py      # Subtitle generation
│   │   ├── cache.py          # Translation cache
│   │   ├── lipsync.py        # Lip-sync (optional)
│   │   └── storage.py        # S3/local storage
│   ├── workers/
│   │   ├── celery_app.py     # Celery config
│   │   └── tasks.py          # Background tasks
│   ├── models/
│   │   └── database.py       # SQLAlchemy models
│   └── utils/
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Trang upload
│   │   ├── layout.tsx        # Root layout
│   │   └── jobs/
│   │       ├── page.tsx      # Danh sách jobs
│   │       └── [jobId]/
│   │           └── page.tsx  # Tiến độ job
│   ├── components/
│   ├── hooks/
│   └── lib/
├── .agents/skills/           # Matt Pocock skills
├── docs/adr/                 # Architecture Decision Records
├── CLAUDE.md                 # Agent instructions
├── CONTEXT.md                # Shared language
├── docker/
├── storage/
├── requirements.txt
├── .env.example
├── run.bat                   # Script chạy 1 lệnh (Windows)
├── run.sh                    # Script chạy 1 lệnh (Linux/Mac)
└── README.md
```

### Thêm TTS Provider mới

1. Tạo class trong `backend/services/tts.py`:

```python
class MyNewTTSProvider(BaseTTSProvider):
    async def synthesize(self, text: str, output_path: str, voice: str, speed: float) -> str:
        # Triển khai
        return output_path

    def list_voices(self) -> list[dict]:
        return [{"id": "my_voice", "name": "My Voice", "provider": "my"}]
```

2. Đăng ký trong `PROVIDERS`:

```python
PROVIDERS["my_tts"] = MyNewTTSProvider
```

3. Set `TTS_PROVIDER=my_tts` trong `.env`

### Thêm Translation Provider mới

1. Thêm method trong `TranslationService`:

```python
async def _translate_my_provider(self, user_prompt: str) -> str:
    # Triển khai
    return translated_text
```

2. Thêm check trong `translate_segment()`

3. Set `TRANSLATION_PROVIDER=my_provider` trong `.env`

## 📝 License

MIT License

## 🙏 Cảm ơn

- [pyVideoTrans](https://github.com/jianchang512/pyvideotrans) — Pipeline inspiration
- [videoTranslator](https://github.com/Felixdiamond/videoTranslator) — Architecture reference
- [WhisperX](https://github.com/m-bain/whisperx) — Speech recognition
- [Edge TTS](https://github.com/rany2/edge-tts) — Free Vietnamese TTS
- [Demucs](https://github.com/facebookresearch/demucs) — Vocal separation
- [Matt Pocock Skills](https://github.com/mattpocock/skills) — Agent skills
