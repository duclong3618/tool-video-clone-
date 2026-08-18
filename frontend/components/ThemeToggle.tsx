// Author: DUC LONG
// Year: 2026
// Project: VideoDubAI

"use client"

import { useTheme } from "@/hooks/useTheme"
import { Moon, Sun, Monitor } from "lucide-react"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  const cycle = () => {
    const next = theme === "light" ? "dark" : theme === "dark" ? "system" : "light"
    setTheme(next)
  }

  return (
    <button
      onClick={cycle}
      className="rounded-md border p-2 hover:bg-muted transition-colors"
      title={`Theme: ${theme}`}
    >
      {theme === "light" && <Sun className="h-4 w-4" />}
      {theme === "dark" && <Moon className="h-4 w-4" />}
      {theme === "system" && <Monitor className="h-4 w-4" />}
    </button>
  )
}
