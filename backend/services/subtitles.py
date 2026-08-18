# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Subtitle service — generate SRT and ASS subtitle files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_ass_time(seconds: float) -> str:
    """Format seconds to ASS timestamp: H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


class SubtitleService:
    """Generate subtitle files in various formats."""

    def generate_srt(
        self,
        segments: list[dict],
        output_path: str,
        use_translated: bool = True,
    ) -> str:
        """
        Generate SRT subtitle file.
        
        Args:
            segments: List of segment dicts with start, end, text, translated_text
            output_path: Output .srt file path
            use_translated: If True, use translated_text; otherwise use original_text
        """
        lines = []
        for i, seg in enumerate(segments, 1):
            start = _format_srt_time(seg["start"])
            end = _format_srt_time(seg["end"])
            text = seg.get("translated_text") if use_translated else seg.get("text", "")
            if not text:
                text = seg.get("text", "")
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return output_path

    def generate_bilingual_srt(
        self,
        segments: list[dict],
        output_path: str,
    ) -> str:
        """Generate SRT with both original and translated text."""
        lines = []
        for i, seg in enumerate(segments, 1):
            start = _format_srt_time(seg["start"])
            end = _format_srt_time(seg["end"])
            original = seg.get("text", "")
            translated = seg.get("translated_text", "")
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(f"{original}\n{translated}")
            lines.append("")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return output_path

    def generate_ass(
        self,
        segments: list[dict],
        output_path: str,
        use_translated: bool = True,
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> str:
        """Generate ASS (Advanced SubStation Alpha) subtitle file."""
        header = f"""[Script Info]
Title: Vietnamese Dubbed Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {video_width}
PlayResY: {video_height}
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for seg in segments:
            start = _format_ass_time(seg["start"])
            end = _format_ass_time(seg["end"])
            text = seg.get("translated_text") if use_translated else seg.get("text", "")
            if not text:
                text = seg.get("text", "")
            # Replace newlines with ASS line break
            text = text.replace("\n", "\\N")
            events.append(
                f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
            )

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(events))
            f.write("\n")
        return output_path

    def segments_to_json(
        self,
        segments: list[dict],
        output_path: str,
    ) -> str:
        """Export segments as a JSON transcript file."""
        import json

        transcript = {
            "segments": [
                {
                    "index": i,
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker": seg.get("speaker", "speaker_01"),
                    "original_text": seg.get("text", ""),
                    "translated_text": seg.get("translated_text", ""),
                }
                for i, seg in enumerate(segments)
            ]
        }

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        return output_path
