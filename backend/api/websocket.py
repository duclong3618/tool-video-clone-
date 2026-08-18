# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
WebSocket handler for real-time job progress updates.

WS /api/jobs/{job_id}/progress
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from backend.models.database import Job, JobStatus, async_session_factory

logger = logging.getLogger(__name__)

# Active WebSocket connections per job
_connections: dict[str, set[WebSocket]] = {}


async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
    """Handle a WebSocket connection for job progress."""
    await websocket.accept()

    # Register connection
    if job_id not in _connections:
        _connections[job_id] = set()
    _connections[job_id].add(websocket)

    try:
        # Send initial status
        await _send_status(websocket, job_id)

        # Keep connection alive and poll for updates
        while True:
            # Check if client sent any message (e.g., cancel)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=2.0
                )
                msg = json.loads(data)
                if msg.get("action") == "cancel":
                    await _cancel_job(job_id)
                    await websocket.send_json({"type": "cancelled"})
                    break
            except asyncio.TimeoutError:
                # No message — send latest status
                pass

            # Send current status
            await _send_status(websocket, job_id)

            # If job is done, close
            status = await _get_job_status(job_id)
            if status in ("completed", "failed", "cancelled"):
                break

            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        logger.info("Client disconnected from job %s", job_id)
    except Exception as e:
        logger.error("WebSocket error for job %s: %s", job_id, e)
    finally:
        _connections[job_id].discard(websocket)
        if not _connections[job_id]:
            _connections.pop(job_id, None)


async def broadcast_progress(
    job_id: str, step: str, progress: float, message: str = ""
) -> None:
    """Broadcast progress to all connected clients for a job."""
    if job_id not in _connections:
        return

    payload = {
        "type": "progress",
        "step": step,
        "progress": round(progress, 1),
        "message": message,
    }

    dead = set()
    for ws in _connections[job_id]:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.add(ws)

    _connections[job_id] -= dead


async def _send_status(websocket: WebSocket, job_id: str) -> None:
    """Send current job status to a WebSocket client."""
    status = await _get_job_status(job_id)
    if status is None:
        await websocket.send_json({"type": "error", "message": "Job not found"})
        return

    await websocket.send_json(status)


async def _get_job_status(job_id: str) -> dict[str, Any] | None:
    """Fetch current job status from database."""
    if async_session_factory is None:
        return None

    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
        job = result.scalar_one_or_none()
        if not job:
            return None

        return {
            "type": "status",
            "job_id": str(job.id),
            "video_id": str(job.video_id),
            "status": job.status.value,
            "current_step": job.current_step.value if job.current_step else None,
            "progress": round(job.progress or 0.0, 1),
            "error_message": job.error_message,
        }


async def _cancel_job(job_id: str) -> None:
    """Cancel a running job."""
    if async_session_factory is None:
        return

    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
        job = result.scalar_one_or_none()
        if job and job.status in (JobStatus.QUEUED, JobStatus.PROCESSING):
            job.status = JobStatus.CANCELLED
            await db.commit()

        # Broadcast cancellation
        await broadcast_progress(job_id, "cancelled", 100, "Job cancelled by user")
