#!/usr/bin/env python3
"""Turn a screen recording into a YouTube-ready video with burned subtitles.

V3.3 intentionally does not auto-edit, cut shorts, or generate quote cards.
It keeps the original recording timing intact and only adds Chinese subtitles.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import textwrap
from datetime import timedelta
from pathlib import Path


FONT_CANDIDATES = [
    "/Library/Fonts/SourceHanSansTC-Regular.otf",
    "/Library/Fonts/SourceHanSansTC-Normal.otf",
    "/System/Library/Fonts/STHeiti Medium.ttc",
]
DEFAULT_VOCAB_PATH = Path(__file__).with_name("vocab.json")
BREAK_PUNCTUATION = "，。？！,?!"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Burn Whisper subtitles into a screen recording.")
    parser.add_argument("input", type=Path, help="Input screen recording, e.g. 03-screen-recording-MVP.mov")
    parser.add_argument("--output", type=Path, default=None, help="Output MP4 path")
    parser.add_argument("--srt", type=Path, default=None, help="Output SRT path")
    parser.add_argument("--ass", type=Path, default=None, help="Output ASS path used by ffmpeg")
    parser.add_argument("--transcript", type=Path, default=None, help="Output plain transcript path")
    parser.add_argument("--model", default="large-v3", help="Whisper model, e.g. medium or large-v3")
    parser.add_argument("--language", default="zh", help="Whisper language code. Use zh for Chinese.")
    parser.add_argument("--font", type=Path, default=None, help="Chinese font file for subtitles")
    parser.add_argument("--font-name", default=None, help="ASS font family name")
    parser.add_argument("--font-size", type=int, default=54, help="ASS subtitle font size")
    parser.add_argument("--margin-v", type=int, default=92, help="ASS bottom margin")
    parser.add_argument("--max-chars", type=int, default=14, help="Target max chars per subtitle segment")
    parser.add_argument("--vocab", type=Path, default=DEFAULT_VOCAB_PATH, help="Vocabulary replacement JSON path")
    parser.add_argument("--initial-prompt", default=None, help="Optional Whisper initial prompt")
    parser.add_argument("--skip-transcribe", action="store_true", help="Reuse existing SRT and ASS if present")
    parser.add_argument("--transcribe-only", action="store_true", help="Only write SRT/transcript, do not burn video")
    return parser


def pick_font(explicit_font: Path | None) -> tuple[Path, str]:
    if explicit_font:
        font = explicit_font.expanduser().resolve()
        if not font.exists():
            raise SystemExit(f"Font not found: {font}")
        return font, font.stem

    for candidate in FONT_CANDIDATES:
        font = Path(candidate)
        if font.exists():
            if "SourceHanSans" in font.name:
                return font, "Source Han Sans TC"
            if "STHeiti" in font.name:
                return font, "STHeiti"
            return font, font.stem
    raise SystemExit("No Chinese font found. Install Source Han Sans TC or provide --font.")


def td(seconds: float) -> timedelta:
    return timedelta(seconds=float(seconds))


def srt_time(value: timedelta) -> str:
    total_ms = round(value.total_seconds() * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def ass_time(seconds: float) -> str:
    total_cs = round(seconds * 100)
    hours, remainder = divmod(total_cs, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    sec, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{sec:02d}.{cs:02d}"


def wrap_cjk(text: str, width: int = 18) -> str:
    compact = " ".join(text.split())
    if len(compact) <= width:
        return compact
    return "\\N".join(textwrap.wrap(compact, width=width, break_long_words=True, replace_whitespace=False))


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "（").replace("}", "）")


def load_vocab(vocab_path: Path | None) -> dict[str, str]:
    if not vocab_path:
        return {}
    path = vocab_path.expanduser()
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    replacements = data.get("replacements", data) if isinstance(data, dict) else {}
    return {str(wrong): str(correct) for wrong, correct in replacements.items()}


def apply_vocab(text: str, replacements: dict[str, str]) -> str:
    corrected = text
    for wrong, correct in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        corrected = corrected.replace(wrong, correct)
    return corrected


def display_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def should_break(text: str) -> bool:
    return text.rstrip().endswith(tuple(BREAK_PUNCTUATION))


def join_piece(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    if re.search(r"[A-Za-z0-9]$", left) and re.match(r"[A-Za-z0-9]", right):
        return f"{left} {right}"
    return left + right


def split_long_word(word: dict, max_chars: int) -> list[dict]:
    text = str(word.get("word", "")).strip()
    if not text or display_len(text) <= max_chars:
        return [word]

    start = float(word.get("start", 0))
    end = float(word.get("end", start))
    chars = list(text)
    chunks = ["".join(chars[index : index + max_chars]) for index in range(0, len(chars), max_chars)]
    duration = max(end - start, 0.01)
    total_chars = max(len(chars), 1)

    split_words = []
    cursor = start
    elapsed_chars = 0
    for chunk in chunks:
        elapsed_chars += len(chunk)
        chunk_end = start + duration * elapsed_chars / total_chars
        split_words.append({"word": chunk, "start": cursor, "end": chunk_end})
        cursor = chunk_end
    return split_words


def collect_words(segments: list[dict], replacements: dict[str, str], max_chars: int) -> list[dict]:
    words = []
    for segment in segments:
        segment_words = segment.get("words") or []
        if not segment_words:
            text = apply_vocab(str(segment.get("text", "")).strip(), replacements)
            if text:
                segment_words = [
                    {
                        "word": text,
                        "start": float(segment["start"]),
                        "end": float(segment["end"]),
                    }
                ]
        for word in segment_words:
            text = apply_vocab(str(word.get("word", "")).strip(), replacements)
            if not text:
                continue
            normalized = {
                "word": text,
                "start": float(word.get("start", segment.get("start", 0))),
                "end": float(word.get("end", segment.get("end", word.get("start", 0)))),
            }
            words.extend(split_long_word(normalized, max_chars))
    return words


def resegment_words(words: list[dict], max_chars: int, min_duration: float = 1.0) -> list[dict]:
    segments = []
    current_words = []

    def flush() -> None:
        nonlocal current_words
        if not current_words:
            return
        text = ""
        for item in current_words:
            text = join_piece(text, item["word"])
        segments.append(
            {
                "start": float(current_words[0]["start"]),
                "end": float(current_words[-1]["end"]),
                "text": text.strip(),
            }
        )
        current_words = []

    for word in words:
        candidate_text = ""
        for item in current_words:
            candidate_text = join_piece(candidate_text, item["word"])
        candidate_text = join_piece(candidate_text, word["word"])
        over_limit = current_words and display_len(candidate_text) > max_chars
        punct_break = current_words and should_break(current_words[-1]["word"]) and display_len(candidate_text) >= 8
        if over_limit or punct_break:
            flush()
        current_words.append(word)
    flush()

    return merge_short_segments(segments, min_duration, max_chars)


def merge_short_segments(segments: list[dict], min_duration: float, max_chars: int) -> list[dict]:
    merged = []
    for segment in segments:
        duration = float(segment["end"]) - float(segment["start"])
        if (
            merged
            and duration < min_duration
            and display_len(merged[-1]["text"]) + display_len(segment["text"]) <= max_chars + 2
        ):
            merged[-1]["text"] = join_piece(merged[-1]["text"], segment["text"])
            merged[-1]["end"] = segment["end"]
        else:
            merged.append(segment)

    index = 0
    while index < len(merged) - 1:
        duration = float(merged[index]["end"]) - float(merged[index]["start"])
        if duration < min_duration and display_len(merged[index]["text"]) + display_len(merged[index + 1]["text"]) <= max_chars + 2:
            merged[index]["text"] = join_piece(merged[index]["text"], merged[index + 1]["text"])
            merged[index]["end"] = merged[index + 1]["end"]
            del merged[index + 1]
        else:
            index += 1
    return merged


def prepare_subtitle_segments(segments: list[dict], replacements: dict[str, str], max_chars: int) -> list[dict]:
    words = collect_words(segments, replacements, max_chars)
    if not words:
        return [
            {**segment, "text": apply_vocab(str(segment.get("text", "")).strip(), replacements)}
            for segment in segments
            if str(segment.get("text", "")).strip()
        ]
    return resegment_words(words, max_chars=max_chars)


def write_srt(segments: list[dict], srt_path: Path, replacements: dict[str, str] | None = None) -> None:
    replacements = replacements or {}
    entries = []
    index = 1
    for segment in segments:
        text = apply_vocab(segment.get("text", "").strip(), replacements)
        if not text:
            continue
        entries.append(
            f"{index}\n"
            f"{srt_time(td(segment['start']))} --> {srt_time(td(segment['end']))}\n"
            f"{text}\n"
        )
        index += 1
    srt_path.write_text("\n".join(entries) + "\n", encoding="utf-8")


def read_srt(srt_path: Path) -> list[dict]:
    text = srt_path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", text.strip())
    segments = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        timing = lines[1]
        match = re.match(r"(.+?)\s+-->\s+(.+)", timing)
        if not match:
            continue
        segments.append(
            {
                "start": parse_srt_time(match.group(1)),
                "end": parse_srt_time(match.group(2)),
                "text": " ".join(line.strip() for line in lines[2:] if line.strip()),
            }
        )
    return segments


def parse_srt_time(value: str) -> float:
    hours, minutes, rest = value.strip().split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def probe_video_resolution(input_path: Path) -> tuple[int, int]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 1920, 1080
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            str(input_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    width, height = result.stdout.strip().split("x")
    return int(width), int(height)


def write_ass(
    segments: list[dict],
    ass_path: Path,
    font_name: str,
    font_size: int,
    margin_v: int,
    play_res_x: int,
    play_res_y: int,
    replacements: dict[str, str] | None = None,
) -> None:
    replacements = replacements or {}
    header = f"""[Script Info]
