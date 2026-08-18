# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

# ADR-005: WebSocket for Real-Time Progress

## Status
Accepted

## Context
Video processing takes 5-30 minutes. Users need to see progress without polling. HTTP polling wastes resources and has latency.

## Decision
Use WebSocket for real-time progress updates. Fallback to HTTP polling if WebSocket fails.

## Consequences

### Positive
- Instant progress updates
- Lower server load than polling
- Cancel support via WebSocket messages

### Negative
- Connection management complexity
- Need heartbeat/reconnection logic
- Harder to debug than HTTP

### Implementation
```
WS /api/jobs/{job_id}/progress
- Client connects on page load
- Server sends {step, progress, message}
- Client can send {action: "cancel"}
- Auto-fallback to GET /api/jobs/{id} polling
```
