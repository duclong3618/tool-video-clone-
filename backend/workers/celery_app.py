# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Celery application configuration for background job processing.
"""

from celery import Celery
from backend.config import get_settings

settings = get_settings()

celery_app = Celery(
    "videodub",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1,
    task_soft_time_limit=3600,  # 1 hour soft limit
    task_time_limit=7200,  # 2 hour hard limit
)
