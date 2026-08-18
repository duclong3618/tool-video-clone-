# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
TTS service — abstraction layer with multiple providers.

Providers: EdgeTTS (free), ElevenLabs, Qwen3-TTS
"""

from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)

# ── Vietnamese voice mappings ────────────────────────────

EDGE_TTS_VOICES = {
    "vi-VN-HoaiMyNeural": "Vietnamese Female (HoaiMy)",
    "vi-VN-NamMinhNeural": "Vietnamese Male (NamMinh)",
}

# Map speakers to default voices
DEFAULT_SPEAKER_VOICE_MAP = {
    "speaker_01": "vi-VN-HoaiMyNeural",
    "speaker_02": "vi-VN-NamMinhNeural",
    "speaker_03": "vi-VN-HoaiMyNeural",
}


class BaseTTSProvider(ABC):
    """Base class for TTS providers."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str,
        speed: float = 1.0,
    ) -> str:
        """Generate speech audio from text. Returns output path."""
        ...

    @abstractmethod
    def list_voices(self) -> list[dict]:
        """List available voices."""
        ...


class EdgeTTSProvider(BaseTTSProvider):
    """Microsoft Edge TTS — free, good quality Vietnamese voices."""

    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = "vi-VN-HoaiMyNeural",
        speed: float = 1.0,
    ) -> str:
        import edge_tts

        # Edge TTS uses rate adjustment like "+10%", "-10%"
        rate_pct = int((speed - 1.0) * 100)
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate_str,
        )
        await communicate.save(output_path)
        return output_path

    def list_voices(self) -> list[dict]:
        return [
            {"id": k, "name": v, "provider": "edge"}
            for k, v in EDGE_TTS_VOICES.items()
        ]


class ElevenLabsProvider(BaseTTSProvider):
    """ElevenLabs TTS — high quality, supports voice cloning."""

    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = "21m00Tcm4TlvDq8ikWAM",
        speed: float = 1.0,
    ) -> str:
        import httpx

        settings = get_settings()
        client = httpx.AsyncClient(timeout=60.0)

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
        headers = {
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": settings.ELEVENLABS_MODEL,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "speed": speed,
            },
        }

        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return output_path
        finally:
            await client.aclose()

    def list_voices(self) -> list[dict]:
        return [{"id": "custom", "name": "ElevenLabs Voice", "provider": "elevenlabs"}]


class Qwen3TTSProvider(BaseTTSProvider):
    """Qwen3-TTS provider — local or API-based."""

    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = "default",
        speed: float = 1.0,
    ) -> str:
        settings = get_settings()

        if settings.QWEN3_TTS_BASE_URL:
            return await self._synthesize_api(text, output_path, voice, speed, settings)
        else:
            return await self._synthesize_local(text, output_path, voice, speed)

    async def _synthesize_api(
        self, text: str, output_path: str, voice: str, speed: float, settings
    ) -> str:
        import httpx

        client = httpx.AsyncClient(timeout=120.0)
        url = f"{settings.QWEN3_TTS_BASE_URL}/v1/audio/speech"
        headers = {"Authorization": f"Bearer {settings.QWEN3_TTS_API_KEY}"}
        payload = {
            "model": "qwen3-tts",
            "input": text,
            "voice": voice,
            "speed": speed,
        }

        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return output_path
        finally:
            await client.aclose()

    async def _synthesize_local(
        self, text: str, output_path: str, voice: str, speed: float
    ) -> str:
        """Local Qwen3-TTS inference (requires model installed locally)."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            model_name = "Qwen/Qwen3-TTS"
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_name, trust_remote_code=True, torch_dtype=torch.float16
            )

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(device)

            # Generate speech
            inputs = tokenizer(text, return_tensors="pt").to(device)
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=4096)

            # Save audio (implementation depends on model's audio output format)
            # This is a placeholder — actual implementation depends on Qwen3-TTS API
            logger.warning("Local Qwen3-TTS requires specific model setup")
            raise NotImplementedError(
                "Local Qwen3-TTS requires model-specific implementation. "
                "Use EdgeTTS or ElevenLabs as fallback."
            )

        except ImportError:
            raise RuntimeError("Qwen3-TTS requires torch and transformers")

    def list_voices(self) -> list[dict]:
        return [{"id": "default", "name": "Qwen3 Default", "provider": "qwen3tts"}]


# ── Factory ──────────────────────────────────────────────

PROVIDERS: dict[str, type[BaseTTSProvider]] = {
    "edge": EdgeTTSProvider,
    "elevenlabs": ElevenLabsProvider,
    "qwen3tts": Qwen3TTSProvider,
}


class TTSService:
    """High-level TTS service that delegates to the configured provider."""

    def __init__(self, provider_name: str | None = None) -> None:
        settings = get_settings()
        name = provider_name or settings.TTS_PROVIDER
        provider_cls = PROVIDERS.get(name)
        if provider_cls is None:
            raise ValueError(f"Unknown TTS provider: {name}. Available: {list(PROVIDERS)}")
        self._provider = provider_cls()
        self._provider_name = name
        logger.info("TTS provider: %s", name)

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> str:
        """Synthesize text to audio file."""
        if voice is None:
            voice = self._default_voice()
        return await self._provider.synthesize(text, output_path, voice, speed)

    async def synthesize_with_retry(
        self,
        text: str,
        output_path: str,
        voice: str | None = None,
        speed: float = 1.0,
        max_retries: int = 3,
    ) -> str:
        """Synthesize with retry logic for transient failures."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return await self.synthesize(text, output_path, voice, speed)
            except Exception as e:
                last_error = e
                logger.warning(
                    "TTS attempt %d/%d failed: %s",
                    attempt + 1, max_retries, e,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
        raise last_error  # type: ignore[misc]

    def list_voices(self) -> list[dict]:
        return self._provider.list_voices()

    def _default_voice(self) -> str:
        settings = get_settings()
        if self._provider_name == "edge":
            return "vi-VN-HoaiMyNeural"
        elif self._provider_name == "elevenlabs":
            return "21m00Tcm4TlvDq8ikWAM"  # Rachel
        else:
            return "default"

    def get_voice_for_speaker(self, speaker: str) -> str:
        """Get the assigned voice for a speaker label."""
        return DEFAULT_SPEAKER_VOICE_MAP.get(speaker, self._default_voice())
