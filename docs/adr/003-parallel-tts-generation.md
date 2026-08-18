# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

# ADR-003: Parallel TTS Generation

## Status
Accepted

## Context
TTS is the bottleneck in the pipeline. Sequential processing of 50+ segments takes 5-10 minutes. Users expect fast results.

## Decision
Run TTS segments in parallel using asyncio.gather with Semaphore(5) to limit concurrency.

## Consequences

### Positive
- 3-5x speed improvement
- Edge TTS handles concurrency well
- Progress tracking per segment

### Negative
- Higher memory usage
- Potential rate limiting from Edge TTS
- Need careful error handling for partial failures

### Implementation
```python
semaphore = asyncio.Semaphore(5)
async def generate_one(i, seg):
    async with semaphore:
        # TTS synthesis
results = await asyncio.gather(*tasks)
```
