# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

# ADR-001: SQLite as Default Database

## Status
Accepted

## Context
VideoDubAI needs a database for storing videos, jobs, segments, and speakers. PostgreSQL is the production choice but requires a running server. Local development and MVP need to work without PostgreSQL.

## Decision
Use SQLite as the default database when PostgreSQL is unavailable. The system auto-detects and falls back to SQLite.

## Consequences

### Positive
- Zero setup for local development
- Works on any machine without server
- Faster iteration during MVP phase

### Negative
- Limited concurrency under heavy load
- Not suitable for production multi-user
- Some PostgreSQL-specific features not available

### Mitigation
- Docker compose includes PostgreSQL for production
- Environment variable `DATABASE_URL` switches between backends
- Future: Add migration from SQLite to PostgreSQL
