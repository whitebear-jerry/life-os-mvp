#!/usr/bin/env python3
"""Build a clean episode video plus separate YouTube CC subtitles.

This is the post-EP1 pipeline: cut silence, normalize the clean video, then
transcribe the cut video with Whisper word timestamps. Subtitle segments are
formed by merging complete Whisper segments only; the script never splits a
segment or burns subtitles into the video.
"""

from __future__ import annotations

import argparse
import difflib
import html
import importlib.util
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
TARGET_CHARS = 20
MAX_CHARS = 24
MIN_SPLIT_CHARS = 6
SOFT_SPLIT_MIN_CHARS = 12
PAUSE_GAP_SECONDS = 0.42
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
OUTPUT_FPS = 60
HARD_BREAK_CHARS = "。！？!?"
SOFT_BREAK_CHARS = "，、；：,;"
CLOSING_BREAK_CHARS = "」』）)]"
SCRIPT_MATCH_RATIO = 0.86
SCRIPT_WINDOW_MATCH_RATIO = 0.78
PUNCTUATION_RESTORE_RATIO = 0.80
SCRIPT_MAX_SEGMENT_WINDOW = 5
SCRIPT_MAX_CHUNK_WINDOW = 3
PROMPT_TERMS = {
    "Readmoo",
    "Pubu",
    "Kobo",
    "Notion",
    "Obsidian",
    "Evernote",
    "蔡加尼克",
    "房貸",
    "瑣事",
    "第二大腦",
    "心靈 NAS",
    "降噪人生",
    "杏仁核",
    "微習慣",
    "自動導航",
    "習慣迴圈",
    "多巴胺",
    "反脆弱躺平術",
}
PROTECTED_SPLIT_TERMS = PROMPT_TERMS | {
    "大腦根本",
    "將近38倍",
    "起跑動作",
    "超小行動",
    "心智安全氣囊",
}
PUNCTUATION_RESTORE_RULES = [
    (r"結果呢", "結果呢？"),
    (r"第一(?=[，,是])", "第一"),
    (r"第二(?=[，,是])", "第二"),
    (r"第三(?=[，,是])", "第三"),
    (r"我是白熊(?=今天|點選|我們)", "我是白熊。"),
    (r"今天要告訴你(?=這)", "今天要告訴你，"),
    (r"不是你沒毅力(?=你也|也)", "不是你沒毅力，"),
    (r"不是沒有自制力(?=不信)", "不是沒有自制力。"),
    (r"完全不需要勉強自己(?=我們來看)", "完全不需要勉強自己。"),
    (r"我們來看阿翔(?=阿翔)", "我們來看阿翔。"),
    (r"為什麼會這樣(?=請|$)", "為什麼會這樣？"),
    (r"第一步(?=找到)", "第一步，"),
    (r"第二步(?=設計)", "第二步，"),
    (r"第三步(?=完成)", "第三步，"),
    (r"反脆弱躺平術(?=我會|$)", "反脆弱躺平術。"),
]
SCRIPT_PATH_CANDIDATES = ("02-script.md", "02-script-web.md")


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
    parser.add_argument("--skip-trim", action="store_true", help="Skip semantic duplicate trimming and stop at autocut outputs")
    parser.add_argument("--trim-threshold", type=float, default=0.78, help="Duplicate trim similarity threshold. Default: 0.78")
    parser.add_argument("--trim-gap", type=int, default=12, help="Duplicate trim max lookahead gap in subtitle blocks. Default: 12")
    parser.add_argument("--trim-dry-run", action="store_true", help="Print duplicate trim cuts without writing trimmed outputs")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier for final outputs. Default: 1.0")
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


def ends_with_break(text: str, break_chars: str) -> bool:
    stripped = text.strip()
    while stripped and stripped[-1] in CLOSING_BREAK_CHARS:
        stripped = stripped[:-1].rstrip()
    return bool(stripped) and stripped[-1] in break_chars


def ends_with_hard_break(text: str) -> bool:
    return ends_with_break(text, HARD_BREAK_CHARS)


def ends_with_soft_break(text: str) -> bool:
    return ends_with_break(text, SOFT_BREAK_CHARS)