ScriptType: v4.00+
ScaledBorderAndShadow: yes
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00111111,&H99000000,0,0,0,0,100,100,0,0,1,4,0,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for segment in segments:
        text = apply_vocab(segment.get("text", "").strip(), replacements)
        if not text:
            continue
        wrapped = ass_escape(wrap_cjk(text))
        lines.append(
            f"Dialogue: 0,{ass_time(float(segment['start']))},{ass_time(float(segment['end']))},"
            f"Default,,0,0,0,,{wrapped}\n"
        )
    ass_path.write_text("".join(lines), encoding="utf-8")


def transcribe(input_path: Path, model_name: str, language: str, initial_prompt: str | None) -> tuple[list[dict], str]:
    try:
        import whisper
    except ImportError as exc:
        raise SystemExit("Missing dependency: openai-whisper. Run: pip install -r tools/video-pipeline/requirements.txt") from exc

    device, fp16 = select_whisper_device()
    try:
        model = whisper.load_model(model_name, device=device)
    except NotImplementedError:
        if device == "mps":
            print("MPS backend is unavailable for this Whisper model; falling back to CPU.")
            device, fp16 = "cpu", False
            model = whisper.load_model(model_name, device=device)
        else:
            raise
    result = model.transcribe(
        str(input_path),
        language=language,
        verbose=False,
        initial_prompt=initial_prompt,
        word_timestamps=True,
        fp16=fp16,
    )
    return list(result.get("segments", [])), str(result.get("text", "")).strip()


