# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
FFmpeg service — all video/audio processing goes through here.

Never hard-code shell commands in business logic; always call this service.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)

FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"


class FFmpegError(Exception):
    """Raised when an FFmpeg command fails."""


class FFmpegService:
    """Centralised wrapper around FFmpeg / FFprobe."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Probe ────────────────────────────────────────────

    async def get_duration(self, file_path: str) -> float:
        """Return duration in seconds for the given media file."""
        cmd = [
            FFPROBE_BIN,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            file_path,
        ]
        result = await self._run(cmd)
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])

    async def get_audio_stream_info(self, file_path: str) -> dict:
        """Return audio stream metadata."""
        cmd = [
            FFPROBE_BIN,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "a",
            file_path,
        ]
        result = await self._run(cmd)
        info = json.loads(result.stdout)
        streams = info.get("streams", [])
        return streams[0] if streams else {}

    # ── Extract audio ────────────────────────────────────

    async def extract_audio(
        self,
        input_video: str,
        output_audio: str,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> str:
        """Extract mono 16 kHz WAV audio from video."""
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", input_video,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", str(channels),
            output_audio,
        ]
        await self._run(cmd)
        return output_audio

    # ── Vocal separation (uses Demucs externally) ────────

    async def extract_background(
        self,
        original_video: str,
        vocals_wav: str,
        output_background: str,
    ) -> str:
        """
        Subtract vocals from original mix to get background.
        This is a simple phase-cancellation approach.
        For better results, use Demucs in the pipeline worker.
        """
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", original_video,
            "-i", vocals_wav,
            "-filter_complex",
            "[0:a][1:a]asubtract=inputs=2:weights=1 1[out]",
            "-map", "[out]",
            output_background,
        ]
        try:
            await self._run(cmd)
        except FFmpegError:
            # Fallback: just extract audio track from original as background
            logger.warning("Vocal subtraction failed, extracting original audio as background")
            cmd = [
                FFMPEG_BIN, "-y",
                "-i", original_video,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "2",
                output_background,
            ]
            await self._run(cmd)
        return output_background

    # ── Adjust audio speed ───────────────────────────────

    async def adjust_speed(
        self,
        input_audio: str,
        output_audio: str,
        target_duration: float,
    ) -> str:
        """Adjust audio speed to match target duration."""
        current_duration = await self.get_duration(input_audio)
        if current_duration <= 0:
            raise FFmpegError("Cannot adjust speed of empty audio")

        tempo = current_duration / target_duration
        # Clamp tempo to reasonable range (0.5x – 2.0x)
        tempo = max(0.5, min(2.0, tempo))

        cmd = [
            FFMPEG_BIN, "-y",
            "-i", input_audio,
            "-filter:a", f"atempo={tempo}",
            output_audio,
        ]
        await self._run(cmd)
        return output_audio

    # ── Concatenate TTS segments ─────────────────────────

    async def concat_audio_segments(
        self,
        segment_paths: list[str],
        output_path: str,
    ) -> str:
        """Concatenate multiple audio files into one."""
        if not segment_paths:
            raise FFmpegError("No segments to concatenate")

        list_file = output_path + ".list.txt"
        with open(list_file, "w") as f:
            for p in segment_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")

        cmd = [
            FFMPEG_BIN, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_path,
        ]
        await self._run(cmd)
        os.remove(list_file)
        return output_path

    # ── Place TTS audio at correct timestamp ─────────────

    async def place_segment_at_timestamp(
        self,
        tts_audio: str,
        output_audio: str,
        start_time: float,
        end_time: float,
        total_duration: float,
    ) -> str:
        """Place a TTS segment at the correct position in a silent audio track."""
        target_duration = end_time - start_time
        current_duration = await self.get_duration(tts_audio)

        # Adjust speed if needed
        adjusted = tts_audio
        if current_duration > target_duration * 1.1:
            adjusted = tts_audio + ".adjusted.wav"
            await self.adjust_speed(tts_audio, adjusted, target_duration)

        # Pad or trim to exact duration, then shift to start_time
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", adjusted,
            "-af", (
                f"apad=whole_dur={target_duration},"
                f"atrim=0:{target_duration},"
                f"adelay={int(start_time * 1000)}|{int(start_time * 1000)}"
            ),
            "-t", str(total_duration),
            "-ar", "44100",
            "-ac", "2",
            output_audio,
        ]
        await self._run(cmd)
        return output_audio

    # ── Mix audio tracks ─────────────────────────────────

    async def mix_audio(
        self,
        tracks: list[tuple[str, float]],  # [(path, volume), ...]
        output_path: str,
        duration: Optional[float] = None,
    ) -> str:
        """Mix multiple audio tracks with volume adjustment."""
        if not tracks:
            raise FFmpegError("No tracks to mix")

        inputs = []
        filter_parts = []
        for i, (path, vol) in enumerate(tracks):
            inputs.extend(["-i", path])
            filter_parts.append(f"[{i}]volume={vol}[a{i}]")

        mix_inputs = "".join(f"[a{i}]" for i in range(len(tracks)))
        filter_parts.append(f"{mix_inputs}amix=inputs={len(tracks)}:duration=longest:dropout_transition=0[out]")

        filter_complex = ";".join(filter_parts)
        cmd = [FFMPEG_BIN, "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-ar", "44100",
            "-ac", "2",
            output_path,
        ]
        if duration:
            cmd.extend(["-t", str(duration)])
        await self._run(cmd)
        return output_path

    # ── Burn subtitles ───────────────────────────────────

    async def burn_subtitles(
        self,
        input_video: str,
        subtitle_file: str,
        output_video: str,
    ) -> str:
        """Burn (hardcode) subtitles into video."""
        # Escape path for FFmpeg filter
        escaped_sub = subtitle_file.replace("\\", "/").replace(":", "\\:")
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", input_video,
            "-vf", f"subtitles='{escaped_sub}'",
            "-c:a", "copy",
            output_video,
        ]
        await self._run(cmd)
        return output_video

    # ── Export final video ───────────────────────────────

    async def export_video(
        self,
        input_video: str,
        audio_track: str,
        output_video: str,
        copy_video_stream: bool = True,
    ) -> str:
        """
        Mux original video stream with new audio track.
        If copy_video_stream=True, re-encodes only the audio.
        """
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", input_video,
            "-i", audio_track,
            "-c:v", "copy" if copy_video_stream else "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_video,
        ]
        await self._run(cmd)
        return output_video

    async def export_with_subtitle_and_audio(
        self,
        input_video: str,
        audio_track: str,
        subtitle_file: str | None,
        output_video: str,
        burn_subtitles: bool = False,
    ) -> str:
        """Export video with audio replacement and optional subtitle embedding."""
        if subtitle_file and burn_subtitles:
            # First burn subtitles, then replace audio
            temp_video = output_video + ".sub.mp4"
            await self.burn_subtitles(input_video, subtitle_file, temp_video)
            return await self.export_video(temp_video, audio_track, output_video)
        else:
            return await self.export_video(input_video, audio_track, output_video)

    # ── Internal runner ──────────────────────────────────

    async def _run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        """Run an FFmpeg/FFprobe command asynchronously."""
        logger.debug("Running: %s", " ".join(shlex.quote(str(c)) for c in cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace")[-2000:]
            logger.error("FFmpeg failed (rc=%d): %s", proc.returncode, err_msg)
            raise FFmpegError(f"Command failed (rc={proc.returncode}): {err_msg}")
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
