<!--
Author: DUC LONG
Year: 2026
Project: VideoDubAI
-->

# 🎬 Hướng dẫn sử dụng VideoDubAI

## Dịch & Lồng tiếng video Trung Quốc → Tiếng Việt

---

## 📋 Mục lục

1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Cài đặt](#2-cài-đặt)
3. [Cấu hình](#3-cấu-hình)
4. [Sử dụng trên trình duyệt](#4-sử-dụng-trên-trình-duyệt)
5. [Sử dụng qua API](#5-sử-dụng-qua-api)
6. [Chỉnh sửa phụ đề](#6-chỉnh-sửa-phụ-đề)
7. [Cấu hình TTS & Dịch](#7-cấu-hình-tts--dịch)
8. [Xử lý sự cố](#8-xử-lý-sự-cố)
9. [Hỏi đáp](#9-hỏi-đáp)

---

## 1. Yêu cầu hệ thống

### Tối thiểu (chạy CPU)
- RAM: 8GB
- Ổ trống: 10GB
- Python 3.11+
- FFmpeg

### Khuyến nghị (có GPU)
- RAM: 16GB+
- GPU NVIDIA: RTX 3060 trở lên (VRAM 8GB+)
- Ổ trống: 20GB
- CUDA 12.x

### Nếu dùng Docker
- Docker Desktop hoặc Docker Engine
- Docker Compose v2

---

## 2. Cài đặt

### Cách A: Docker (dễ nhất, khuyến nghị)

```bash
# Bước 1: Vào thư mục project
cd videodub

# Bước 2: Tạo file cấu hình từ mẫu
cp .env.example .env

# Bước 3: Chỉnh file .env (xem phần 3)

# Bước 4: Khởi chạy
cd docker
docker-compose up -d
```

Kiểm tra đã chạy chưa:
```bash
docker-compose ps
```

Tất cả services phải hiển thị `Up`:
```
videodub-postgres-1    Up
videodub-redis-1       Up
videodub-backend-1     Up
videodub-worker-1      Up
videodub-frontend-1    Up
```

Mở trình duyệt:
- 🌐 Frontend: **http://localhost:3000**
- 📡 API Docs: **http://localhost:8000/docs**

### Cách B: Cài thủ công

```bash
# ── Bước 1: Tạo virtual environment ──────────
python -m venv venv

# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# ── Bước 2: Cài dependencies ─────────────────
pip install -r requirements.txt

# ── Bước 3: Cài WhisperX (tùy chọn, tốt nhất) ──
pip install git+https://github.com/m-bain/whisperx.git

# ── Bước 4: Cài Demucs (tùy chọn, tách giọng) ──
pip install demucs

# ── Bước 5: Tạo file cấu hình ───────────────
cp .env.example .env

# ── Bước 6: Chỉnh file .env (xem phần 3) ────

# ── Bước 7: Chạy backend ─────────────────────
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# ── Bước 8: Terminal mới — chạy frontend ─────
cd frontend
npm install
npm run dev
```

---

## 3. Cấu hình

### File `.env` — Bắt buộc phải chỉnh

```env
# ════════════════════════════════════════════════
# DỊCH THUẬT (chọn 1 trong 2)
# ════════════════════════════════════════════════

# ── Cách 1: OpenAI (trả phí, chất lượng tốt) ──
TRANSLATION_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxx
TRANSLATION_MODEL=gpt-4o-mini

# ── Cách 2: Ollama (miễn phí, chạy local) ─────
# TRANSLATION_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=qwen3:8b

# ════════════════════════════════════════════════
# GIỌNG NÓI (TTS)
# ════════════════════════════════════════════════

# ── Edge TTS: Miễn phí, không cần key ─────────
TTS_PROVIDER=edge

# ── ElevenLabs: Trả phí, chất lượng cao ──────
# TTS_PROVIDER=elevenlabs
# ELEVENLABS_API_KEY=xxxxxxxxxxxxxxxxxx

# ════════════════════════════════════════════════
# CẤU HÌNH KHÁC (có thể giữ mặc định)
# ════════════════════════════════════════════════

# Whisper model (large-v3 tốt nhất, tiny nhanh nhất)
WHISPER_MODEL=large-v3
WHISPER_DEVICE=auto

# Database (giữ nguyên nếu dùng Docker)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/videodub

# Redis
REDIS_URL=redis://localhost:6379/0
```

### Cách lấy API key

**OpenAI:**
1. Vào https://platform.openai.com/api-keys
2. Đăng nhập
3. Nhấn "Create new secret key"
4. Copy key dán vào `.env`

**ElevenLabs:**
1. Vào https://elevenlabs.io
2. Đăng ký tài khoản
3. Vào Profile → API Keys
4. Copy key dán vào `.env`

**Ollama (miễn phí):**
```bash
# Cài Ollama
curl -fsSL https://ollama.com/install.sh | sh   # Linux
# Hoặc tải từ https://ollama.com cho Windows/Mac

# Tải model
ollama pull qwen3:8b

# Kiểm tra
ollama list
```

---

## 4. Sử dụng trên trình duyệt

### Bước 1: Mở trang chủ

Truy cập **http://localhost:3000**

### Bước 2: Upload video

```
┌─────────────────────────────────────┐
│                                     │
│   🎬 Drag & drop video vào đây     │
│                                     │
│   Hoặc nhấn Browse Files            │
│                                     │
│   MP4, AVI, MOV, MKV — Max 500MB   │
└─────────────────────────────────────┘
```

- Kéo thả file video vào ô
- Hoặc nhấn **Browse Files** để chọn
- Chờ upload xong → nhấn **Upload Video**

### Bước 3: Chọn tùy chọn

| Tùy chọn | Giải thích | Khuyến nghị |
|----------|------------|--------------|
| Source Language | Ngôn ngữ nguồn | Giữ `Chinese` |
| Target Language | Ngôn ngữ đích | Giữ `Vietnamese` |
| TTS Engine | Công cụ tạo giọng | `Edge TTS (Free)` |
| Speaker Diarization | Phân biệt người nói | Bật nếu nhiều người |
| Generate Subtitles | Tạo file phụ đề | ✅ Bật |
| Burn Subtitles | Đốt phụ đề vào video | Tuỳ chọn |
| Preserve Background | Giữ nhạc nền | ✅ Bật |

### Bước 4: Bắt đầu

Nhấn **🚀 Translate & Dub**

Quá trình xử lý:

```
🔄 Extracting Audio        0%
🔄 Separating Vocals       0%
🔄 Transcribing            0%
🔄 Translating             0%
🔄 Generating Voices       0%
🔄 Mixing Audio            0%
🔄 Rendering Video         0%
```

Progress cập nhật **real-time** qua WebSocket.

### Bước 5: Tải kết quả

Khi hoàn tất, nhấn:

- **📥 Download Dubbed Video** — video đã lồng tiếng tiếng Việt
- **📝 Edit Subtitles** — chỉnh sửa phụ đề

---

## 5. Sử dụng qua API

### Upload video

```bash
curl -X POST http://localhost:8000/api/videos/upload \
  -F "file=@video_trung_quoc.mp4"
```

Trả về:
```json
{
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "video_trung_quoc.mp4"
}
```

### Tạo job dịch & lồng tiếng

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "source_language": "zh",
    "target_language": "vi",
    "tts_provider": "edge",
    "enable_subtitles": true,
    "preserve_background": true
  }'
```

Trả về:
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440001",
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

### Kiểm tra tiến độ

```bash
curl http://localhost:8000/api/jobs/660e8400-e29b-41d4-a716-446655440001
```

Trả về:
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "processing",
  "current_step": "translating",
  "progress": 45.5
}
```

### Theo dõi real-time qua WebSocket

```bash
# Dùng websocat
pip install websocket-client
python -c "
import websocket
ws = websocket.create_connection('ws://localhost:8000/api/jobs/JOB_ID/progress')
while True:
    print(ws.recv())
"
```

Hoặc dùng trang web tự động theo dõi.

### Tải video kết quả

```bash
curl -O http://localhost:8000/api/videos/VIDEO_ID/download
```

### Xem phụ đề

```bash
curl http://localhost:8000/api/videos/VIDEO_ID/subtitles
```

---

## 6. Chỉnh sửa phụ đề

### Truy cập trang chỉnh sửa

Sau khi video xử lý xong, nhấn **Edit Subtitles**
hoặc truy cập: `http://localhost:3000/videos/VIDEO_ID/subtitles`

### Chỉnh sửa

```
┌──────────────────────────────────────────────────────┐
│ #1  speaker_01                           [🔄 Regen]  │
│                                                      │
│ 00:00:12.42 → 00:00:15.81                           │
│                                                      │
│ ┌─ Original (Chinese) ─┐  ┌─ Vietnamese ──────────┐ │
│ │ 你今天为什么来到这里？  │  │ Hôm nay tại sao bạn    │ │
│ │                        │  │ lại đến đây?          │ │
│ └────────────────────────┘  └──────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

- **Sửa text tiếng Việt** — chỉnh câu dịch cho tự nhiên
- **Sửa thời gian** — chỉnh start/end time (định dạng HH:MM:SS.ms)
- **🔄 Regenerate Voice** — tạo lại giọng cho đoạn này
- **🗑️ Xóa segment** — xóa đoạn phụ đề
- **➕ Add Segment** — thêm đoạn mới

Nhấn **💾 Save** khi xong.

---

## 7. Cấu hình TTS & Dịch

### So sánh TTS providers

| Provider | Chi phí | Chất lượng | Voice Cloning | Ngôn ngữ |
|----------|---------|------------|---------------|----------|
| **Edge TTS** | Miễn phí | ⭐⭐⭐⭐ | Không | 70+ ngôn ngữ |
| **ElevenLabs** | Trả phí | ⭐⭐⭐⭐⭐ | Có | 29 ngôn ngữ |
| **Qwen3-TTS** | Local | ⭐⭐⭐⭐ | Giới hạn | Nhiều |

### Voices tiếng Việt có sẵn

**Edge TTS:**
- `vi-VN-HoaiMyNeural` — Nữ (mặc định)
- `vi-VN-NamMinhNeural` — Nam

**ElevenLabs:**
- Tùy chỉnh theo voice ID bạn tạo

### Speaker-to-Voice mapping

Khi bật Speaker Diarization:
- `speaker_01` → Giọng nữ Việt (mặc định)
- `speaker_02` → Giọng nam Việt
- `speaker_03` → Giọng nữ Việt (lặp lại)

Bạn có thể chỉnh mapping trong `backend/services/tts.py`:

```python
DEFAULT_SPEAKER_VOICE_MAP = {
    "speaker_01": "vi-VN-HoaiMyNeural",
    "speaker_02": "vi-VN-NamMinhNeural",
    "speaker_03": "vi-VN-HoaiMyNeural",
}
```

### So sánh Translation providers

| Provider | Chi phí | Chất lượng | Yêu cầu |
|----------|---------|------------|----------|
| **OpenAI** | $0.15/1M tokens | ⭐⭐⭐⭐⭐ | API key |
| **Ollama** | Miễn phí | ⭐⭐⭐⭐ | GPU 8GB+ |

---

## 8. Xử lý sự cố

### Lỗi thường gặp

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-------------|-----------|
| `Unsupported file type` | Sai định dạng | Dùng .mp4, .avi, .mov, .mkv |
| `File too large` | File > 500MB | Nén video hoặc tăng `MAX_UPLOAD_SIZE_MB` |
| `No transcription backend` | Chưa cài Whisper | `pip install faster-whisper` |
| `WhisperX alignment failed` | Model chưa tải | Chờ tải hoặc set `WHISPER_MODEL=base` |
| `OpenAI translation failed` | Sai API key | Kiểm tra `OPENAI_API_KEY` trong `.env` |
| `Ollama translation failed` | Ollama chưa chạy | `ollama serve` trong terminal mới |
| `Edge TTS error` | Mạng | Kiểm tra kết nối internet |
| `FFmpeg not found` | Chưa cài FFmpeg | `apt install ffmpeg` hoặc `brew install ffmpeg` |
| `GPU out of memory` | VRAM không đủ | Set `WHISPER_DEVICE=cpu` trong `.env` |
| `Connection refused` | Backend chưa chạy | Kiểm tra `uvicorn` đang chạy |
| `WebSocket closed` | Mất kết nối | Fallback sang polling tự động |

### Kiểm tra health

```bash
curl http://localhost:8000/health
# Trả về: {"status": "ok", "app": "VideoDubAI"}
```

### Xem logs

```bash
# Docker
docker-compose logs -f backend
docker-compose logs -f worker

# Thủ công — logs hiển thị trên terminal đang chạy uvicorn
```

### Reset tất cả

```bash
# Dừng và xóa containers
cd docker
docker-compose down -v

# Xóa storage
rm -rf storage/*

# Chạy lại
docker-compose up -d
```

---

## 9. Hỏi đáp

### Video nào dùng được?
- Định dạng: MP4, AVI, MOV, MKV, WebM, FLV, WMV
- Kích thước tối đa: 500MB (có thể thay đổi trong `.env`)
- Thời lượng khuyên nghị: < 30 phút

### Tốc độ xử lý?
- Video 5 phút: ~5-10 phút (có GPU)
- Video 30 phút: ~30-60 phút (có GPU)
- CPU sẽ chậm hơn 3-5 lần

### Chất lượng lồng tiếng?
- Edge TTS: Tự nhiên, phù hợpmost use cases
- ElevenLabs: Cao cấp, giống người thật nhất
- Có thể chỉnh lại text trong Subtitle Editor

### Hỗ trợ ngôn ngữ nào?
- **Nguồn:** Tiếng Trung (zh) — mặc định
- **Đích:** Tiếng Việt (vi) — mặc định
- Có thể mở rộng sang ngôn ngữ khác

### Cần GPU không?
- **Không bắt buộc** — CPU vẫn chạy được
- GPU giúp nhanh hơn 3-5x
- Auto-detect GPU trong code

### Dữ liệu có an toàn?
- Chạy local trên máy bạn
- Không gửi data lên cloud (trừ API translation)
- API keys lưu trong `.env`, không commit lên git

---

## Liên hệ & Hỗ trợ

- 📖 Docs: http://localhost:8000/docs (Swagger UI)
- 🐛 Issues: Tạo issue trên GitHub
- 💬 Discussion: GitHub Discussions

---

> **Mẹo:** Bắt đầu với video ngắn (1-2 phút) để test, sau đó dùng video dài hơn.
