#!/usr/bin/env python3
"""Render slide PDF pages to a narrated 16:9 video."""

from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path


SLIDE_MARKER_RE = re.compile(r"\[(?:切換到\s*)?Slide\s*(\d+)[^\]]*\]", re.IGNORECASE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Combine a slide PDF with narration audio.")
    parser.add_argument("--pdf", required=True, type=Path, help="Slide PDF path")
    parser.add_argument("--audio", required=True, type=Path, help="Narration audio path")
    parser.add_argument("--script", required=True, type=Path, help="Markdown script with [切換到 Slide N] markers")
    parser.add_argument("--srt", type=Path, default=None, help="Whisper SRT for total timing reference")
    parser.add_argument("--output", type=Path, required=True, help="Output MP4")
    return parser


def total_srt_seconds(srt_path: Path | None) -> float | None:
    if not srt_path or not srt_path.exists():
        return None
    try:
        import srt
    except ImportError as exc:
        raise SystemExit(f"Missing dependency: {exc.name}. Run: pip install -r requirements.txt") from exc
    entries = list(srt.parse(srt_path.read_text(encoding="utf-8")))
    if not entries:
        return None
    return entries[-1].end.total_seconds()


def slide_timing(script_text: str, audio_duration: float) -> list[tuple[int, float]]:
    matches = list(SLIDE_MARKER_RE.finditer(script_text))
    if not matches:
        return [(1, 0.0)]
    total_chars = max(1, len(script_text))
    timings: list[tuple[int, float]] = []
    for match in matches:
        slide_no = int(match.group(1))
        second = min(audio_duration, (match.start() / total_chars) * audio_duration)
        timings.append((slide_no, second))
    if timings[0][1] > 0:
        timings.insert(0, (timings[0][0], 0.0))
    return timings


def set_duration(clip, duration: float):
    return clip.with_duration(duration) if hasattr(clip, "with_duration") else clip.set_duration(duration)


def set_audio(clip, audio):
    return clip.with_audio(audio) if hasattr(clip, "with_audio") else clip.set_audio(audio)


def resize_width(clip, width: int):
    return clip.resized(width=width) if hasattr(clip, "resized") else clip.resize(width=width)


def main() -> None:
    args = build_parser().parse_args()
    pdf_path = args.pdf.expanduser().resolve()
    audio_path = args.audio.expanduser().resolve()
    script_path = args.script.expanduser().resolve()
    output = args.output.expanduser().resolve()
    for path in (pdf_path, audio_path, script_path):
        if not path.exists():
            raise SystemExit(f"Missing input: {path}")

    try:
        from pdf2image import convert_from_path
        from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
    except ImportError:
        try:
            from pdf2image import convert_from_path
            from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
        except ImportError as exc:
            raise SystemExit(f"Missing dependency: {exc.name}. Run: pip install -r requirements.txt") from exc

    audio = AudioFileClip(str(audio_path))
    duration = total_srt_seconds(args.srt) or audio.duration
    script_text = script_path.read_text(encoding="utf-8")
    timings = slide_timing(script_text, duration)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pages = convert_from_path(str(pdf_path), dpi=160, output_folder=tmp, fmt="png")
        if not pages:
            raise SystemExit("No pages rendered from PDF")
        image_paths = []
        for index, page in enumerate(pages, start=1):
            image_path = Path(tmp) / f"slide-{index:02d}.png"
            page.save(image_path)
            image_paths.append(image_path)

        clips = []
        for idx, (slide_no, start) in enumerate(timings):
            next_start = timings[idx + 1][1] if idx + 1 < len(timings) else duration
            clip_duration = max(0.2, next_start - start)
            image_path = image_paths[min(max(slide_no, 1), len(image_paths)) - 1]
            clips.append(resize_width(set_duration(ImageClip(str(image_path)), clip_duration), 1920))

        video = set_audio(concatenate_videoclips(clips, method="compose"), audio)
        video.write_videofile(str(output), codec="libx264", audio_codec="aac", fps=30)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
