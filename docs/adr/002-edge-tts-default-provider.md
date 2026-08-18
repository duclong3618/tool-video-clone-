# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

# ADR-002: Edge TTS as Default Provider

## Status
Accepted

## Context
TTS is a core feature. Providers vary in cost, quality, and availability. Need a default that works for MVP without requiring API keys.

## Decision
Edge TTS is the default TTS provider. Users can switch to ElevenLabs or Qwen3-TTS via configuration.

## Consequences

### Positive
- Free — no API key required
- Good Vietnamese voices (HoaiMy, NamMinh)
- Simple integration via edge-tts library

### Negative
- Requires internet connection
- Rate limits from Microsoft
- Less control over voice parameters

### Alternatives Considered
- ElevenLabs: Higher quality but paid
- Qwen3-TTS: Local but requires GPU + model download
