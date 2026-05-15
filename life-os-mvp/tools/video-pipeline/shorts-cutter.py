#!/usr/bin/env python3
"""Cut three vertical shorts from long-form video using script quote markers."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


QUOTE_RE = re.compile(r"✨\s*(?:\*\*)?[「\"]?(.+?)[」\"]?(?:\*\*)?\s*$", re.MULTILINE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cut 3 vertical 60-second shorts.")
    parser.add_argument("--video", required=True, type=Path, help="Long-form video path")
    parser.add_argument("--script", required=True, type=Path, help="Script markdown with ✨ quote markers")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for shorts")
    parser.add_argument("--duration", type=float, default=60.0)
    return parser


def extract_quotes(script_path: Path) -> list[str]:
    text = script_path.read_text(encoding="utf-8")
    return [match.group(1).strip("。 ") for match in QUOTE_RE.finditer(text)][:3]


def subclip(clip, start: float, end: float):
    return clip.subclipped(start, end) if hasattr(clip, "subclipped") else clip.subclip(start, end)


def crop(clip, **kwargs):
    return clip.cropped(**kwargs) if hasattr(clip, "cropped") else clip.crop(**kwargs)


def resize(clip, size: tuple[int, int]):
    return clip.resized(size) if hasattr(clip, "resized") else clip.resize(size)


def center_crop_vertical(clip):
    width, height = clip.size
    target_ratio = 9 / 16
    current_ratio = width / height
    if current_ratio > target_ratio:
        new_width = int(height * target_ratio)
        x1 = (width - new_width) // 2
        return resize(crop(clip, x1=x1, y1=0, width=new_width, height=height), (1080, 1920))
    new_height = int(width / target_ratio)
    y1 = max(0, (height - new_height) // 2)
    return resize(crop(clip, x1=0, y1=y1, width=width, height=new_height), (1080, 1920))


def main() -> None:
    args = build_parser().parse_args()
    video_path = args.video.expanduser().resolve()
    script_path = args.script.expanduser().resolve()
    if not video_path.exists():
        raise SystemExit(f"Video not found: {video_path}")
    if not script_path.exists():
        raise SystemExit(f"Script not found: {script_path}")

    try:
        from moviepy import VideoFileClip
    except ImportError:
        try:
            from moviepy.editor import VideoFileClip
        except ImportError as exc:
            raise SystemExit(f"Missing dependency: {exc.name}. Run: pip install -r requirements.txt") from exc

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    quotes = extract_quotes(script_path) or ["short-1", "short-2", "short-3"]

    video = VideoFileClip(str(video_path))
    step = max(1.0, video.duration / (len(quotes) + 1))
    for index, quote in enumerate(quotes, start=1):
        start = min(max(0.0, step * index - 10), max(0.0, video.duration - args.duration))
        end = min(video.duration, start + args.duration)
        short = center_crop_vertical(subclip(video, start, end))
        output = output_dir / f"short-{index:02d}.mp4"
        short.write_videofile(str(output), codec="libx264", audio_codec="aac", fps=30)
        print(f"Wrote {output} ({quote})")


if __name__ == "__main__":
    main()