def normalize_match_text(text: str) -> str:
    return re.sub(r"[\s，。、；：！？!?,.;:「」『』（）()\[\]【】《》“”\"'`—…-]+", "", text)


def atom_text(atoms: list[dict]) -> str:
    text = ""
    for atom in atoms:
        text = join_text(text, str(atom["text"]))
    return text


def build_segment(atoms: list[dict]) -> dict:
    return {"start": atoms[0]["start"], "end": atoms[-1]["end"], "text": atom_text(atoms)}


def split_timed_text(text: str, start: float, end: float) -> list[dict]:
    text = text.strip()
    if not text:
        return []
    pieces = [piece.strip() for piece in re.findall(rf".*?[{re.escape(HARD_BREAK_CHARS + SOFT_BREAK_CHARS)}]+|.+$", text) if piece.strip()]
    if len(pieces) == 1 and display_len(text) > MAX_CHARS:
        pieces = split_text_for_subtitles(text)
    if len(pieces) <= 1:
        return [{"start": start, "end": end, "text": text}]

    total_len = sum(max(display_len(piece), 1) for piece in pieces)
    cursor = start
    atoms: list[dict] = []
    duration = max(end - start, 0.05)
    for index, piece in enumerate(pieces):
        if index == len(pieces) - 1:
            piece_end = end
        else:
            piece_end = min(end, cursor + duration * max(display_len(piece), 1) / total_len)
        atoms.append({"start": cursor, "end": max(piece_end, cursor + 0.01), "text": piece})
        cursor = piece_end
    return atoms


def has_break_punctuation(text: str) -> bool:
    return any(char in HARD_BREAK_CHARS + SOFT_BREAK_CHARS for char in text)


def is_break_punctuation(char: str) -> bool:
    return char in HARD_BREAK_CHARS + SOFT_BREAK_CHARS


def inside_protected_term(text: str) -> bool:
    normalized = normalize_match_text(text)
    if not normalized:
        return False
    for term in PROTECTED_SPLIT_TERMS:
        term_norm = normalize_match_text(term)
        if len(term_norm) < 3 or normalized.endswith(term_norm):
            continue
        for split_at in range(1, len(term_norm)):
            if normalized.endswith(term_norm[:split_at]):
                return True
    return False


