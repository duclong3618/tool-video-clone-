# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Video dubbing pipeline — end-to-end orchestrator.

Chinese video → extract audio → transcribe → translate → TTS → mix → export
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from backend.config import get_settings
from backend.services.ffmpeg import FFmpegService, FFmpegError
from backend.services.transcription import TranscriptionService, TranscriptSegment
from backend.services.translation import TranslationService
from backend.services.tts import TTSService
from backend.services.audio_mixer import AudioMixerService
from backend.services.subtitles import SubtitleService

logger = logging.getLogger(__name__)


@dataclass
class PipelineOptions:
    """Options for a dubbing pipeline run."""
    source_language: str = "zh"
    target_language: str = "vi"
    translation_model: str = ""
    tts_provider: str = "edge"
    tts_voice: str = ""
    enable_diarization: bool = False
    enable_subtitles: bool = True
    burn_subtitles: bool = False
    preserve_background: bool = True
    enable_lipsync: bool = False
    output_quality: str = "high"  # low | medium | high
    webhook_url: str = ""  # Optional webhook for job completion


@dataclass
class PipelineResult:
    """Result of a completed pipeline run."""
    output_video: str = ""
    subtitle_srt: str = ""
    subtitle_ass: str = ""
    transcript_json: str = ""
    segments: list[dict] = field(default_factory=list)
    speakers: dict = field(default_factory=dict)
    error: str = ""
    success: bool = False


class PipelineProgress:
    """Track and report pipeline progress via callback."""

    STEPS = [
        "extracting_audio",
        "separating_vocals",
        "transcribing",
        "detecting_speakers",
        "translating",
        "generating_voices",
        "synchronizing_audio",
        "mixing_audio",
        "rendering_video",
        "completed",
    ]

    def __init__(self, on_progress: Callable[[str, float, str], Any] | None = None):
        self._on_progress = on_progress
        self._current_step_idx = 0

    def update(self, step: str, progress: float, message: str = "") -> None:
        """Report progress for the current step."""
        # Calculate overall progress
        step_weight = 100.0 / len(self.STEPS)
        if step in self.STEPS:
            self._current_step_idx = self.STEPS.index(step)
        overall = (self._current_step_idx * step_weight) + (progress * step_weight / 100)

        logger.info("[%s] %.1f%% - %s", step, overall, message)

        if self._on_progress:
            self._on_progress(step, min(overall, 100.0), message)

    def complete(self) -> None:
        """Mark pipeline as complete."""
        if self._on_progress:
            self._on_progress("completed", 100.0, "Pipeline completed successfully")


