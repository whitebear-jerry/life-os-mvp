#!/usr/bin/env python3
"""Transcribe an audio file with Whisper and write SRT plus plain transcript."""

from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe audio with openai-whisper.")
    parser.add_argument("audio", type=Path, help="Input audio file, e.g. 03-raw-audio.m4a")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for subtitles.srt and transcript.txt")
    parser.add_argument("--model", default="medium", help="Whisper model name, e.g. medium or large-v3")
    parser.add_argument("--language", default="zh", help="Whisper language code")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    audio_path = args.audio.expanduser().resolve()
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")

    output_dir = (args.output_dir or audio_path.parent).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import srt
        import whisper
    except ImportError as exc:
        raise SystemExit(f"Missing dependency: {exc.name}. Run: pip install -r requirements.txt") from exc

    model = whisper.load_model(args.model)
    result = model.transcribe(str(audio_path), language=args.language, verbose=False)

    transcript_lines: list[str] = []
    subtitles: list[object] = []
    for index, segment in enumerate(result.get("segments", []), start=1):
        text = segment.get("text", "").strip()
        if not text:
            continue
        transcript_lines.append(text)
        subtitles.append(
            srt.Subtitle(
                index=index,
                start=timedelta(seconds=float(segment["start"])),
                end=timedelta(seconds=float(segment["end"])),
                content=text,
            )
        )

    (output_dir / "transcript.txt").write_text("\n".join(transcript_lines) + "\n", encoding="utf-8")
    (output_dir / "subtitles.srt").write_text(srt.compose(subtitles), encoding="utf-8")
    print(f"Wrote {output_dir / 'subtitles.srt'}")
    print(f"Wrote {output_dir / 'transcript.txt'}")


if __name__ == "__main__":
    main()
