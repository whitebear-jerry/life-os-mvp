#!/usr/bin/env python3
"""Build a clean episode video plus separate YouTube CC subtitles.

This is the post-EP1 pipeline: cut silence, normalize the clean video, then
transcribe the cut video with Whisper word timestamps. Subtitle segments are
formed by merging complete Whisper segments only; the script never splits a
segment or burns subtitles into the video.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from datetime import timedelta
from fractions import Fraction
from pathlib import Path


DEFAULT_VOCAB_PATH = Path(__file__).with_name("vocab.json")
AUTO_EDITOR_VENV = Path.home() / ".venv-autoeditor" / "bin" / "auto-editor"
TARGET_CHARS = 12
MAX_CHARS = 16
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
OUTPUT_FPS = 60


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cut a screen recording and write clean MP4 + separate SRT.")
    parser.add_argument("input", type=Path, help="Input screen recording, e.g. 03-screen-recording-MVP.mov")
    parser.add_argument("--out-dir", type=Path, default=None, help="Episode output folder. Defaults to input folder.")
    parser.add_argument("--ep", required=True, help="Episode number, e.g. 01")
    parser.add_argument("--model", default="medium", help="Whisper model. Default: medium")
    parser.add_argument("--language", default="zh", help="Whisper language code. Default: zh")
    parser.add_argument("--margin", type=float, default=0.4, help="auto-editor margin in seconds. Default: 0.4")
    parser.add_argument("--vocab", type=Path, default=DEFAULT_VOCAB_PATH, help="Vocabulary replacement JSON path")
    parser.add_argument("--initial-prompt", default=None, help="Optional Whisper initial prompt")
    parser.add_argument("--suffix", default="", help="Suffix before extensions, e.g. -regen for regression tests")
    parser.add_argument("--skip-cut", action="store_true", help="Use an existing clean output video for transcription")
    parser.add_argument("--skip-transcribe", action="store_true", help="Reuse an existing SRT/transcript if present")
    parser.add_argument("--transcribe-only", action="store_true", help="Only write SRT + transcript, not the final MP4")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output files")
    parser.add_argument("--work-dir", type=Path, default=None, help="Local directory for intermediate files")
    parser.add_argument("--keep-work", action="store_true", help="Keep intermediate files")
    return parser


def td(seconds: float) -> timedelta:
    return timedelta(seconds=float(seconds))


def srt_time(value: timedelta) -> str:
    total_ms = round(value.total_seconds() * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def display_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def join_text(left: str, right: str) -> str:
    left = left.strip()
    right = right.strip()
    if not left:
        return right
    if not right:
        return left
    if re.search(r"[A-Za-z0-9]$", left) and re.match(r"[A-Za-z0-9]", right):
        return f"{left} {right}"
    return left + right


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


def find_auto_editor() -> Path:
    if AUTO_EDITOR_VENV.exists():
        return AUTO_EDITOR_VENV
    auto_editor = shutil.which("auto-editor")
    if auto_editor:
        return Path(auto_editor)
    raise SystemExit("auto-editor not found. Expected ~/.venv-autoeditor/bin/auto-editor.")


def find_ffmpeg() -> Path:
    ffmpeg_full = sorted(Path("/opt/homebrew/Cellar/ffmpeg-full").glob("*/bin/ffmpeg"), reverse=True)
    if ffmpeg_full:
        return ffmpeg_full[0]
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return Path(ffmpeg_path)
    raise SystemExit("ffmpeg not found. Install ffmpeg or ffmpeg-full.")


def find_ffprobe() -> Path:
    ffprobe_full = sorted(Path("/opt/homebrew/Cellar/ffmpeg-full").glob("*/bin/ffprobe"), reverse=True)
    if ffprobe_full:
        return ffprobe_full[0]
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        return Path(ffprobe_path)
    raise SystemExit("ffprobe not found. Install ffmpeg or ffmpeg-full.")


def run(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def probe_video(input_path: Path) -> dict[str, float | int | str]:
    ffprobe = find_ffprobe()
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,codec_name:format=duration",
            "-of",
            "json",
            str(input_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    stream = data.get("streams", [{}])[0]
    fps_value = stream.get("avg_frame_rate", "0/1")
    try:
        fps = float(Fraction(fps_value))
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    return {
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "fps": fps,
        "codec": str(stream.get("codec_name", "")),
        "duration": float(data.get("format", {}).get("duration", 0.0)),
    }


def cut_silence(input_path: Path, cut_path: Path, margin: float, force: bool) -> None:
    ensure_writable(cut_path, force)
    auto_editor = find_auto_editor()
    cmd = [
        str(auto_editor),
        str(input_path),
        "--margin",
        f"{margin:g}sec",
        "--no-open",
        "--progress",
        "none",
        "-o",
        str(cut_path),
    ]
    run(cmd)


def normalize_video(input_path: Path, output_path: Path, force: bool) -> None:
    ensure_writable(output_path, force)
    ffmpeg = find_ffmpeg()
    cmd = [
        str(ffmpeg),
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps={OUTPUT_FPS}",
        "-fps_mode",
        "cfr",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run(cmd)


def ensure_writable(path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"Output exists: {path}\nUse --force or --suffix to avoid/replace it.")


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


def atomize_whisper_segments(raw_segments: list[dict], replacements: dict[str, str]) -> list[dict]:
    atoms = []
    for segment in raw_segments:
        words = [word for word in segment.get("words", []) if str(word.get("word", "")).strip()]
        text = apply_vocab(str(segment.get("text", "")).strip(), replacements)
        if not text:
            text = apply_vocab("".join(str(word.get("word", "")).strip() for word in words), replacements)
        if not text:
            continue

        if words:
            start = float(words[0].get("start", segment.get("start", 0.0)))
            end = float(words[-1].get("end", segment.get("end", start)))
        else:
            start = float(segment.get("start", 0.0))
            end = float(segment.get("end", start))
        if end <= start:
            end = start + 0.05
        atoms.append({"start": start, "end": end, "text": text})
    return atoms


def merge_segments(atoms: list[dict]) -> list[dict]:
    merged: list[dict] = []
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current and current["text"].strip():
            merged.append(current)
        current = None

    for atom in atoms:
        if current is None:
            current = dict(atom)
            continue

        candidate_text = join_text(current["text"], atom["text"])
        current_len = display_len(current["text"])
        candidate_len = display_len(candidate_text)
        can_merge = current_len < TARGET_CHARS and candidate_len <= MAX_CHARS
        if can_merge:
            current["text"] = candidate_text
            current["end"] = atom["end"]
        else:
            flush()
            current = dict(atom)
    flush()
    return clean_timing(merged)


def clean_timing(segments: list[dict]) -> list[dict]:
    cleaned = []
    cursor = 0.0
    for segment in segments:
        start = max(float(segment["start"]), cursor)
        end = max(float(segment["end"]), start + 0.05)
        text = segment["text"].strip()
        if not text:
            continue
        cleaned.append({"start": start, "end": end, "text": text})
        cursor = end
    return cleaned


def write_srt(segments: list[dict], srt_path: Path, replacements: dict[str, str]) -> None:
    entries = []
    for index, segment in enumerate(segments, start=1):
        text = apply_vocab(segment["text"].strip(), replacements)
        if not text:
            continue
        entries.append(
            f"{index}\n"
            f"{srt_time(td(segment['start']))} --> {srt_time(td(segment['end']))}\n"
            f"{text}\n"
        )
    srt_path.write_text("\n".join(entries) + "\n", encoding="utf-8")


def write_transcript(text: str, fallback_segments: list[dict], transcript_path: Path, replacements: dict[str, str]) -> None:
    transcript = apply_vocab(text.strip(), replacements)
    if not transcript:
        transcript = "\n".join(segment["text"].strip() for segment in fallback_segments if segment["text"].strip())
    transcript_path.write_text(transcript.rstrip() + "\n", encoding="utf-8")


def output_paths(out_dir: Path, ep: str, suffix: str) -> tuple[Path, Path, Path]:
    ep_number = ep.zfill(2) if ep.isdigit() else ep
    video_path = out_dir / f"05-final-video-autocut{suffix}.mp4"
    srt_path = out_dir / f"EP{ep_number}-字幕-zh-TW-autocut{suffix}.srt"
    transcript_path = out_dir / f"transcript-autocut{suffix}.txt"
    return video_path, srt_path, transcript_path


def default_work_dir(input_path: Path, ep: str, suffix: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"ep{ep}-{input_path.stem}{suffix or ''}").strip("-")
    return Path(tempfile.gettempdir()) / "life-os-episode-pipeline" / safe_name


def default_prompt(replacements: dict[str, str]) -> str:
    terms = sorted(set(replacements.values()) | {"蔡加尼克", "Readmoo", "房貸", "瑣事", "第二大腦", "Pubu", "Notion", "Obsidian"})
    return "、".join(terms)


def cleanup(paths: list[Path], keep_work: bool) -> None:
    if keep_work:
        return
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def main() -> None:
    args = build_parser().parse_args()
    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    out_dir = (args.out_dir or input_path.parent).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = (args.work_dir.expanduser().resolve() if args.work_dir else default_work_dir(input_path, args.ep, args.suffix))
    work_dir.mkdir(parents=True, exist_ok=True)

    video_path, srt_path, transcript_path = output_paths(out_dir, args.ep, args.suffix)
    replacements = load_vocab(args.vocab)
    prompt = args.initial_prompt if args.initial_prompt is not None else default_prompt(replacements)

    if args.skip_transcribe:
        if not srt_path.exists():
            raise SystemExit(f"--skip-transcribe requested but SRT does not exist: {srt_path}")
        print(f"Reusing {srt_path}")
        return

    if not args.transcribe_only:
        ensure_writable(video_path, args.force)
    ensure_writable(srt_path, args.force)
    ensure_writable(transcript_path, args.force)

    transient_paths: list[Path] = []
    cut_path = work_dir / f"{input_path.stem}{args.suffix or '-work'}-cut.mp4"
    normalized_work_path = work_dir / f"{input_path.stem}{args.suffix or '-work'}-normalized.mp4"

    if args.skip_cut:
        if args.transcribe_only:
            transcribe_input = input_path
        else:
            normalize_video(input_path, normalized_work_path, force=True)
            transient_paths.append(normalized_work_path)
            transcribe_input = normalized_work_path
    else:
        cut_silence(input_path, cut_path, args.margin, force=True)
        transient_paths.append(cut_path)
        normalize_video(cut_path, normalized_work_path, force=True)
        transient_paths.append(normalized_work_path)
        transcribe_input = normalized_work_path

    raw_segments, transcript = transcribe(transcribe_input, args.model, args.language, prompt)
    if not raw_segments:
        raise SystemExit("Whisper returned no segments.")
    atoms = atomize_whisper_segments(raw_segments, replacements)
    segments = merge_segments(atoms)
    write_srt(segments, srt_path, replacements)
    write_transcript(transcript, segments, transcript_path, replacements)
    video_info = probe_video(transcribe_input)
    if not args.transcribe_only and transcribe_input != video_path:
        shutil.copy2(transcribe_input, video_path)
    cleanup(transient_paths, args.keep_work)

    print(f"Wrote {srt_path}")
    print(f"Wrote {transcript_path}")
    if not args.transcribe_only:
        print(f"Wrote {video_path}")
    print(f"Subtitle segments: {len(segments)}")
    print(f"Clean video duration: {video_info['duration']:.1f}s")


if __name__ == "__main__":
    main()
