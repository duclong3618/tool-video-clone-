// Author: DUC LONG
// Year: 2026
// Project: VideoDubAI

"use client"

import { useEffect, useState, use } from "react"
import { useRouter } from "next/navigation"
import {
  CheckCircle,
  XCircle,
  Loader2,
  Download,
  FileText,
  RotateCcw,
} from "lucide-react"
import axios from "axios"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface JobStatus {
  type: string
  job_id: string
  video_id: string
  status: string
  current_step: string | null
  progress: number
  error_message: string | null
}

const STEPS = [
  { key: "extracting_audio", label: "Extracting Audio", icon: "🎵" },
  { key: "separating_vocals", label: "Separating Vocals", icon: "🎤" },
  { key: "transcribing", label: "Transcribing Speech", icon: "📝" },
  { key: "detecting_speakers", label: "Detecting Speakers", icon: "👥" },
  { key: "translating", label: "Translating to Vietnamese", icon: "🌐" },
  { key: "generating_voices", label: "Generating Vietnamese Voices", icon: "🗣️" },
  { key: "synchronizing_audio", label: "Synchronizing Audio", icon: "⏱️" },
  { key: "mixing_audio", label: "Mixing Audio Tracks", icon: "🎛️" },
  { key: "rendering_video", label: "Rendering Video", icon: "🎬" },
  { key: "completed", label: "Completed", icon: "✅" },
]

export default function JobPage({
  params,
}: {
  params: Promise<{ jobId: string }>
}) {
  const { jobId } = use(params)
  const router = useRouter()
  const [job, setJob] = useState<JobStatus | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const wsUrl = API_URL.replace("http", "ws")
    const ws = new WebSocket(`${wsUrl}/api/jobs/${jobId}/progress`)

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === "status" || data.type === "progress") {
          setJob((prev) => ({
            ...prev,
            ...data,
            type: "status",
          } as JobStatus))
        }
      } catch (e) {
        console.error("Failed to parse WS message:", e)
      }
    }

    ws.onerror = (e) => {
      console.error("WebSocket error:", e)
      // Fallback to polling
      pollJob()
    }

    return () => {
      ws.close()
    }
  }, [jobId])

  // Fallback polling
  const pollJob = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/jobs/${jobId}`)
      setJob({ type: "status", ...res.data })
    } catch (e) {
      console.error("Poll failed:", e)
    }
  }

  useEffect(() => {
    if (!connected && job?.status !== "completed" && job?.status !== "failed") {
      const interval = setInterval(pollJob, 3000)
      return () => clearInterval(interval)
    }
  }, [connected, job?.status])

  const currentStepIndex = job?.current_step
    ? STEPS.findIndex((s) => s.key === job.current_step)
    : -1

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Processing Video</h1>
        <p className="mt-2 text-muted-foreground">
          Job: {jobId.slice(0, 8)}...
        </p>
      </div>

      {/* Overall Progress */}
      <div className="rounded-lg border p-6">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-sm font-medium">Overall Progress</span>
          <span className="text-sm text-muted-foreground">
            {job?.progress?.toFixed(1) || 0}%
          </span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{ width: `${job?.progress || 0}%` }}
          />
        </div>

        {job?.status === "completed" && (
          <div className="mt-4 flex items-center gap-2 text-green-600">
            <CheckCircle className="h-5 w-5" />
            <span className="font-medium">Video processing complete!</span>
          </div>
        )}

        {job?.status === "failed" && (
          <div className="mt-4 rounded-md bg-destructive/10 p-3 text-destructive">
            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5" />
              <span className="font-medium">Processing failed</span>
            </div>
            {job.error_message && (
              <p className="mt-1 text-sm">{job.error_message}</p>
            )}
          </div>
        )}

        {!connected && job?.status !== "completed" && job?.status !== "failed" && (
          <p className="mt-2 text-xs text-muted-foreground">
            Reconnecting...
          </p>
        )}
      </div>

      {/* Step Progress */}
      <div className="rounded-lg border p-6">
        <h2 className="mb-4 text-lg font-semibold">Pipeline Steps</h2>
        <div className="space-y-3">
          {STEPS.map((step, index) => {
            const isCompleted =
              currentStepIndex > index ||
              job?.status === "completed"
            const isCurrent = job?.current_step === step.key
            const isPending = !isCompleted && !isCurrent

            return (
              <div
                key={step.key}
                className={`flex items-center gap-3 rounded-md p-3 ${
                  isCurrent
                    ? "bg-primary/10 border border-primary/20"
                    : isCompleted
                    ? "bg-green-50"
                    : "opacity-50"
                }`}
              >
                <span className="text-lg">{step.icon}</span>
                <span
                  className={`flex-1 text-sm ${
                    isCurrent
                      ? "font-medium"
                      : isCompleted
                      ? "text-green-700"
                      : ""
                  }`}
                >
                  {step.label}
                </span>
                {isCompleted && (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                )}
                {isCurrent && (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Actions */}
      {job?.status === "completed" && (
        <div className="flex gap-4">
          <a
            href={`${API_URL}/api/videos/${job.video_id}/download`}
            className="flex flex-1 items-center justify-center gap-2 rounded-md bg-primary px-6 py-3 text-primary-foreground hover:bg-primary/90"
          >
            <Download className="h-5 w-5" />
            Download Dubbed Video
          </a>
          <a
            href={`/videos/${job.video_id}/subtitles`}
            className="flex flex-1 items-center justify-center gap-2 rounded-md border px-6 py-3 hover:bg-muted"
          >
            <FileText className="h-5 w-5" />
            Edit Subtitles
          </a>
        </div>
      )}

      {job?.status === "failed" && (
        <button
          onClick={() => router.push("/")}
          className="flex w-full items-center justify-center gap-2 rounded-md border px-6 py-3 hover:bg-muted"
        >
          <RotateCcw className="h-5 w-5" />
          Start New Translation
        </button>
      )}
    </div>
  )
}
