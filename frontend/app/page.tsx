// Author: DUC LONG
// Year: 2026
// Project: VideoDubAI

"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Upload, FileVideo, Loader2, X, Play, Volume2 } from "lucide-react"
import axios from "axios"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface UploadState {
  file: File | null
  uploading: boolean
  progress: number
  videoId: string | null
  error: string | null
}

interface JobOptions {
  sourceLanguage: string
  targetLanguage: string
  ttsProvider: string
  ttsVoice: string
  enableDiarization: boolean
  enableSubtitles: boolean
  burnSubtitles: boolean
  preserveBackground: boolean
  outputQuality: string
}

interface Voice {
  id: string
  name: string
  provider: string
}

export default function HomePage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragActive, setDragActive] = useState(false)
  const [upload, setUpload] = useState<UploadState>({
    file: null,
    uploading: false,
    progress: 0,
    videoId: null,
    error: null,
  })
  const [options, setOptions] = useState<JobOptions>({
    sourceLanguage: "zh",
    targetLanguage: "vi",
    ttsProvider: "edge",
    ttsVoice: "vi-VN-HoaiMyNeural",
    enableDiarization: false,
    enableSubtitles: true,
    burnSubtitles: false,
    preserveBackground: true,
    outputQuality: "high",
  })
  const [creating, setCreating] = useState(false)
  const [voices, setVoices] = useState<Voice[]>([])
  const [previewing, setPreviewing] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }, [])

  const handleFile = (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase()
    const allowed = ["mp4", "avi", "mov", "mkv", "webm", "flv", "wmv"]
    if (!ext || !allowed.includes(ext)) {
      setUpload((prev) => ({
        ...prev,
        error: `Unsupported file type: .${ext}. Allowed: ${allowed.join(", ")}`,
      }))
      return
    }
    setUpload({
      file,
      uploading: false,
      progress: 0,
      videoId: null,
      error: null,
    })
  }

  const handleUpload = async () => {
    if (!upload.file) return

    setUpload((prev) => ({ ...prev, uploading: true, error: null }))

    const formData = new FormData()
    formData.append("file", upload.file)

    try {
      const res = await axios.post(`${API_URL}/api/videos/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          const total = e.total ?? 0
          if (total > 0) {
            setUpload((prev) => ({
              ...prev,
              progress: Math.round((e.loaded * 100) / total),
            }))
          }
        },
      })

      setUpload((prev) => ({
        ...prev,
        videoId: res.data.video_id,
        uploading: false,
        progress: 100,
      }))
    } catch (err: any) {
      setUpload((prev) => ({
        ...prev,
        uploading: false,
        error: err.response?.data?.detail || "Upload failed",
      }))
    }
  }

  const handleStartJob = async () => {
    if (!upload.videoId) return

    setCreating(true)
    try {
      const res = await axios.post(`${API_URL}/api/jobs`, {
        video_id: upload.videoId,
        source_language: options.sourceLanguage,
        target_language: options.targetLanguage,
        tts_provider: options.ttsProvider,
        enable_diarization: options.enableDiarization,
        enable_subtitles: options.enableSubtitles,
        burn_subtitles: options.burnSubtitles,
        preserve_background: options.preserveBackground,
      })

      router.push(`/jobs/${res.data.job_id}`)
    } catch (err: any) {
      setUpload((prev) => ({
        ...prev,
        error: err.response?.data?.detail || "Failed to create job",
      }))
      setCreating(false)
    }
  }

  const resetUpload = () => {
    setUpload({ file: null, uploading: false, progress: 0, videoId: null, error: null })
  }

  // Load voices when TTS provider changes
  useEffect(() => {
    const loadVoices = async () => {
      try {
        const res = await axios.get(
          `${API_URL}/api/tts/voices?provider=${options.ttsProvider}`
        )
        setVoices(res.data.voices)
      } catch (e) {
        console.error("Failed to load voices:", e)
      }
    }
    loadVoices()
  }, [options.ttsProvider])

  const handlePreviewVoice = async (voiceId: string) => {
    setPreviewing(voiceId)
    try {
      const res = await axios.post(
        `${API_URL}/api/tts/preview`,
        null,
        {
          params: {
            text: "Xin chào, đây là giọng nói mẫu cho video đã dịch.",
            voice: voiceId,
            provider: options.ttsProvider,
          },
          responseType: "blob",
        }
      )
      const url = URL.createObjectURL(res.data)
      if (audioRef.current) {
        audioRef.current.pause()
      }
      audioRef.current = new Audio(url)
      audioRef.current.play()
    } catch (e) {
      console.error("Preview failed:", e)
    } finally {
      setPreviewing(null)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Upload Video</h1>
        <p className="mt-2 text-muted-foreground">
          Upload a Chinese video to translate and dub into Vietnamese
        </p>
      </div>

      {/* Upload Area */}
      <div
        className={`relative rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
          dragActive
            ? "border-primary bg-primary/5"
            : upload.videoId
            ? "border-green-500 bg-green-50"
            : "border-muted-foreground/25 hover:border-muted-foreground/50"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        {!upload.file ? (
          <>
            <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-4 text-lg font-medium">
              Drag & drop your video here
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              or click to browse
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              MP4, AVI, MOV, MKV, WebM — Max 500MB
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.avi,.mov,.mkv,.webm,.flv,.wmv"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="mt-4 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
            >
              Browse Files
            </button>
          </>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-3">
              <FileVideo className="h-8 w-8 text-primary" />
              <div className="text-left">
                <p className="font-medium">{upload.file.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(upload.file.size / (1024 * 1024)).toFixed(1)} MB
                </p>
              </div>
              <button
                onClick={resetUpload}
                className="ml-4 rounded-full p-1 hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Upload Progress */}
            {upload.uploading && (
              <div className="space-y-2">
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${upload.progress}%` }}
                  />
                </div>
                <p className="text-sm text-muted-foreground">
                  Uploading... {upload.progress}%
                </p>
              </div>
            )}

            {/* Upload Button */}
            {!upload.videoId && !upload.uploading && (
              <button
                onClick={handleUpload}
                className="rounded-md bg-primary px-6 py-2 text-sm text-primary-foreground hover:bg-primary/90"
              >
                Upload Video
              </button>
            )}

            {/* Success */}
            {upload.videoId && (
              <p className="text-sm text-green-600 font-medium">
                ✅ Video uploaded successfully!
              </p>
            )}
          </div>
        )}
      </div>

      {/* Error */}
      {upload.error && (
        <div className="rounded-md bg-destructive/10 p-4 text-destructive">
          {upload.error}
        </div>
      )}

      {/* Options */}
      {upload.videoId && (
        <div className="space-y-6 rounded-lg border p-6">
          <h2 className="text-lg font-semibold">Translation Options</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">Source Language</label>
              <select
                value={options.sourceLanguage}
                onChange={(e) =>
                  setOptions((prev) => ({ ...prev, sourceLanguage: e.target.value }))
                }
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="zh">Chinese (中文)</option>
                <option value="ja">Japanese (日本語)</option>
                <option value="ko">Korean (한국어)</option>
                <option value="en">English</option>
                <option value="auto">Auto-detect</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium">Target Language</label>
              <select
                value={options.targetLanguage}
                onChange={(e) =>
                  setOptions((prev) => ({ ...prev, targetLanguage: e.target.value }))
                }
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="vi">Vietnamese (Tiếng Việt)</option>
                <option value="en">English</option>
                <option value="zh">Chinese (中文)</option>
                <option value="ja">Japanese (日本語)</option>
                <option value="ko">Korean (한국어)</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium">TTS Engine</label>
              <select
                value={options.ttsProvider}
                onChange={(e) =>
                  setOptions((prev) => ({ ...prev, ttsProvider: e.target.value }))
                }
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="edge">Edge TTS (Free)</option>
                <option value="elevenlabs">ElevenLabs</option>
                <option value="qwen3tts">Qwen3-TTS</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium">Output Quality</label>
              <select
                value={options.outputQuality}
                onChange={(e) =>
                  setOptions((prev) => ({ ...prev, outputQuality: e.target.value }))
                }
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="low">Low (Fast)</option>
                <option value="medium">Medium</option>
                <option value="high">High (Best)</option>
              </select>
            </div>
          </div>

          {/* Voice Selection with Preview */}
          {voices.length > 0 && (
            <div>
              <label className="text-sm font-medium">Voice</label>
              <div className="mt-2 space-y-2">
                {voices.map((voice) => (
                  <div
                    key={voice.id}
                    className={`flex items-center justify-between rounded-md border p-3 cursor-pointer transition-colors ${
                      options.ttsVoice === voice.id
                        ? "border-primary bg-primary/5"
                        : "hover:bg-muted/50"
                    }`}
                    onClick={() => setOptions((prev) => ({ ...prev, ttsVoice: voice.id }))}
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="voice"
                        checked={options.ttsVoice === voice.id}
                        onChange={() => setOptions((prev) => ({ ...prev, ttsVoice: voice.id }))}
                        className="h-4 w-4"
                      />
                      <div>
                        <p className="text-sm font-medium">{voice.name}</p>
                        <p className="text-xs text-muted-foreground">{voice.provider}</p>
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handlePreviewVoice(voice.id)
                      }}
                      disabled={previewing === voice.id}
                      className="rounded-md border px-2 py-1 text-xs hover:bg-muted disabled:opacity-50"
                    >
                      {previewing === voice.id ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Volume2 className="h-3 w-3" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-3">
            <ToggleOption
              label="Speaker Diarization"
              description="Detect different speakers and assign different voices"
              checked={options.enableDiarization}
              onChange={(v) =>
                setOptions((prev) => ({ ...prev, enableDiarization: v }))
              }
            />
            <ToggleOption
              label="Generate Subtitles"
              description="Create SRT and ASS subtitle files"
              checked={options.enableSubtitles}
              onChange={(v) =>
                setOptions((prev) => ({ ...prev, enableSubtitles: v }))
              }
            />
            <ToggleOption
              label="Burn Subtitles"
              description="Hardcode subtitles into the video"
              checked={options.burnSubtitles}
              onChange={(v) =>
                setOptions((prev) => ({ ...prev, burnSubtitles: v }))
              }
            />
            <ToggleOption
              label="Preserve Background Audio"
              description="Keep music and sound effects from the original"
              checked={options.preserveBackground}
              onChange={(v) =>
                setOptions((prev) => ({ ...prev, preserveBackground: v }))
              }
            />
          </div>

          <button
            onClick={handleStartJob}
            disabled={creating}
            className="w-full rounded-md bg-primary px-6 py-3 text-lg font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {creating ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin" />
                Starting...
              </span>
            ) : (
              "🚀 Translate & Dub"
            )}
          </button>
        </div>
      )}
    </div>
  )
}

function ToggleOption({
  label,
  description,
  checked,
  onChange,
}: {
  label: string
  description: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between rounded-md border p-3 hover:bg-muted/50">
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded"
      />
    </label>
  )
}
