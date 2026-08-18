# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

# ADR-004: Translation Caching

## Status
Accepted

## Context
Translation API calls cost money and time. Identical segments across videos (or re-runs) should not re-translate.

## Decision
Cache translations in three layers: in-memory → Redis → disk. Lookup order: memory first, then Redis, then disk.

## Consequences

### Positive
- Saves API costs on repeated translations
- Near-instant cache hits from memory
- Persistent across restarts via disk cache

### Negative
- Stale translations if source text changes
- Disk cache grows over time (mitigated by SHA256 key)

### Cache Key
SHA256 hash of `source_lang:target_lang:text`
