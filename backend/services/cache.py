# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Translation cache service — avoid re-translating identical segments.

Uses Redis if available, otherwise falls back to in-memory + disk cache.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

from backend.config import get_settings

logger = logging.getLogger(__name__)


class TranslationCache:
    """Cache translation results to avoid redundant API calls."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._memory_cache: dict[str, str] = {}
        self._redis = None
        self._disk_cache_dir = os.path.join(
            self._settings.OUTPUT_DIR, "_cache", "translations"
        )
        os.makedirs(self._disk_cache_dir, exist_ok=True)

        # Try to connect to Redis
        self._init_redis()

    def _init_redis(self) -> None:
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self._settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=3,
            )
            logger.info("Translation cache: Redis connected")
        except Exception:
            logger.info("Translation cache: using in-memory + disk fallback")
            self._redis = None

    def _cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate a cache key from text + languages."""
        raw = f"{source_lang}:{target_lang}:{text}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    async def get(
        self, text: str, source_lang: str = "zh", target_lang: str = "vi"
    ) -> str | None:
        """Look up cached translation. Returns None if miss."""
        key = self._cache_key(text, source_lang, target_lang)

        # 1. Memory cache (fastest)
        if key in self._memory_cache:
            return self._memory_cache[key]

        # 2. Redis cache
        if self._redis:
            try:
                cached = await self._redis.get(f"trans:{key}")
                if cached:
                    self._memory_cache[key] = cached
                    return cached
            except Exception:
                pass

        # 3. Disk cache (slowest, but persistent)
        disk_path = os.path.join(self._disk_cache_dir, f"{key}.json")
        if os.path.exists(disk_path):
            try:
                with open(disk_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    translated = data.get("translated", "")
                    self._memory_cache[key] = translated
                    # Also populate Redis if available
                    if self._redis:
                        try:
                            await self._redis.set(
                                f"trans:{key}", translated, ex=86400 * 30
                            )
                        except Exception:
                            pass
                    return translated
            except Exception:
                pass

        return None

    async def set(
        self,
        text: str,
        translated: str,
        source_lang: str = "zh",
        target_lang: str = "vi",
    ) -> None:
        """Store a translation in all cache layers."""
        key = self._cache_key(text, source_lang, target_lang)

        # 1. Memory cache
        self._memory_cache[key] = translated

        # 2. Redis cache (30 day TTL)
        if self._redis:
            try:
                await self._redis.set(f"trans:{key}", translated, ex=86400 * 30)
            except Exception:
                pass

        # 3. Disk cache
        disk_path = os.path.join(self._disk_cache_dir, f"{key}.json")
        try:
            with open(disk_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"source": text, "translated": translated, "key": key},
                    f,
                    ensure_ascii=False,
                )
        except Exception:
            pass

    async def get_many(
        self, texts: list[str], source_lang: str = "zh", target_lang: str = "vi"
    ) -> dict[str, str]:
        """Batch lookup. Returns {text: translated} for cache hits."""
        results = {}
        for text in texts:
            cached = await self.get(text, source_lang, target_lang)
            if cached:
                results[text] = cached
        return results

    async def close(self) -> None:
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass


# Singleton
_cache_instance: TranslationCache | None = None


def get_translation_cache() -> TranslationCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TranslationCache()
    return _cache_instance
