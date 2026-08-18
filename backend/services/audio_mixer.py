# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Audio mixing service — combine TTS voices with background music/effects.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from backend.services.ffmpeg import FFmpegService
from backend.config import get_settings

logger = logging.getLogger(__name__)


class AudioMixerService:
    """Mix TTS segments with background audio."""

    def __init__(self) -> None:
        self._ffmpeg = FFmpegService()
        self._settings = get_settings()

    async def build_dubbed_track(
        self,
        tts_segments: list[dict],
        output_path: str,
        total_duration: float,
    ) -> str:
        """
        Build a complete dubbed audio track from individual TTS segments.
        
        Each tts_segment dict: {
            "start": float,
            "end": float,
            "audio_path": str,
            "speaker": str,
        }
        """
        if not tts_segments:
            raise ValueError("No TTS segments to mix")

        settings = self._settings
        temp_dir = os.path.join(settings.AUDIO_DIR, "mix_temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Place each TTS segment at its correct timestamp
        placed_segments = []
        for i, seg in enumerate(tts_segments):
            if not seg.get("audio_path") or not os.path.exists(seg["audio_path"]):
                logger.warning("Missing TTS audio for segment %d, skipping", i)
                continue

            placed_path = os.path.join(temp_dir, f"placed_{i:04d}.wav")
            await self._ffmpeg.place_segment_at_timestamp(
                tts_audio=seg["audio_path"],
                output_audio=placed_path,
                start_time=seg["start"],
                end_time=seg["end"],
                total_duration=total_duration,
            )
            placed_segments.append(placed_path)

        if not placed_segments:
            raise ValueError("No valid TTS segments after placement")

        # Mix all placed segments together
        track_paths = [(p, 1.0) for p in placed_segments]
        await self._ffmpeg.mix_audio(track_paths, output_path, duration=total_duration)

        # Cleanup temp files
        for p in placed_segments:
            try:
                os.remove(p)
            except OSError:
                pass

        return output_path

    async def mix_with_background(
        self,
        dubbed_track: str,
        background_audio: Optional[str],
        output_path: str,
        total_duration: float,
        background_volume: float = 0.3,
        dubbed_volume: float = 1.0,
    ) -> str:
        """
        Mix dubbed voice track with background audio.
        
        Args:
            dubbed_track: Path to the generated Vietnamese dubbed audio
            background_audio: Path to extracted background music/effects
            output_path: Output path for mixed audio
            total_duration: Total duration in seconds
            background_volume: Volume multiplier for background (0.0-1.0)
            dubbed_volume: Volume multiplier for dubbed voice
        """
        if not background_audio or not os.path.exists(background_audio):
            # No background to mix — just copy the dubbed track
            logger.info("No background audio available, using dubbed track only")
            tracks = [(dubbed_track, dubbed_volume)]
        else:
            # Mix dubbed + background
            tracks = [
                (dubbed_track, dubbed_volume),
                (background_audio, background_volume),
            ]

        await self._ffmpeg.mix_audio(tracks, output_path, duration=total_duration)
        return output_path

    async def normalize_audio(
        self,
        input_path: str,
        output_path: str,
        target_loudness: float = -16.0,
    ) -> str:
        """Normalize audio to target loudness (LUFS)."""
        # Use loudnorm filter for broadcast-quality normalization
        import shlex
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-af", f"loudnorm=I={target_loudness}:TP=-1.5:LRA=11",
            "-ar", "44100",
            "-ac", "2",
            output_path,
        ]
        await self._ffmpeg._run(cmd)
        return output_path
