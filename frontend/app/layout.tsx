// Author: DUC LONG
// Year: 2026
// Project: VideoDubAI

import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/hooks/useTheme"
import { ThemeToggle } from "@/components/ThemeToggle"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "VideoDubAI — Video Dubbing AI",
  description: "AI-powered video translation and dubbing",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider>
          <div className="min-h-screen bg-background">
            <header className="border-b">
              <div className="container mx-auto flex h-16 items-center justify-between px-4">
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold">🎬 VideoDubAI</span>
                  <span className="text-sm text-muted-foreground hidden sm:inline">
                    Translate & Dub Videos
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <nav className="flex gap-4">
                    <a href="/" className="text-sm hover:underline">
                      Upload
                    </a>
                    <a href="/jobs" className="text-sm hover:underline">
                      Jobs
                    </a>
                  </nav>
                  <ThemeToggle />
                </div>
              </div>
            </header>
            <main className="container mx-auto px-4 py-8">{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  )
}
