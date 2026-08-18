# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Transcription service — WhisperX wrapper with GPU detection.

Supports WhisperX (primary) and faster-whisper as fallback.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """A single transcription segment."""
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    words: list[dict] = field(default_factory=list)


@dataclass
class TranscriptionResult:
    """Full transcription result."""
    segments: list[TranscriptSegment]
    language: str
    duration: float
    raw_text: str = ""


def detect_device() -> tuple[str, str]:
    """Detect the best available compute device and precision."""
    settings = get_settings()

    if settings.WHISPER_DEVICE == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
                compute_type = "float16"
            else:
                device = "cpu"
                compute_type = "int8"
        except ImportError:
            device = "cpu"
            compute_type = "int8"
    else:
        device = settings.WHISPER_DEVICE
        if settings.WHISPER_COMPUTE_TYPE == "auto":
            compute_type = "float16" if device == "cuda" else "int8"
        else:
            compute_type = settings.WHISPER_COMPUTE_TYPE

    logger.info("Using device=%s, compute_type=%s", device, compute_type)
    return device, compute_type


class TranscriptionService:
    """Transcribe audio using WhisperX (preferred) or faster-whisper."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._model = None
        self._device: str | None = None

    def _load_model(self) -> None:
        if self._model is not None:
            return

        device, compute_type = detect_device()
        self._device = device
        model_name = self._settings.WHISPER_MODEL

        # Try WhisperX first
        try:
            import whisperx

            logger.info("Loading WhisperX model: %s on %s", model_name, device)
            self._model = whisperx.load_model(
                model_name,
                device,
                compute_type=compute_type,
                language="zh",
            )
            self._backend = "whisperx"
            return
        except (ImportError, Exception) as e:
            logger.warning("WhisperX unavailable (%s), trying faster-whisper", e)

        # Fallback to faster-whisper
        try:
            from faster_whisper import WhisperModel

            logger.info("Loading faster-whisper model: %s on %s", model_name, device)
            model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
            )
            self._model = model
            self._backend = "faster-whisper"
        except ImportError as e:
            raise RuntimeError(
                "No transcription backend available. "
                "Install whisperx or faster-whisper."
            ) from e

    async def transcribe(
        self,
        audio_path: str,
        language: str = "zh",
        batch_size: int = 16,
    ) -> TranscriptionResult:
        """
        Transcribe audio file and return structured segments.
        
        Args:
            audio_path: Path to WAV audio file (16 kHz mono recommended)
            language: Source language code
            batch_size: Batch size for GPU processing
            
        Returns:
            TranscriptionResult with timed segments
        """
        self._load_model()
        logger.info("Transcribing: %s (backend=%s)", audio_path, self._backend)

        if self._backend == "whisperx":
            return await self._transcribe_whisperx(audio_path, language, batch_size)
        else:
            return await self._transcribe_faster(audio_path, language)

    async def _transcribe_whisperx(
        self, audio_path: str, language: str, batch_size: int
    ) -> TranscriptionResult:
        import whisperx

        # 1. Transcribe
        audio = whisperx.load_audio(audio_path)
        result = self._model.transcribe(audio, batch_size=batch_size, language=language)

        # 2. Align for better word-level timestamps
        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=language, device=self._device
            )
            result = whisperx.align(
                result["segments"], model_a, metadata, audio, self._device
            )
        except Exception as e:
            logger.warning("Alignment failed, using raw segments: %s", e)

        segments = []
        for seg in result.get("segments", []):
            segments.append(TranscriptSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"].strip(),
                words=seg.get("words", []),
            ))

        raw_text = " ".join(s.text for s in segments)

        return TranscriptionResult(
            segments=segments,
            language=language,
            duration=segments[-1].end if segments else 0.0,
            raw_text=raw_text,
        )

    async def _transcribe_faster(
        self, audio_path: str, language: str
    ) -> TranscriptionResult:
        from faster_whisper import WhisperModel

        model: WhisperModel = self._model
        segments_gen, info = model.transcribe(
            audio_path,
            language=language if language != "auto" else None,
            beam_size=5,
            word_timestamps=True,
        )

        segments = []
        for seg in segments_gen:
            words = []
            if seg.words:
                words = [
                    {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                    for w in seg.words
                ]
            segments.append(TranscriptSegment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                words=words,
            ))

        raw_text = " ".join(s.text for s in segments)

        return TranscriptionResult(
            segments=segments,
            language=info.language or language,
            duration=segments[-1].end if segments else 0.0,
            raw_text=raw_text,
        )

    async def diarize(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
    ) -> dict[str, list[str]]:
        """
        Run speaker diarization using pyannote.
        
        Returns a mapping of speaker_label -> list of segment indices.
        """
        settings = self._settings

        if not settings.PYANNOTE_AUTH_TOKEN:
            logger.warning("No pyannote auth token — skipping diarization")
            return {}

        try:
            from pyannote.audio import Pipeline
            import torch

            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=settings.PYANNOTE_AUTH_TOKEN,
            )

            device = "cuda" if torch.cuda.is_available() else "cpu"
            pipeline.to(torch.device(device))

            diarize_kwargs = {}
            if num_speakers:
                diarize_kwargs["num_speakers"] = num_speakers

            diarization = pipeline(audio_path, **diarize_kwargs)

            speaker_segments: dict[str, list[dict]] = {}
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                if speaker not in speaker_segments:
                    speaker_segments[speaker] = []
                speaker_segments[speaker].append({
                    "start": turn.start,
                    "end": turn.end,
                })

            return speaker_segments

        except ImportError:
            logger.warning("pyannote not installed — skipping diarization")
            return {}
        except Exception as e:
            logger.error("Diarization failed: %s", e)
            return {}

    def assign_speakers_to_segments(
        self,
        segments: list[TranscriptSegment],
        speaker_segments: dict[str, list[dict]],
    ) -> list[TranscriptSegment]:
        """Assign speaker labels to transcript segments based on overlap."""
        if not speaker_segments:
            # Default: single speaker
            for seg in segments:
                seg.speaker = "speaker_01"
            return segments

        for seg in segments:
            best_speaker = None
            best_overlap = 0.0

            for speaker, turns in speaker_segments.items():
                for turn in turns:
                    overlap_start = max(seg.start, turn["start"])
                    overlap_end = min(seg.end, turn["end"])
                    overlap = max(0.0, overlap_end - overlap_start)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_speaker = speaker

            seg.speaker = best_speaker or "speaker_01"

        return segments