class VideoDubPipeline:
    """End-to-end video dubbing pipeline."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._ffmpeg = FFmpegService()
        self._transcription = TranscriptionService()
        self._translation = TranslationService()
        self._tts: TTSService | None = None
        self._mixer = AudioMixerService()
        self._subtitles = SubtitleService()

    async def run(
        self,
        video_id: str,
        input_video: str,
        options: PipelineOptions | None = None,
        on_progress: Callable[[str, float, str], Any] | None = None,
    ) -> PipelineResult:
        """
        Run the full dubbing pipeline.
        
        Args:
            video_id: Unique ID for this video/job
            input_video: Path to input video file
            options: Pipeline options
            on_progress: Callback for progress updates (step, progress, message)
        """
        if options is None:
            options = PipelineOptions()

        settings = self._settings
        progress = PipelineProgress(on_progress)

        # Create working directories
        work_dir = os.path.join(settings.OUTPUT_DIR, video_id)
        os.makedirs(work_dir, exist_ok=True)

        result = PipelineResult()

        try:
            # ── Step 1: Extract audio ────────────────────────
            progress.update("extracting_audio", 0, "Extracting audio from video")
            audio_path = os.path.join(work_dir, "audio_original.wav")
            await self._ffmpeg.extract_audio(input_video, audio_path)
            progress.update("extracting_audio", 100, "Audio extracted")

            # ── Step 2: Separate vocals (if enabled) ─────────
            vocals_path = audio_path
            background_path = None

            if options.preserve_background:
                progress.update("separating_vocals", 0, "Separating vocals from background")
                vocals_path = os.path.join(work_dir, "vocals.wav")
                background_path = os.path.join(work_dir, "background.wav")

                try:
                    # Try Demucs first
                    vocals_path, background_path = await self._separate_with_demucs(
                        audio_path, vocals_path, background_path
                    )
                except Exception as e:
                    logger.warning("Demucs separation failed (%s), using original audio", e)
                    vocals_path = audio_path
                    background_path = None

                progress.update("separating_vocals", 100, "Vocal separation complete")

            # ── Step 3: Transcribe ───────────────────────────
            progress.update("transcribing", 0, f"Transcribing with WhisperX ({options.source_language})")
            transcription = await self._transcription.transcribe(
                audio_path=vocals_path,
                language=options.source_language,
            )
            progress.update("transcribing", 100, f"Transcribed {len(transcription.segments)} segments")

            # ── Step 4: Speaker diarization ──────────────────
            speakers_map: dict[str, list] = {}
            if options.enable_diarization:
                progress.update("detecting_speakers", 0, "Detecting speakers")
                speakers_map = await self._transcription.diarize(vocals_path)
                transcription.segments = self._transcription.assign_speakers_to_segments(
                    transcription.segments, speakers_map
                )
                progress.update("detecting_speakers", 100, f"Found {len(speakers_map)} speakers")
            else:
                # Default single speaker
                for seg in transcription.segments:
                    seg.speaker = "speaker_01"

            # Build segment dicts for the rest of the pipeline
            segment_dicts = [
                {
                    "index": i,
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "speaker": seg.speaker or "speaker_01",
                }
                for i, seg in enumerate(transcription.segments)
            ]

            # ── Step 5: Translate ────────────────────────────
            progress.update("translating", 0, f"Translating {len(segment_dicts)} segments to Vietnamese")

            translated_segments = await self._translate_with_progress(
                segment_dicts, progress
            )
            progress.update("translating", 100, "Translation complete")

            # ── Step 6: Generate TTS ─────────────────────────
            progress.update("generating_voices", 0, "Generating Vietnamese voices")
            self._tts = TTSService(provider_name=options.tts_provider)

            tts_segments = await self._generate_tts_with_progress(
                translated_segments, work_dir, progress
            )
            progress.update("generating_voices", 100, "Voice generation complete")

            # ── Step 7: Synchronize audio ────────────────────
            progress.update("synchronizing_audio", 0, "Synchronizing audio timing")

            total_duration = transcription.duration
            dubbed_track = os.path.join(work_dir, "dubbed_track.wav")

            await self._mixer.build_dubbed_track(
                tts_segments=tts_segments,
                output_path=dubbed_track,
                total_duration=total_duration,
            )
            progress.update("synchronizing_audio", 100, "Audio synchronized")

            # ── Step 8: Mix with background ──────────────────
            progress.update("mixing_audio", 0, "Mixing audio tracks")

            mixed_audio = os.path.join(work_dir, "mixed_audio.wav")
            await self._mixer.mix_with_background(
                dubbed_track=dubbed_track,
                background_audio=background_path,
                output_path=mixed_audio,
                total_duration=total_duration,
                background_volume=0.3,
            )
            progress.update("mixing_audio", 100, "Audio mixed")

            # ── Step 9: Generate subtitles ───────────────────
            subtitle_srt = ""
            subtitle_ass = ""
            transcript_json = ""

            if options.enable_subtitles:
                subtitle_srt = os.path.join(work_dir, "subtitle_vi.srt")
                subtitle_ass = os.path.join(work_dir, "subtitle_vi.ass")
                transcript_json = os.path.join(work_dir, "transcript.json")

                self._subtitles.generate_srt(translated_segments, subtitle_srt)
                self._subtitles.generate_ass(translated_segments, subtitle_ass)
                self._subtitles.segments_to_json(translated_segments, transcript_json)

            # ── Step 10: Lip-sync (optional) ────────────────
            lip_synced_video = input_video
            if options.enable_lipsync:
                progress.update("rendering_video", 20, "Applying lip-sync")
                try:
                    from backend.services.lipsync import get_lipsync_provider
                    lipsync = get_lipsync_provider()
                    lip_synced_video = os.path.join(work_dir, "lipsynced.mp4")
                    await lipsync.process(input_video, mixed_audio, lip_synced_video)
                except Exception as e:
                    logger.warning("Lip-sync failed, continuing without: %s", e)
                    lip_synced_video = input_video

            # ── Step 11: Render final video ──────────────────
            progress.update("rendering_video", 50, "Rendering final video")

            output_video = os.path.join(settings.OUTPUT_DIR, f"{video_id}_dubbed.mp4")

            await self._ffmpeg.export_with_subtitle_and_audio(
                input_video=lip_synced_video,
                audio_track=mixed_audio,
                subtitle_file=subtitle_ass if options.burn_subtitles else None,
                output_video=output_video,
                burn_subtitles=options.burn_subtitles,
            )
            progress.update("rendering_video", 100, "Video rendered")

            # ── Done ────────────────────────────────────────
            progress.complete()

            result.output_video = output_video
            result.subtitle_srt = subtitle_srt
            result.subtitle_ass = subtitle_ass
            result.transcript_json = transcript_json
            result.segments = translated_segments
            result.speakers = speakers_map
            result.success = True

        except Exception as e:
            logger.error("Pipeline failed: %s", e, exc_info=True)
            result.error = str(e)
            result.success = False

        finally:
            await self._translation.close()

        # Send webhook notification if configured
        if options.webhook_url and result.success:
            await self._send_webhook(options.webhook_url, result, video_id)

        return result

    async def _send_webhook(self, url: str, result: PipelineResult, video_id: str) -> None:
        """Send webhook notification when pipeline completes."""
        try:
            import httpx
            payload = {
                "video_id": video_id,
                "status": "completed",
                "output_video": result.output_video,
                "subtitle_srt": result.subtitle_srt,
                "subtitle_ass": result.subtitle_ass,
                "segments_count": len(result.segments),
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json=payload)
                logger.info("Webhook sent to %s", url)
        except Exception as e:
            logger.warning("Webhook failed: %s", e)

    # ── Helpers ───────────────────────────────────────────

    async def _separate_with_demucs(
        self, audio_path: str, vocals_out: str, bg_out: str
    ) -> tuple[str, str]:
        """Separate vocals using Demucs."""
        try:
            import subprocess
            work_dir = os.path.dirname(vocals_out)
            cmd = [
                "python", "-m", "demucs",
                "--two-stems", "vocals",
                "-o", work_dir,
                audio_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise FFmpegError(f"Demucs failed: {stderr.decode()[-500:]}")

            # Demucs outputs to a subdirectory
            base_name = Path(audio_path).stem
            demucs_dir = os.path.join(work_dir, "htdemucs", base_name)
            vocals_src = os.path.join(demucs_dir, "vocals.wav")
            bg_src = os.path.join(demucs_dir, "no_vocals.wav")

            if os.path.exists(vocals_src):
                os.rename(vocals_src, vocals_out)
            if os.path.exists(bg_src):
                os.rename(bg_src, bg_out)

            return vocals_out, bg_out
        except ImportError:
            raise FFmpegError("Demucs not installed")

    async def _translate_with_progress(
        self,
        segments: list[dict],
        progress: PipelineProgress,
    ) -> list[dict]:
        """Translate segments with progress updates."""
        total = len(segments)
        translated = []

        # Process in batches for progress reporting
        batch_size = 5
        for i in range(0, total, batch_size):
            batch = segments[i : i + batch_size]
            results = await self._translation.translate_batch(batch)
            translated.extend(results)

            pct = min((i + batch_size) / total * 100, 100)
            progress.update("translating", pct, f"Translated {min(i + batch_size, total)}/{total}")

        return translated

    async def _generate_tts_with_progress(
        self,
        segments: list[dict],
        work_dir: str,
        progress: PipelineProgress,
    ) -> list[dict]:
        """Generate TTS for each segment in parallel with progress updates."""
        tts_dir = os.path.join(work_dir, "tts")
        os.makedirs(tts_dir, exist_ok=True)

        total = len(segments)
        tts_segments: list[dict] = []
        completed_count = 0
        lock = asyncio.Lock()

        # Limit concurrent TTS requests (edge-tts has rate limits)
        max_concurrent = 5
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _generate_one(i: int, seg: dict) -> dict | None:
            nonlocal completed_count
            async with semaphore:
                speaker = seg.get("speaker", "speaker_01")
                voice = self._tts.get_voice_for_speaker(speaker)  # type: ignore
                output_path = os.path.join(tts_dir, f"tts_{i:04d}.wav")

                try:
                    audio_path = await self._tts.synthesize_with_retry(  # type: ignore
                        text=seg.get("translated_text", seg["text"]),
                        output_path=output_path,
                        voice=voice,
                    )
                    result = {**seg, "audio_path": audio_path}
                except Exception as e:
                    logger.error("TTS failed for segment %d: %s", i, e)
                    result = None

                async with lock:
                    completed_count += 1
                    pct = min(completed_count / total * 100, 100)
                    progress.update(
                        "generating_voices", pct,
                        f"Generated {completed_count}/{total} voices"
                    )
                return result

        # Run all TTS tasks in parallel
        tasks = [_generate_one(i, seg) for i, seg in enumerate(segments)]
        results = await asyncio.gather(*tasks)

        tts_segments = [r for r in results if r is not None]
        return tts_segments
