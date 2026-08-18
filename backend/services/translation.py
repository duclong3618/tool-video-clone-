# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Translation service — Chinese → Vietnamese subtitle translation.

Supports OpenAI-compatible APIs and Ollama for local LLM.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

from backend.config import get_settings
from backend.services.cache import get_translation_cache

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional Chinese-to-Vietnamese subtitle translator.

Translate Chinese dialogue into natural, conversational Vietnamese.

Requirements:
- Preserve meaning and tone.
- Preserve names and terminology (keep Chinese names, transliterate if needed).
- Do not add explanations or summaries.
- Do not add translator notes.
- Keep the speaker's emotion and intent.
- Make dialogue sound natural when spoken aloud in Vietnamese.
- Keep the translated sentence concise enough for dubbing.
- Avoid literal / machine-translation style Vietnamese.
- Use natural Vietnamese particles and expressions.
- Output ONLY the translated text, nothing else.

Output format: Return ONLY the Vietnamese translation. No quotes, no numbering, no explanation."""


class TranslationService:
    """Translate text segments using LLM backends."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def translate_segment(
        self,
        text: str,
        context_before: str = "",
        context_after: str = "",
    ) -> str:
        """Translate a single Chinese segment to Vietnamese."""
        settings = self._settings

        # Check cache first (exact match only, no context)
        cache = get_translation_cache()
        cached = await cache.get(text, settings.SOURCE_LANGUAGE, settings.TARGET_LANGUAGE)
        if cached:
            logger.debug("Cache hit: %s → %s", text[:50], cached[:50])
            return cached

        # Build contextual prompt
        user_prompt = text
        if context_before or context_after:
            parts = []
            if context_before:
                parts.append(f"[Context before: {context_before}]")
            parts.append(f"[Translate]: {text}")
            if context_after:
                parts.append(f"[Context after: {context_after}]")
            user_prompt = " ".join(parts)

        if settings.TRANSLATION_PROVIDER == "ollama":
            result = await self._translate_ollama(user_prompt)
        else:
            result = await self._translate_openai(user_prompt)

        # Store in cache
        await cache.set(text, result, settings.SOURCE_LANGUAGE, settings.TARGET_LANGUAGE)
        return result

    async def translate_batch(
        self,
        segments: list[dict],
        context_window: int = 2,
    ) -> list[dict]:
        """
        Translate a batch of segments with context from neighboring segments.
        
        Each segment dict should have 'text', 'start', 'end', 'speaker'.
        Returns the same list with 'translated_text' added.
        """
        results = []
        for i, seg in enumerate(segments):
            # Build context from nearby segments
            before_texts = []
            for j in range(max(0, i - context_window), i):
                t = segments[j].get("translated_text") or segments[j].get("text", "")
                if t:
                    before_texts.append(t)

            after_texts = []
            for j in range(i + 1, min(len(segments), i + 1 + context_window)):
                after_texts.append(segments[j].get("text", ""))

            translated = await self.translate_segment(
                text=seg["text"],
                context_before=" ".join(before_texts),
                context_after=" ".join(after_texts),
            )

            results.append({**seg, "translated_text": translated})
            logger.debug("Translated: %s → %s", seg["text"][:50], translated[:50])

        return results

    async def _translate_openai(self, user_prompt: str) -> str:
        """Translate via OpenAI-compatible API."""
        settings = self._settings
        client = await self._get_client()

        url = f"{settings.OPENAI_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.TRANSLATION_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 512,
        }

        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error("OpenAI translation failed: %s", e)
            raise

    async def _translate_ollama(self, user_prompt: str) -> str:
        """Translate via Ollama local LLM."""
        settings = self._settings
        client = await self._get_client()

        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 512,
            },
        }

        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"].strip()
        except Exception as e:
            logger.error("Ollama translation failed: %s", e)
            raise

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
