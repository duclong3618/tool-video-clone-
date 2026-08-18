# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Lip-sync service — LatentSync integration (optional).

This module provides a provider interface for lip-sync processing.
LatentSync requires GPU and specific model weights; if unavailable,
the pipeline continues without lip-sync.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseLipSyncProvider(ABC):
    """Base class for lip-sync providers."""

    @abstractmethod
    async def process(
        self,
        input_video: str,
        audio_track: str,
        output_video: str,
    ) -> str:
        """Apply lip-sync to video. Returns output path."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available on the current system."""
        ...


class LatentSyncProvider(BaseLipSyncProvider):
    """LatentSync lip-sync provider."""

    @property
    def is_available(self) -> bool:
        try:
            import torch
            if not torch.cuda.is_available():
                return False
            # Check if LatentSync model is available
            # This is a placeholder check
            return False
        except ImportError:
            return False

    async def process(
        self,
        input_video: str,
        audio_track: str,
        output_video: str,
    ) -> str:
        if not self.is_available:
            raise RuntimeError("LatentSync is not available on this system")

        # LatentSync integration would go here
        # For now, just copy input to output
        import shutil
        shutil.copy2(input_video, output_video)
        return output_video


class NoOpLipSyncProvider(BaseLipSyncProvider):
    """No-op provider that passes through without modification."""

    @property
    def is_available(self) -> bool:
        return True

    async def process(
        self,
        input_video: str,
        audio_track: str,
        output_video: str,
    ) -> str:
        import shutil
        shutil.copy2(input_video, output_video)
        return output_video


def get_lipsync_provider() -> BaseLipSyncProvider:
    """Get the best available lip-sync provider."""
    providers = [LatentSyncProvider()]

    for provider in providers:
        if provider.is_available:
            logger.info("Using lip-sync provider: %s", type(provider).__name__)
            return provider

    logger.info("No lip-sync provider available, using no-op")
    return NoOpLipSyncProvider()
