#!/usr/bin/env python3
"""Remove long silences, optionally skip filler-only captions, and burn subtitles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto-edit a narrated video or audio track.")
    parser.add_argument("input", type=Path, help="Input video/audio file")
    parser.add_argument("--srt", type=Path, default=None, help="Whisper SRT file for subtitle burn-in and filler hints")
    parser.add_argument("--output", type=Path, default=None, help="Output MP4 path")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--min-silence-ms", type=int, default=None)
    parser.add_argument("--silence-threshold-db", type=int, default=None)
    return parser


def load_config(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def detect_keep_ranges(audio_path: Path, silence_threshold: int, min_silence_ms: int) -> list[tuple[float, float]]:
    try:
        from pydub import AudioSegment
        from pydub.silence import detect_nonsilent
    except ImportError as exc:
        raise SystemExit(f"Missing dependency: {exc.name}. Run: pip install -r requirements.txt") from exc

    audio = AudioSegment.from_file(audio_path)
    nonsilent = detect_nonsilent(audio, min_silence_len=min_silence_ms, silence_thresh=silence_threshold)
    if not nonsilent:
        return [(0.0, len(audio) / 1000)]
    return [(start / 1000, end / 1000) for start, end in nonsilent]


def remap_time(seconds: float, keep_ranges: list[tuple[float, float]]) -> float | None:
    elapsed = 0.0
    for start, end in keep_ranges:
        if start <= seconds <= end:
            return elapsed + seconds - start
        if seconds < start:
            return None
        elapsed += max(0.0, end - start)
    return None


def remap_subtitles(srt_path: Path, keep_ranges: list[tuple[float, float]]):
    try:
        import srt
    except ImportError:
        raise SystemExit("Missing dependency: srt. Run: pip install -r requirements.txt")

    remapped = []
    for item in srt.parse(srt_path.read_text(encoding="utf-8")):
        text = item.content.replace("\n", " ").strip()
        if not text:
            continue
        source_start = item.start.total_seconds()
        source_end = item.end.total_seconds()
        start = remap_time(source_start, keep_ranges)
        end = remap_time(source_end, keep_ranges)
        if start is None:
            continue
        if end is None:
            end = start + max(0.1, source_end - source_start)
        if end <= start:
            end = start + 0.1
        remapped.append(
            srt.Subtitle(
                index=len(remapped) + 1,
                start=srt.timedelta(seconds=start),
                end=srt.timedelta(seconds=end),
                content=text,
            )
        )
    return remapped


def build_subtitle_overlays(subtitles, config: dict, video_size: tuple[int, int]):
    try:
        from moviepy import TextClip
    except ImportError:
        try:
            from moviepy.editor import TextClip
        except ImportError as exc:
            raise SystemExit(f"Missing dependency: {exc.name}. Run: pip install -r requirements.txt") from exc

    font = str(config.get("subtitle_font", "/System/Library/Fonts/STHeiti Medium.ttc"))
    font_size = int(config.get("subtitle_font_size", 48))
    margin_bottom = int(config.get("subtitle_margin_bottom", 90))
    max_width = int(video_size[0] * 0.86)
    clips = []
    for item in subtitles:
        text = item.content.strip()
        if not text:
            continue
        start = item.start.total_seconds()
        end = item.end.total_seconds()
        duration = max(0.1, end - start)
        try:
            clip = (
                TextClip(
                    text=text,
                    font=font,
                    font_size=font_size,
                    color="white",
                    stroke_color="black",
                    stroke_width=3,
                    size=(max_width, None),
                    method="caption",
                    text_align="center",
                )
                .with_start(start)
                .with_duration(duration)
                .with_position(("center", video_size[1] - margin_bottom))
            )
        except TypeError:
            clip = (
                TextClip(text, font=font, fontsize=font_size, color="white", stroke_color="black", stroke_width=3)
                .set_start(start)
                .set_duration(duration)
                .set_position(("center", video_size[1] - margin_bottom))
            )
        clips.append(clip)
    return clips


def set_duration(clip, duration: float):
    return clip.with_duration(duration) if hasattr(clip, "with_duration") else clip.set_duration(duration)


def set_audio(clip, audio):
    return clip.with_audio(audio) if hasattr(clip, "with_audio") else clip.set_audio(audio)


def subclip(clip, start: float, end: float):
    return clip.subclipped(start, end) if hasattr(clip, "subclipped") else clip.subclip(start, end)


def main() -> None:
    args = build_parser().parse_args()
    source = args.input.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"Input not found: {source}")

    config = load_config(args.config.expanduser().resolve())
    silence_threshold = args.silence_threshold_db or int(config.get("silence_threshold_db", -42))
    min_silence_ms = args.min_silence_ms or int(config.get("min_silence_ms", 800))
    output = (args.output or source.with_name("05-final-video.mp4")).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, VideoFileClip, concatenate_videoclips
    except ImportError:
        try:
            from moviepy.editor import AudioFileClip, ColorClip, CompositeVideoClip, VideoFileClip, concatenate_videoclips
        except ImportError as exc:
            raise SystemExit(f"Missing dependency: {exc.name}. Run: pip install -r requirements.txt") from exc

    is_video = source.suffix.lower() in {".mp4", ".mov", ".m4v"}
    audio_clip = AudioFileClip(str(source)) if not is_video else None
    base_clip = VideoFileClip(str(source)) if is_video else set_duration(ColorClip((1920, 1080), color=(16, 24, 19)), audio_clip.duration)
    if not is_video:
        base_clip = set_audio(base_clip, audio_clip)

    keep_ranges = detect_keep_ranges(source, silence_threshold, min_silence_ms)
    clips = [subclip(base_clip, start, min(end, base_clip.duration)) for start, end in keep_ranges if end > start]
    edited = concatenate_videoclips(clips, method="compose") if clips else base_clip

    if args.srt and args.srt.exists():
        remapped_subtitles = remap_subtitles(args.srt, keep_ranges)
        if remapped_subtitles:
            import srt

            edited_srt = args.srt.with_name(f"{args.srt.stem}-edited.srt")
            edited_srt.write_text(srt.compose(remapped_subtitles), encoding="utf-8")
            print(f"Wrote {edited_srt}")
        overlays = build_subtitle_overlays(remapped_subtitles, config, tuple(edited.size))
        if overlays:
            edited = CompositeVideoClip([edited, *overlays])

    edited.write_videofile(str(output), codec="libx264", audio_codec="aac", fps=30)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
