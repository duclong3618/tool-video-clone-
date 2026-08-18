// Author: DUC LONG
// Year: 2026
// Project: VideoDubAI

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatTime(seconds: number): string {
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

export function parseTime(timeStr: string): number {
  const parts = timeStr.split(":")
  if (parts.length !== 3) return 0
  const h = parseInt(parts[0]) || 0
  const m = parseInt(parts[1]) || 0
  const sParts = parts[2].split(".")
  const s = parseInt(sParts[0]) || 0
  const ms = parseInt(sParts[1]) || 0
  return h * 3600 + m * 60 + s + ms / 100
}