def split_text_for_subtitles(text: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for char in text.strip():
        current += char
        if char in HARD_BREAK_CHARS:
            if current.strip():
                chunks.append(current.strip())
            current = ""
            continue
        if char in SOFT_BREAK_CHARS and display_len(current) >= SOFT_SPLIT_MIN_CHARS:
            if current.strip():
                chunks.append(current.strip())
            current = ""
            continue
        if display_len(current) >= MAX_CHARS and not inside_protected_term(current):
            if current.strip():
                chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks


def merge_short_segments(segments: list[dict]) -> list[dict]:
    merged: list[dict] = []
    pending_first: dict | None = None

    for segment in segments:
        text = segment["text"].strip()
        if not text:
            continue

        current = segment
        if pending_first is not None:
            current = {
                "start": pending_first["start"],
                "end": segment["end"],
                "text": join_text(pending_first["text"], text),
            }
            pending_first = None

        if display_len(current["text"]) >= MIN_SPLIT_CHARS:
            merged.append(current)
            continue

        if merged:
            previous = merged[-1]
            merged[-1] = {
                "start": previous["start"],
                "end": current["end"],
                "text": join_text(previous["text"], current["text"]),
            }
        else:
            pending_first = current

    if pending_first is not None:
        merged.append(pending_first)

    return clean_timing(merged)


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


def load_trim_duplicate_takes():
    trim_path = Path(__file__).with_name("trim-duplicates.py")
    spec = importlib.util.spec_from_file_location("trim_duplicates_cli", trim_path)
    if not spec or not spec.loader:
        raise SystemExit(f"Unable to load trim duplicate module: {trim_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.trim_duplicate_takes


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


def atomize_whisper_segments(raw_segments: list[dict]) -> list[dict]:
    atoms = []
    for segment in raw_segments:
        words = [word for word in segment.get("words", []) if str(word.get("word", "")).strip()]
        text = str(segment.get("text", "")).strip()

        if words:
            for word in words:
                word_text = str(word.get("word", "")).strip()
                if not word_text:
                    continue
                start = float(word.get("start", segment.get("start", 0.0)))
                end = float(word.get("end", segment.get("end", start)))
                if end <= start:
                    end = start + 0.05
                atoms.extend(split_timed_text(word_text, start, end))
            continue

        if not text:
            continue

        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        if end <= start:
            end = start + 0.05
        atoms.extend(split_timed_text(text, start, end))
    return atoms


def merge_segments(atoms: list[dict]) -> list[dict]:
    merged: list[dict] = []
    current: list[dict] = []

    def flush() -> None:
        nonlocal current
        if current:
            segment = build_segment(current)
            if segment["text"].strip():
                merged.append(segment)
        current = []

    def split_at_soft_break(candidate: list[dict]) -> int | None:
        best_index = None
        left_text = ""
        for index, atom in enumerate(candidate[:-1], start=1):
            left_text = join_text(left_text, str(atom["text"]))
            left_len = display_len(left_text)
            if left_len < SOFT_SPLIT_MIN_CHARS:
                continue
            if ends_with_soft_break(left_text) and left_len <= MAX_CHARS:
                best_index = index
        return best_index

    for atom in atoms:
        if not current:
            current = [atom]
            if ends_with_hard_break(atom_text(current)):
                flush()
            continue

        current_text = atom_text(current)
        gap = float(atom["start"]) - float(current[-1]["end"])
        if ends_with_hard_break(current_text) or (gap > PAUSE_GAP_SECONDS and display_len(current_text) >= MIN_SPLIT_CHARS):
            flush()
            current = [atom]
            if ends_with_hard_break(atom_text(current)):
                flush()
            continue

        candidate = current + [atom]
        candidate_text = atom_text(candidate)
        candidate_len = display_len(candidate_text)
        if candidate_len <= MAX_CHARS:
            current = candidate
            if ends_with_hard_break(candidate_text):
                flush()
            continue

        split_index = split_at_soft_break(candidate)
        if split_index:
            merged.append(build_segment(candidate[:split_index]))
            current = candidate[split_index:]
            if current and ends_with_hard_break(atom_text(current)):
                flush()
            continue

        if display_len(current_text) >= TARGET_CHARS:
            flush()
            current = [atom]
        else:
            current = candidate
    flush()
    return merge_short_segments(clean_timing(merged))


def apply_vocab_to_segments(segments: list[dict], replacements: dict[str, str]) -> list[dict]:
    corrected = []
    for segment in segments:
        text = apply_vocab(segment["text"].strip(), replacements)
        if not text:
            continue
        corrected.append({**segment, "text": text})
    return corrected


def restore_rule_punctuation(text: str) -> str:
    restored = text.strip()
    if not restored:
        return restored
    for pattern, replacement in PUNCTUATION_RESTORE_RULES:
        restored = re.sub(pattern, replacement, restored)
    restored = re.sub(r"([。！？!?])([。！？!?])+", r"\1", restored)
    restored = re.sub(r"([，、；：,;])([，、；：,;])+", r"\1", restored)
    return restored


def punctuation_after_reference_chars(reference: str) -> tuple[str, list[str]]:
    normalized_chars: list[str] = []
    punctuation_after: list[str] = []
    last_index = -1

    for char in reference:
        if is_break_punctuation(char):
            if last_index >= 0 and char not in punctuation_after[last_index]:
                punctuation_after[last_index] += char
            continue
        if normalize_match_text(char):
            normalized_chars.append(char)
            punctuation_after.append("")
            last_index += 1

    return "".join(normalized_chars), punctuation_after


def content_char_positions(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    positions: list[int] = []
    for index, char in enumerate(text):
        if normalize_match_text(char):
            chars.append(char)
            positions.append(index)
    return "".join(chars), positions


def existing_punctuation_after(text: str, index: int) -> bool:
    cursor = index + 1
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor < len(text) and is_break_punctuation(text[cursor])


def align_reference_indices(asr_norm: str, reference_norm: str) -> dict[int, int]:
    mapping: dict[int, int] = {}
    matcher = difflib.SequenceMatcher(None, asr_norm, reference_norm)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                mapping[i1 + offset] = j1 + offset
            continue
        if tag != "replace":
            continue
        asr_len = i2 - i1
        ref_len = j2 - j1
        if asr_len <= 0 or ref_len <= 0:
            continue
        for offset in range(asr_len):
            if asr_len == 1:
                ref_offset = 0
            else:
                ref_offset = round(offset * (ref_len - 1) / (asr_len - 1))
            mapping[i1 + offset] = j1 + ref_offset
    return mapping


def transfer_script_punctuation(asr_text: str, reference_text: str) -> str:
    asr_norm, asr_positions = content_char_positions(asr_text)
    reference_norm, reference_punctuation = punctuation_after_reference_chars(reference_text)
    if len(asr_norm) < MIN_SPLIT_CHARS or len(reference_norm) < MIN_SPLIT_CHARS:
        return asr_text

    mapping = align_reference_indices(asr_norm, reference_norm)
    insertions: dict[int, str] = {}
    for asr_char_index, reference_char_index in mapping.items():
        if reference_char_index >= len(reference_punctuation):
            continue
        punctuation = reference_punctuation[reference_char_index]
        if not punctuation:
            continue
        original_index = asr_positions[asr_char_index]
        if existing_punctuation_after(asr_text, original_index):
            continue
        insertions[original_index] = insertions.get(original_index, "") + punctuation

    if not insertions:
        return asr_text

    output: list[str] = []
    for index, char in enumerate(asr_text):
        output.append(char)
        if index in insertions:
            output.append(insertions[index])
    restored = "".join(output)
    restored = re.sub(r"([。！？!?])([。！？!?])+", r"\1", restored)
    restored = re.sub(r"([，、；：,;])([，、；：,;])+", r"\1", restored)
    return restored


def best_script_punctuation_match(text: str, script_chunks: list[str], cursor: int) -> tuple[str | None, int]:
    normalized = normalize_match_text(text)
    if len(normalized) < MIN_SPLIT_CHARS:
        return None, cursor

    best_text = None
    best_index = cursor
    best_ratio = 0.0
    start = max(0, cursor - 6)
    end = min(len(script_chunks), cursor + 22)
    for chunk_index in range(start, end):
        for chunk_window in range(1, min(SCRIPT_MAX_CHUNK_WINDOW + 1, len(script_chunks) - chunk_index) + 1):
            reference = "".join(script_chunks[chunk_index : chunk_index + chunk_window])
            reference_norm = normalize_match_text(reference)
            if len(reference_norm) < MIN_SPLIT_CHARS:
                continue
            length_ratio = len(normalized) / max(len(reference_norm), 1)
            if not 0.68 <= length_ratio <= 1.48:
                continue
            ratio = difflib.SequenceMatcher(None, normalized, reference_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_text = reference
                best_index = chunk_index + chunk_window

    if best_text and best_ratio >= PUNCTUATION_RESTORE_RATIO and has_break_punctuation(best_text):
        return best_text, best_index
    return None, cursor


def restore_punctuation_to_raw_segments(raw_segments: list[dict], script_chunks: list[str]) -> list[dict]:
    restored_segments = []
    script_cursor = 0
    for segment in raw_segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            restored_segments.append(segment)
            continue

        restored_text = restore_rule_punctuation(text)
        script_text, next_cursor = best_script_punctuation_match(restored_text, script_chunks, script_cursor)
        if script_text:
            restored_text = transfer_script_punctuation(restored_text, script_text)
            script_cursor = max(script_cursor, next_cursor)

        if restored_text != text and has_break_punctuation(restored_text):
            # Use proportional timing from the restored sentence text so the
            # restored punctuation is visible before segmentation.
            restored_segments.append({**segment, "text": restored_text, "words": []})
        else:
            restored_segments.append({**segment, "text": restored_text})
    return restored_segments


def strip_html_tags(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def is_dialogue_span_style(style: str) -> bool:
    normalized = re.sub(r"\s+", "", style).lower()
    return any(
        token in normalized
        for token in (
            "color:#1a9c4a",
            "color:#1565c0",
            "color:#1a73e8",
            "color:#2563eb",
            "color:#1d4ed8",
            "color:#0070c0",
            "color:blue",
        )
    )


def extract_dialogue_span_lines(markdown: str) -> list[str]:
    pattern = re.compile(
        r"<span\b[^>]*style=[\"']([^\"']*)[\"'][^>]*>(.*?)</span>",
        re.IGNORECASE | re.DOTALL,
    )
    lines = []
    for match in pattern.finditer(markdown):
        if not is_dialogue_span_style(match.group(1)):
            continue
        text = strip_html_tags(match.group(2))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            lines.append(text)
    return lines


def strip_script_markup(line: str) -> str:
    line = strip_html_tags(line)
    line = re.sub(r"`?\[[^\]]+\]`?", "", line)
    line = re.sub(r"[（(][^）)]*(?:→|按|跳出|Slide|slide|標籤|字卡|泡泡)[^）)]*[）)]", "", line)
    line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
    line = re.sub(r"[`*_]", "", line)
    return line.strip()


def split_script_chunks(text: str) -> list[str]:
    chunks = []
    for piece in re.findall(rf".*?[{re.escape(HARD_BREAK_CHARS)}]+|.+$", text):
        cleaned = piece.strip()
        if cleaned:
            chunks.append(cleaned)
    return chunks


def chunks_from_script_lines(lines: list[str]) -> list[str]:
    chunks: list[str] = []
    for line in lines:
        cleaned = strip_script_markup(line)
        if not cleaned or cleaned.startswith(("[", "【")):
            continue
        if not re.search(r"[\u4e00-\u9fffA-Za-z0-9]", cleaned):
            continue
        chunks.extend(split_script_chunks(cleaned))
    return chunks


def time_text_chunks(chunks: list[str], start: float, end: float) -> list[dict]:
    subtitle_chunks: list[str] = []
    for chunk in chunks:
        subtitle_chunks.extend(split_text_for_subtitles(chunk))
    subtitle_chunks = [chunk for chunk in subtitle_chunks if chunk.strip()]
    if not subtitle_chunks:
        return []

    duration = max(end - start, 0.05)
    total_len = sum(max(display_len(chunk), 1) for chunk in subtitle_chunks)
    cursor = start
    segments = []
    for index, chunk in enumerate(subtitle_chunks):
        if index == len(subtitle_chunks) - 1:
            chunk_end = end
        else:
            chunk_end = min(end, cursor + duration * max(display_len(chunk), 1) / total_len)
        segments.append({"start": cursor, "end": max(chunk_end, cursor + 0.05), "text": chunk})
        cursor = chunk_end
    return segments


def load_script_chunks(script_path: Path) -> list[str]:
    if not script_path.exists():
        return []

    markdown = script_path.read_text(encoding="utf-8")
    dialogue_lines = extract_dialogue_span_lines(markdown)
    if dialogue_lines:
        return chunks_from_script_lines(dialogue_lines)

    lines: list[str] = []
    in_frontmatter = False
    frontmatter_seen = False
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "---" and not frontmatter_seen:
            in_frontmatter = True
            frontmatter_seen = True
            continue
        if line == "---" and in_frontmatter:
            in_frontmatter = False
            continue
        if in_frontmatter:
            continue
        if line.startswith("## 🎛️") or "按鍵速查" in line:
            break
        if line.startswith(("#", ">", "|", "---")):
            continue
        lines.append(line)
    return chunks_from_script_lines(lines)


def find_script_path(out_dir: Path) -> Path | None:
    for filename in SCRIPT_PATH_CANDIDATES:
        path = out_dir / filename
        if path.exists():
            return path
    return None


def correct_segments_with_script(segments: list[dict], script_chunks: list[str]) -> tuple[list[dict], int]:
    if not script_chunks:
        return segments, 0

    corrected: list[dict] = []
    script_cursor = 0
    correction_count = 0
    segment_index = 0

    while segment_index < len(segments):
        best_match = None
        search_start = max(0, script_cursor - 5)
        search_end = min(len(script_chunks), script_cursor + 20)
        for segment_window in range(1, min(SCRIPT_MAX_SEGMENT_WINDOW, len(segments) - segment_index) + 1):
            segment_slice = segments[segment_index : segment_index + segment_window]
            combined_text = "".join(segment["text"].strip() for segment in segment_slice)
            combined_norm = normalize_match_text(combined_text)
            if len(combined_norm) < MIN_SPLIT_CHARS:
                continue

            for chunk_index in range(search_start, search_end):
                for chunk_window in range(1, min(SCRIPT_MAX_CHUNK_WINDOW, len(script_chunks) - chunk_index) + 1):
                    reference_chunks = script_chunks[chunk_index : chunk_index + chunk_window]
                    reference_text = "".join(reference_chunks)
                    reference_norm = normalize_match_text(reference_text)
                    if len(reference_norm) < MIN_SPLIT_CHARS:
                        continue
                    length_ratio = len(combined_norm) / max(len(reference_norm), 1)
                    if not 0.70 <= length_ratio <= 1.45:
                        continue
                    ratio = difflib.SequenceMatcher(None, combined_norm, reference_norm).ratio()
                    if ratio < SCRIPT_WINDOW_MATCH_RATIO:
                        continue
                    score = ratio - abs(1.0 - length_ratio) * 0.08 + segment_window * 0.002
                    if best_match is None or score > best_match["score"]:
                        best_match = {
                            "score": score,
                            "ratio": ratio,
                            "segment_window": segment_window,
                            "chunk_index": chunk_index,
                            "chunk_window": chunk_window,
                            "reference_chunks": reference_chunks,
                        }

        if best_match:
            segment_slice = segments[segment_index : segment_index + int(best_match["segment_window"])]
            replacement = time_text_chunks(
                list(best_match["reference_chunks"]),
                float(segment_slice[0]["start"]),
                float(segment_slice[-1]["end"]),
            )
            if replacement:
                corrected.extend(replacement)
                correction_count += 1
                script_cursor = max(script_cursor, int(best_match["chunk_index"]) + int(best_match["chunk_window"]))
                segment_index += int(best_match["segment_window"])
                continue

        segment = segments[segment_index]
        text = segment["text"].strip()
        normalized = normalize_match_text(text)
        if len(normalized) < MIN_SPLIT_CHARS:
            corrected.append(segment)
            segment_index += 1
            continue

        best_index = -1
        best_ratio = 0.0
        start = max(0, script_cursor - 5)
        end = min(len(script_chunks), script_cursor + 18)
        for index in range(start, end):
            candidate = script_chunks[index]
            candidate_norm = normalize_match_text(candidate)
            if len(candidate_norm) < MIN_SPLIT_CHARS:
                continue
            ratio = difflib.SequenceMatcher(None, normalized, candidate_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = index

        if best_index >= 0 and best_ratio >= SCRIPT_MATCH_RATIO:
            reference = script_chunks[best_index]
            ref_norm = normalize_match_text(reference)
            length_ratio = len(normalized) / max(len(ref_norm), 1)
            if 0.75 <= length_ratio <= 1.35 and text != reference:
                corrected.append({**segment, "text": reference})
                correction_count += 1
            else:
                corrected.append(segment)
            script_cursor = max(script_cursor, best_index + 1)
        else:
            corrected.append(segment)
        segment_index += 1

    return clean_timing(corrected), correction_count


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


def write_srt(segments: list[dict], srt_path: Path) -> None:
    entries = []
    for index, segment in enumerate(segments, start=1):
        text = segment["text"].strip()
        if not text:
            continue
        entries.append(
            f"{index}\n"
            f"{srt_time(td(segment['start']))} --> {srt_time(td(segment['end']))}\n"
            f"{text}\n"
        )
    srt_path.write_text("\n".join(entries) + "\n", encoding="utf-8")


def parse_srt_timestamp(value: str) -> float:
    hours, minutes, rest = value.strip().replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def scale_srt_timestamps(srt_path: Path, speed: float) -> None:
    content = srt_path.read_text(encoding="utf-8")

    def repl(match: re.Match[str]) -> str:
        start = parse_srt_timestamp(match.group(1)) / speed
        end = parse_srt_timestamp(match.group(2)) / speed
        return f"{srt_time(td(start))} --> {srt_time(td(end))}"

    scaled = re.sub(
        r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
        repl,
        content,
    )
    srt_path.write_text(scaled, encoding="utf-8")


def apply_video_speed(input_path: Path, output_path: Path, speed: float, force: bool) -> None:
    ensure_writable(output_path, force)
    ffmpeg = find_ffmpeg()
    cmd = [
        str(ffmpeg),
        "-y",
        "-i",
        str(input_path),
        "-filter_complex",
        f"[0:v]setpts=PTS/{speed:g}[v];[0:a]atempo={speed:g}[a]",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-r",
        str(OUTPUT_FPS),
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


def apply_speed_outputs(video_path: Path, srt_path: Path, speed: float, work_dir: Path) -> None:
    if abs(speed - 1.0) < 1e-9:
        return
    if speed <= 0:
        raise SystemExit("--speed must be greater than 0.")
    sped_video_path = work_dir / f"{video_path.stem}-speed{speed:g}{video_path.suffix}"
    apply_video_speed(video_path, sped_video_path, speed, force=True)
    shutil.move(sped_video_path, video_path)
    scale_srt_timestamps(srt_path, speed)


def write_transcript(text: str, fallback_segments: list[dict], transcript_path: Path, replacements: dict[str, str]) -> None:
    segment_transcript = "\n".join(segment["text"].strip() for segment in fallback_segments if segment["text"].strip())
    transcript = segment_transcript or apply_vocab(text.strip(), replacements)
    transcript_path.write_text(transcript.rstrip() + "\n", encoding="utf-8")


def output_paths(out_dir: Path, ep: str, suffix: str) -> tuple[Path, Path, Path]:
    ep_number = ep.zfill(2) if ep.isdigit() else ep
    video_path = out_dir / f"05-final-video-autocut{suffix}.mp4"
    srt_path = out_dir / f"EP{ep_number}-字幕-zh-TW-autocut{suffix}.srt"
    transcript_path = out_dir / f"transcript-autocut{suffix}.txt"
    return video_path, srt_path, transcript_path


def trimmed_output_paths(out_dir: Path, ep: str, suffix: str) -> tuple[Path, Path, Path]:
    ep_number = ep.zfill(2) if ep.isdigit() else ep
    video_path = out_dir / f"05-final-video-autocut{suffix}-trimmed.mp4"
    srt_path = out_dir / f"EP{ep_number}-字幕-zh-TW-autocut{suffix}-trimmed.srt"
    transcript_path = out_dir / f"transcript-autocut{suffix}-trimmed.txt"
    return video_path, srt_path, transcript_path


def default_work_dir(input_path: Path, ep: str, suffix: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"ep{ep}-{input_path.stem}{suffix or ''}").strip("-")
    return Path(tempfile.gettempdir()) / "life-os-episode-pipeline" / safe_name


def default_prompt(replacements: dict[str, str], script_chunks: list[str] | None = None) -> str:
    terms = set(replacements.values()) | PROMPT_TERMS
    for chunk in script_chunks or []:
        for term in PROMPT_TERMS:
            if term in chunk:
                terms.add(term)
        for ascii_term in re.findall(r"[A-Za-z][A-Za-z0-9%+-]*(?: [A-Za-z0-9%+-]+)*", chunk):
            if len(ascii_term) >= 2:
                terms.add(ascii_term)
    terms = sorted(terms)
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
    trimmed_video_path, trimmed_srt_path, trimmed_transcript_path = trimmed_output_paths(out_dir, args.ep, args.suffix)
    trim_enabled = not args.skip_trim and not args.transcribe_only
    replacements = load_vocab(args.vocab)
    script_path = find_script_path(out_dir)
    script_chunks = load_script_chunks(script_path) if script_path else []
    if script_path:
        print(f"Using script for punctuation: {script_path.name} ({len(script_chunks)} chunks)")
    else:
        print("No script found for punctuation restoration.")
    prompt = args.initial_prompt if args.initial_prompt is not None else default_prompt(replacements, script_chunks)

    if args.skip_transcribe:
        if not srt_path.exists():
            raise SystemExit(f"--skip-transcribe requested but SRT does not exist: {srt_path}")
        print(f"Reusing {srt_path}")
        if trim_enabled:
            trim_duplicate_takes = load_trim_duplicate_takes()
            if not args.trim_dry_run:
                ensure_writable(trimmed_video_path, args.force)
                ensure_writable(trimmed_srt_path, args.force)
                ensure_writable(trimmed_transcript_path, args.force)
            trim_duplicate_takes(
                video_path=video_path,
                srt_path=srt_path,
                out_video=trimmed_video_path,
                out_srt=trimmed_srt_path,
                out_txt=trimmed_transcript_path,
                threshold=args.trim_threshold,
                gap=args.trim_gap,
                apply=not args.trim_dry_run,
                force=args.force,
                ffmpeg_path=find_ffmpeg(),
                text_transform=lambda text: apply_vocab(text, replacements),
            )
        return

    if not args.transcribe_only:
        ensure_writable(video_path, args.force)
        if trim_enabled and not args.trim_dry_run:
            ensure_writable(trimmed_video_path, args.force)
    ensure_writable(srt_path, args.force)
    ensure_writable(transcript_path, args.force)
    if trim_enabled and not args.trim_dry_run:
        ensure_writable(trimmed_srt_path, args.force)
        ensure_writable(trimmed_transcript_path, args.force)

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
        normalize_video(input_path, normalized_work_path, force=True)
        transient_paths.append(normalized_work_path)
        cut_silence(normalized_work_path, cut_path, args.margin, force=True)
        transient_paths.append(cut_path)
        transcribe_input = cut_path

    raw_segments, transcript = transcribe(transcribe_input, args.model, args.language, prompt)
    if not raw_segments:
        raise SystemExit("Whisper returned no segments.")
    raw_segments = restore_punctuation_to_raw_segments(raw_segments, script_chunks)
    atoms = atomize_whisper_segments(raw_segments)
    segments = apply_vocab_to_segments(merge_segments(atoms), replacements)
    script_correction_count = 0
    write_srt(segments, srt_path)
    write_transcript(transcript, segments, transcript_path, replacements)
    video_info = probe_video(transcribe_input)
    if not args.transcribe_only and transcribe_input != video_path:
        shutil.copy2(transcribe_input, video_path)
    if trim_enabled:
        trim_duplicate_takes = load_trim_duplicate_takes()
        trim_duplicate_takes(
            video_path=video_path,
            srt_path=srt_path,
            out_video=trimmed_video_path,
            out_srt=trimmed_srt_path,
            out_txt=trimmed_transcript_path,
            threshold=args.trim_threshold,
            gap=args.trim_gap,
            apply=not args.trim_dry_run,
            force=args.force,
            ffmpeg_path=find_ffmpeg(),
        )
    if not args.transcribe_only and not args.trim_dry_run:
        if trim_enabled:
            apply_speed_outputs(trimmed_video_path, trimmed_srt_path, args.speed, work_dir)
        else:
            apply_speed_outputs(video_path, srt_path, args.speed, work_dir)
    cleanup(transient_paths, args.keep_work)

    print(f"Wrote {srt_path}")
    print(f"Wrote {transcript_path}")
    if not args.transcribe_only:
        print(f"Wrote {video_path}")
        if trim_enabled and not args.trim_dry_run:
            print(f"Wrote {trimmed_video_path}")
            print(f"Wrote {trimmed_srt_path}")
            print(f"Wrote {trimmed_transcript_path}")
        elif trim_enabled:
            print("Trim dry-run only: no trimmed outputs were written.")
    print(f"Subtitle segments: {len(segments)}")
    print(f"Script corrections: {script_correction_count}")
    print(f"Clean video duration: {video_info['duration']:.1f}s")


if __name__ == "__main__":
    main()
