// Author: DUC LONG
// Year: 2026
// Project: VideoDubAI

"use client"

import { useEffect, useState, use } from "react"
import { Save, RotateCcw, Plus, Trash2, Loader2 } from "lucide-react"
import axios from "axios"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface Segment {
  segment_id: string
  index: number
  start_time: number
  end_time: number
  original_text: string
  translated_text: string
  speaker: string | null
  status: string
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 100)
  return `${h.toString().padStart(2, "0")}:${m
    .toString()
    .padStart(2, "0")}:${s.toString().padStart(2, "0")}.${ms
    .toString()
    .padStart(2, "0")}`
}

function parseTime(timeStr: string): number {
  const parts = timeStr.split(":")
  if (parts.length !== 3) return 0
  const h = parseInt(parts[0]) || 0
  const m = parseInt(parts[1]) || 0
  const sParts = parts[2].split(".")
  const s = parseInt(sParts[0]) || 0
  const ms = parseInt(sParts[1]) || 0
  return h * 3600 + m * 60 + s + ms / 100
}

export default function SubtitleEditorPage({
  params,
}: {
  params: Promise<{ videoId: string }>
}) {
  const { videoId } = use(params)
  const [segments, setSegments] = useState<Segment[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [regenerating, setRegenerating] = useState<string | null>(null)

  useEffect(() => {
    loadSubtitles()
  }, [videoId])

  const loadSubtitles = async () => {
    try {
      const res = await axios.get(
        `${API_URL}/api/videos/${videoId}/subtitles`
      )
      setSegments(res.data)
    } catch (e) {
      console.error("Failed to load subtitles:", e)
    } finally {
      setLoading(false)
    }
  }

  const updateSegment = (
    index: number,
    field: keyof Segment,
    value: string | number
  ) => {
    setSegments((prev) =>
      prev.map((seg, i) =>
        i === index ? { ...seg, [field]: value } : seg
      )
    )
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await axios.put(`${API_URL}/api/videos/${videoId}/subtitles`, segments)
    } catch (e) {
      console.error("Failed to save:", e)
    } finally {
      setSaving(false)
    }
  }

  const handleRegenerate = async (segmentId: string) => {
    setRegenerating(segmentId)
    try {
      await axios.post(
        `${API_URL}/api/videos/${videoId}/segments/${segmentId}/regenerate`,
        {}
      )
    } catch (e) {
      console.error("Failed to regenerate:", e)
    } finally {
      setRegenerating(null)
    }
  }

  const addSegment = () => {
    const lastSeg = segments[segments.length - 1]
    const newStart = lastSeg ? lastSeg.end_time : 0
    setSegments((prev) => [
      ...prev,
      {
        segment_id: `new-${Date.now()}`,
        index: prev.length,
        start_time: newStart,
        end_time: newStart + 2,
        original_text: "",
        translated_text: "",
        speaker: "speaker_01",
        status: "pending",
      },
    ])
  }

  const removeSegment = (index: number) => {
    setSegments((prev) => prev.filter((_, i) => i !== index))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Subtitle Editor</h1>
          <p className="text-sm text-muted-foreground">
            Edit translations and regenerate voices
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={addSegment}
            className="flex items-center gap-1 rounded-md border px-3 py-2 text-sm hover:bg-muted"
          >
            <Plus className="h-4 w-4" />
            Add Segment
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {segments.map((seg, index) => (
          <div
            key={seg.segment_id}
            className="rounded-lg border p-4 space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-muted-foreground">
                  #{index + 1}
                </span>
                <span className="text-xs text-muted-foreground">
                  {seg.speaker || "speaker_01"}
                </span>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => handleRegenerate(seg.segment_id)}
                  disabled={regenerating === seg.segment_id}
                  className="flex items-center gap-1 rounded border px-2 py-1 text-xs hover:bg-muted disabled:opacity-50"
                >
                  {regenerating === seg.segment_id ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <RotateCcw className="h-3 w-3" />
                  )}
                  Regenerate Voice
                </button>
                <button
                  onClick={() => removeSegment(index)}
                  className="rounded border p-1 text-destructive hover:bg-destructive/10"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            </div>

            {/* Time inputs */}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={formatTime(seg.start_time)}
                onChange={(e) =>
                  updateSegment(index, "start_time", parseTime(e.target.value))
                }
                className="w-28 rounded border px-2 py-1 font-mono text-xs"
              />
              <span className="text-muted-foreground">→</span>
              <input
                type="text"
                value={formatTime(seg.end_time)}
                onChange={(e) =>
                  updateSegment(index, "end_time", parseTime(e.target.value))
                }
                className="w-28 rounded border px-2 py-1 font-mono text-xs"
              />
            </div>

            {/* Text inputs */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">
                  Original (Chinese)
                </label>
                <textarea
                  value={seg.original_text}
                  onChange={(e) =>
                    updateSegment(index, "original_text", e.target.value)
                  }
                  rows={2}
                  className="mt-1 w-full rounded border px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">
                  Vietnamese Translation
                </label>
                <textarea
                  value={seg.translated_text}
                  onChange={(e) =>
                    updateSegment(index, "translated_text", e.target.value)
                  }
                  rows={2}
                  className="mt-1 w-full rounded border px-3 py-2 text-sm"
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {segments.length === 0 && (
        <div className="py-12 text-center text-muted-foreground">
          No subtitle segments found.
        </div>
      )}
    </div>
  )
}
