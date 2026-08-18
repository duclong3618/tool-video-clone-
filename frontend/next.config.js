// Author: DUC LONG
// Year: 2026
// Project: VideoDubAI

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    serverComponentsExternalPackages: ["sharp"],
  },
}

module.exports = nextConfig