def select_whisper_device() -> tuple[str, bool]:
    try:
        import torch
    except ImportError:
        return "cpu", False
    if torch.cuda.is_available():
        return "cuda", True
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps", True
    return "cpu", False


def burn_subtitles(input_path: Path, output_path: Path, ass_path: Path, fonts_dir: Path) -> None:
    # FFmpeg filter arguments need their own quoting because ':' separates options
    # and spaces/non-ASCII paths are common under Google Drive on macOS.
    ass_filter = f"ass=filename='{ass_path}':fontsdir='{fonts_dir}'"
    ffmpeg_bin = find_ffmpeg()
    cmd = [
        str(ffmpeg_bin),
        "-y",
        "-i",
        str(input_path),
        "-vf",
        ass_filter,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def find_ffmpeg() -> Path:
    ffmpeg_full = sorted(Path("/opt/homebrew/Cellar/ffmpeg-full").glob("*/bin/ffmpeg"), reverse=True)
    if ffmpeg_full:
        return ffmpeg_full[0]
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return Path(ffmpeg_path)
    raise SystemExit("ffmpeg not found. Install ffmpeg or ffmpeg-full.")


def main() -> None:
    args = build_parser().parse_args()
    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    output_path = (args.output or input_path.with_name("05-final-video-MVP.mp4")).expanduser().resolve()
    srt_path = (args.srt or input_path.with_name("04-subtitles-screen-MVP.srt")).expanduser().resolve()
    ass_path = (args.ass or input_path.with_name("04-subtitles-screen-MVP.ass")).expanduser().resolve()
    transcript_path = (args.transcript or input_path.with_name("transcript-screen-MVP.txt")).expanduser().resolve()
    for path in (output_path, srt_path, ass_path, transcript_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    replacements = load_vocab(args.vocab)
    font_path, detected_font_name = pick_font(args.font)
    font_name = args.font_name or detected_font_name
    play_res_x, play_res_y = probe_video_resolution(input_path)

    if args.skip_transcribe and srt_path.exists() and ass_path.exists():
        print(f"Reusing {srt_path}")
        segments = read_srt(srt_path)
        write_ass(segments, ass_path, font_name, args.font_size, args.margin_v, play_res_x, play_res_y, replacements)
        print(f"Regenerated {ass_path}")
    else:
        raw_segments, transcript = transcribe(input_path, args.model, args.language, args.initial_prompt)
        if not raw_segments:
            raise SystemExit("Whisper returned no segments.")
        segments = prepare_subtitle_segments(raw_segments, replacements, args.max_chars)
        write_srt(segments, srt_path, replacements)
        transcript_path.write_text(transcript + "\n", encoding="utf-8")
        print(f"Wrote {srt_path}")
        if args.transcribe_only:
            print(f"Wrote {transcript_path}")
            return
        write_ass(segments, ass_path, font_name, args.font_size, args.margin_v, play_res_x, play_res_y, replacements)
        print(f"Wrote {ass_path}")
        print(f"Wrote {transcript_path}")

    burn_subtitles(input_path, output_path, ass_path, font_path.parent)
    print(f"Wrote {output_path}")
    print(f"Subtitle font: {font_name} ({font_path})")


if __name__ == "__main__":
    main()
