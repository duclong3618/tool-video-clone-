// Author: DUC LONG
// Year: 2026
// Project: VideoDubAI

"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Clock, CheckCircle, XCircle, Loader2 } from "lucide-react"

interface Job {
  job_id: string
  video_id: string
  status: string
  current_step: string | null
  progress: number
  created_at: string
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // For MVP, this is a placeholder
    // In production, we'd fetch from /api/jobs
    setLoading(false)
  }, [])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case "failed":
        return <XCircle className="h-5 w-5 text-destructive" />
      case "processing":
        return <Loader2 className="h-5 w-5 animate-spin text-primary" />
      default:
        return <Clock className="h-5 w-5 text-muted-foreground" />
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold">Processing Jobs</h1>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="rounded-lg border p-12 text-center">
          <p className="text-muted-foreground">No jobs yet.</p>
          <Link
            href="/"
            className="mt-4 inline-block rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
          >
            Upload a Video
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <Link
              key={job.job_id}
              href={`/jobs/${job.job_id}`}
              className="flex items-center justify-between rounded-lg border p-4 hover:bg-muted/50"
            >
              <div className="flex items-center gap-3">
                {getStatusIcon(job.status)}
                <div>
                  <p className="font-medium">
                    Job {job.job_id.slice(0, 8)}...
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {job.current_step
                      ? job.current_step.replace(/_/g, " ")
                      : job.status}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">{job.progress.toFixed(1)}%</p>
                <p className="text-xs text-muted-foreground">
                  {new Date(job.created_at).toLocaleDateString()}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
