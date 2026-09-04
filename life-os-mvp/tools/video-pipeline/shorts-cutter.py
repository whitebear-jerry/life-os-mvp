#!/usr/bin/env python3
"""Cut three vertical shorts from long-form video using script quote markers."""

from __future__ import annotations

import argparse
import difflib
import re
import unicodedata
from pathlib import Path


QUOTE_RE = re.compile(r"^\s*(?:[-*]\s*)?✨\s*(?:\*\*)?[「\"]?(.+?)[」\"]?(?:\*\*)?\s*$", re.MULTILINE)
EXPECTED_QUOTES = [
    "大腦是用來思考的，不是用來記憶的",
    "別當被瑣事追著跑的倉鼠，當開啟上帝視角的指揮官",
    "我已經外包記下來了，你可以停止發送警報了",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cut 3 vertical 60-second shorts.")
    parser.add_argument("--video", required=True, type=Path, help="Long-form video path")
    parser.add_argument("--script", required=True, type=Path, help="Script markdown with ✨ quote markers")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for shorts")
    parser.add_argument("--srt", type=Path, default=None, help="Edited SRT aligned to the input video")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--mode", choices=["letterbox", "recompose"], default="letterbox")
    return parser


def extract_quotes(script_path: Path) -> list[str]:
    text = script_path.read_text(encoding="utf-8")
    quotes = [clean_quote(match.group(1)) for match in QUOTE_RE.finditer(text)]
    for quote in EXPECTED_QUOTES:
        if all(normalize(quote) not in normalize(existing) for existing in quotes):
            quotes.append(quote)
    return quotes[:3]


def clean_quote(text: str) -> str:
    return text.strip().strip("。.!！?？ ").replace("『", "").replace("』", "")


def normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"[\s，,。.!！?？：「」『』“”\"'()（）【】\[\]、-]", "", normalized)


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


def letterbox_vertical(clip):
    try:
        from moviepy import ColorClip, CompositeVideoClip
    except ImportError:
        from moviepy.editor import ColorClip, CompositeVideoClip

    width, height = clip.size
    scaled_height = int(round(height * (1080 / width)))
    scaled_height += scaled_height % 2
    scaled = resize(clip, (1080, scaled_height))
    background = ColorClip((1080, 1920), color=(0, 0, 0), duration=clip.duration)
    composed = CompositeVideoClip([background, scaled.with_position(("center", "center"))], size=(1080, 1920))
    return composed.with_audio(clip.audio) if hasattr(composed, "with_audio") else composed.set_audio(clip.audio)


def load_srt_items(srt_path: Path):
    try:
        import srt
    except ImportError as exc:
        raise SystemExit(f"Missing dependency: {exc.name}. Run: pip install -r requirements.txt") from exc

    return list(srt.parse(srt_path.read_text(encoding="utf-8")))


def find_quote_time(quote: str, subtitles) -> float | None:
    target = normalize(quote)
    best_score = 0.0
    best_start = None
    for index in range(len(subtitles)):
        for window_size in range(1, 5):
            window = subtitles[index : index + window_size]
            if not window:
                continue
            text = normalize("".join(item.content for item in window))
            if not text:
                continue
            if target in text or text in target:
                return window[0].start.total_seconds()
            score = difflib.SequenceMatcher(None, target, text).ratio()
            if score > best_score:
                best_score = score
                best_start = window[0].start.total_seconds()
    if best_score < 0.48:
        return None
    return best_start


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
    srt_path = (args.srt or video_path.with_name("04-subtitles-edited.srt")).expanduser().resolve()
    if not srt_path.exists():
        raise SystemExit(f"Edited SRT not found: {srt_path}. Run auto-edit-video.py first.")

    quotes = extract_quotes(script_path) or EXPECTED_QUOTES
    subtitles = load_srt_items(srt_path)

    video = VideoFileClip(str(video_path))
    for index, quote in enumerate(quotes, start=1):
        quote_time = find_quote_time(quote, subtitles)
        if quote_time is None:
            raise SystemExit(f"Could not locate quote in SRT: {quote}")
        start = min(max(0.0, quote_time - 15), max(0.0, video.duration - args.duration))
        end = min(video.duration, start + args.duration)
        clip = subclip(video, start, end)
        short = letterbox_vertical(clip) if args.mode == "letterbox" else center_crop_vertical(clip)
        output = output_dir / f"short-{index:02d}.mp4"
        short.write_videofile(str(output), codec="libx264", audio_codec="aac", fps=30)
        print(f"Wrote {output} ({quote}; quote at {quote_time:.2f}s)")


if __name__ == "__main__":
    main()
