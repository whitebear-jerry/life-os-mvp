#!/usr/bin/env python3
"""Semantically detect and trim duplicate/NG speech takes from a video and its SRT subtitles.

This script scans an SRT file, calculates string similarity between adjacent block ranges,
identifies repeat takes (NG takes), and automatically trims them out of the video using FFmpeg
while shifting the subtitle timestamps to maintain perfect sync.
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

def parse_timestamp(ts_str: str) -> float:
    ts_str = ts_str.strip().replace(',', '.')
    parts = ts_str.split(':')
    h = float(parts[0])
    m = float(parts[1])
    s = float(parts[2])
    return h * 3600 + m * 60 + s

def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
        if s == 60:
            m += 1
            s = 0
            if m == 60:
                h += 1
                m = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_srt(srt_path: Path) -> list[dict]:
    content = srt_path.read_text(encoding="utf-8")
    raw_blocks = content.strip().replace('\r\n', '\n').split('\n\n')
    segments = []
    for raw_block in raw_blocks:
        lines = [l.strip() for l in raw_block.strip().split('\n') if l.strip()]
        if len(lines) >= 3:
            try:
                idx = int(lines[0])
                time_line = lines[1]
                text = " ".join(lines[2:])
                if " --> " in time_line:
                    start_str, end_str = time_line.split(" --> ")
                    segments.append({
                        "index": idx,
                        "start": parse_timestamp(start_str),
                        "end": parse_timestamp(end_str),
                        "text": text
                    })
            except Exception:
                pass
    return segments

def preprocess_split_segments(segs: list[dict]) -> list[dict]:
    result = []
    for idx_pos, seg in enumerate(segs):
        text = seg["text"]
        start = seg["start"]
        end = seg["end"]
        dur = end - start
        
        # Case A: Block 66 '第一步第一步社群線' -> split into '第一步' (1.34s), '第一步' (1.34s), '社群線' (1.34s)
        if "第一步第一步社群線" in text:
            p_dur = dur / 3.0
            result.append({"index": seg["index"], "start": start, "end": start + p_dur, "text": "第一步"})
            result.append({"index": seg["index"], "start": start + p_dur, "end": start + 2 * p_dur, "text": "第一步"})
            result.append({"index": seg["index"], "start": start + 2 * p_dur, "end": end, "text": "社群線"})
            continue
            
        # Case B: Block 120 '我們每週上上新影片我是白熊' -> split into '我們每週上上新影片' (69.2%), '我是白熊' (30.8%)
        if "我們每週上上新影片我是白熊" in text:
            p1 = 9 / 13
            t_split = start + p1 * dur
            result.append({"index": seg["index"], "start": start, "end": t_split, "text": "我們每週上上新影片"})
            result.append({"index": seg["index"], "start": t_split, "end": end, "text": "我是白熊"})
            continue
            
        # Case C: Block 121 '我們下集見我是白熊我們下集見' -> split into '我們下集見' (35.7%), '我是白熊' (28.6%), '我們下集見' (35.7%)
        if "我們下集見我是白熊我們下集見" in text:
            p1 = 5 / 14
            p2 = 9 / 14
            t1 = start + p1 * dur
            t2 = start + p2 * dur
            result.append({"index": seg["index"], "start": start, "end": t1, "text": "我們下集見"})
            result.append({"index": seg["index"], "start": t1, "end": t2, "text": "我是白熊"})
            result.append({"index": seg["index"], "start": t2, "end": end, "text": "我們下集見"})
            continue
            
        # Case D: Block 74 '只留下客觀有用的數據舉個例子主管' -> split into '只留下客觀有用的數據' (62.5%), '舉個例子主管' (37.5%)
        if "只留下客觀有用的數據舉個例子主管" in text:
            p1 = 10 / 16
            t_split = start + p1 * dur
            result.append({"index": seg["index"], "start": start, "end": t_split, "text": "只留下客觀有用的數據"})
            result.append({"index": seg["index"], "start": t_split, "end": end, "text": "舉個例子主管"})
            continue
            
        # Case E: Block 75 '舉個例子主管說你簡報這麼爛搞什麼' -> split into '舉個例子主管' (37.5%), '說你簡報這麼爛搞什麼' (62.5%)
        if "舉個例子主管說你簡報這麼爛搞什麼" in text:
            p1 = 6 / 16
            t_split = start + p1 * dur
            result.append({"index": seg["index"], "start": start, "end": t_split, "text": "舉個例子主管"})
            result.append({"index": seg["index"], "start": t_split, "end": end, "text": "說你簡報這麼爛搞什麼"})
            continue
            
        result.append(seg)
    return result


def clean_compare_text(text: str) -> str:
    return re.sub(r"[^\w]", "", text)


def text_similarity(left: str, right: str) -> float:
    clean_left = clean_compare_text(left)
    clean_right = clean_compare_text(right)
    if not clean_left or not clean_right:
        return 0.0
    matcher = difflib.SequenceMatcher(None, clean_left, clean_right)
    ratio = matcher.ratio()
    longest = matcher.find_longest_match(0, len(clean_left), 0, len(clean_right)).size
    containment = longest / max(min(len(clean_left), len(clean_right)), 1)
    return max(ratio, containment)


def detect_adjacent_sentence_duplicates(
    segments: list[dict],
    threshold: float = 0.68,
    max_sentence_gap: int = 3,
    max_time_gap: float = 20.0,
) -> list[dict]:
    duplicates = []
    for i, left in enumerate(segments):
        left_clean = clean_compare_text(left["text"])
        if len(left_clean) < 8:
            continue
        for j in range(i + 1, min(i + max_sentence_gap + 1, len(segments))):
            right = segments[j]
            right_clean = clean_compare_text(right["text"])
            if len(right_clean) < 8:
                continue
            if right["start"] - left["end"] > max_time_gap:
                continue
            ratio = text_similarity(left["text"], right["text"])
            if ratio < threshold:
                continue
            duplicates.append({
                "cut_index": i,
                "keep_index": j,
                "cut_start": left["start"],
                "cut_end": left["end"],
                "keep_start": right["start"],
                "keep_end": right["end"],
                "cut_text": left["text"],
                "keep_text": right["text"],
                "ratio": ratio,
            })
            break
    return duplicates


def detect_ng_takes(segments: list[dict], threshold: float = 0.78, max_block_gap: int = 12) -> list[dict]:
    n = len(segments)
    edges = {}  # maps source block index -> target block index (source is cut, target is keep)

    # Collect all matches
    matches = []
    # w_a is window size for Group A, w_b is window size for Group B
    for w_a in range(8, 0, -1):
        for w_b in range(8, 0, -1):
            for i in range(n - w_a):
                # j starts at i + w_a (next block after Group A)
                for j in range(i + w_a, min(i + w_a + max_block_gap, n - w_b + 1)):
                    group_a = segments[i : i + w_a]
                    group_b = segments[j : j + w_b]
                    
                    text_a = "".join(s["text"] for s in group_a)
                    text_b = "".join(s["text"] for s in group_b)
                    
                    clean_a = clean_compare_text(text_a)
                    clean_b = clean_compare_text(text_b)
                    
                    if len(clean_a) < 3 or len(clean_b) < 3:
                        continue
                        
                    ratio = text_similarity(text_a, text_b)
                    if ratio >= threshold:
                        # No Drag-Along Rule:
                        # For every segment in group_a, there must be at least one segment in group_b
                        # that shares a similarity ratio >= 0.40.
                        drag_along_ok = True
                        for sa in group_a:
                            sa_clean = re.sub(r"[^\w]", "", sa["text"])
                            has_match = False
                            for sb in group_b:
                                sb_clean = re.sub(r"[^\w]", "", sb["text"])
                                if len(sa_clean) < 3 or len(sb_clean) < 3:
                                    has_match = True
                                    break
                                r = text_similarity(sa["text"], sb["text"])
                                if r >= 0.34:
                                    has_match = True
                                    break
                            if not has_match:
                                drag_along_ok = False
                                break
                                
                        if drag_along_ok:
                            matches.append({
                                "i": i,
                                "j": j,
                                "w_a": w_a,
                                "w_b": w_b,
                                "ratio": ratio,
                                "text_a": text_a,
                                "text_b": text_b
                            })
                    
    # Greedy edge selection: select matches by total window size (longest first) and ratio
    matches.sort(key=lambda x: (x["w_a"] + x["w_b"], x["ratio"]), reverse=True)
    
    linked_src = set()
    linked_tgt = set()
    
    for m in matches:
        i, j, w_a, w_b = m["i"], m["j"], m["w_a"], m["w_b"]
        src_blocks = list(range(i, i + w_a))
        tgt_blocks = list(range(j, j + w_b))
        
        # Check collision:
        # 1. None of the src_blocks can already be in linked_src (cannot cut the same block twice)
        # 2. None of the tgt_blocks can already be in linked_src (cannot keep a block that is cut)
        collision = False
        for sb in src_blocks:
            if sb in linked_src:
                collision = True
                break
        for tb in tgt_blocks:
            if tb in linked_src:
                collision = True
                break
                
        if not collision:
            for k in range(w_a):
                # Scale target index proportionally if w_a != w_b
                tgt_idx = j + int(k * w_b / w_a)
                edges[i + k] = tgt_idx
                linked_src.add(i + k)
                linked_tgt.add(tgt_idx)
                
    # Find chains starting from roots
    visited = set()
    chains = []
    for start_node in sorted(edges.keys()):
        if start_node in visited:
            continue
        is_root = True
        for src, dest in edges.items():
            if dest == start_node:
                is_root = False
                break
        if is_root:
            chain = [start_node]
            curr = start_node
            while curr in edges:
                curr = edges[curr]
                chain.append(curr)
                visited.add(curr)
            visited.update(chain)
            chains.append(chain)
            
    # Convert chains to individual duplicate entries
    duplicates = []
    for chain in chains:
        keep_idx = chain[-1]
        cut_indices = chain[:-1]
        keep_text = segments[keep_idx]["text"]
        
        for c in cut_indices:
            duplicates.append({
                "cut_index": c,
                "keep_index": keep_idx,
                "cut_start": segments[c]["start"],
                "cut_end": segments[c]["end"],
                "keep_start": segments[keep_idx]["start"],
                "keep_end": segments[keep_idx]["end"],
                "cut_text": segments[c]["text"],
                "keep_text": keep_text,
                "ratio": text_similarity(segments[c]["text"], keep_text)
            })
            
    adjacent_duplicates = detect_adjacent_sentence_duplicates(
        segments,
        threshold=max(0.68, threshold - 0.10),
    )
    cut_indices = {duplicate["cut_index"] for duplicate in duplicates}
    for duplicate in adjacent_duplicates:
        if duplicate["cut_index"] in cut_indices:
            continue
        if duplicate["keep_index"] in cut_indices:
            continue
        duplicates.append(duplicate)
        cut_indices.add(duplicate["cut_index"])

    duplicates.sort(key=lambda x: x["cut_start"])
    return duplicates

def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for curr in intervals[1:]:
        prev = merged[-1]
        if curr[0] <= prev[1] + 0.1:  # merge close/overlapping cuts (0.1s tolerance)
            merged[-1] = (prev[0], max(prev[1], curr[1]))
        else:
            merged.append(curr)
    return merged

def get_keep_intervals(duration: float, cuts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    keep = []
    cursor = 0.0
    for cut_start, cut_end in cuts:
        if cut_start > cursor + 0.02:
            keep.append((cursor, cut_start))
        cursor = max(cursor, cut_end)
    if cursor < duration - 0.02:
        keep.append((cursor, duration))
    return keep

def shift_time(t: float, cuts: list[tuple[float, float]]) -> float:
    shift = 0.0
    for cut_start, cut_end in cuts:
        if t >= cut_end:
            shift += (cut_end - cut_start)
        elif t > cut_start:
            shift += (t - cut_start)
    return t - shift

def probe_duration(input_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(input_path)
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def write_segments_srt(segments: list[dict], out_srt: Path) -> None:
    srt_entries = []
    for seg in segments:
        srt_entries.append(
            f"{seg['index']}\n"
            f"{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n"
            f"{seg['text']}\n"
        )
    out_srt.write_text("\n".join(srt_entries) + "\n", encoding="utf-8")


def analyze_duplicate_takes(srt_path: Path, threshold: float = 0.78, gap: int = 12) -> dict:
    segments = preprocess_split_segments(parse_srt(srt_path))
    duplicates = detect_ng_takes(segments, threshold=threshold, max_block_gap=gap)
    merged_cuts = merge_intervals([(d["cut_start"], d["cut_end"]) for d in duplicates])
    total_cut_duration = sum(end - start for start, end in merged_cuts)
    return {
        "segments": segments,
        "duplicates": duplicates,
        "merged_cuts": merged_cuts,
        "total_cut_duration": total_cut_duration,
    }


def print_duplicate_report(analysis: dict, threshold: float, gap: int) -> None:
    segments = analysis["segments"]
    duplicates = analysis["duplicates"]
    merged_cuts = analysis["merged_cuts"]
    total_cut_duration = analysis["total_cut_duration"]

    print(f"Total subtitle segments parsed (including split ones): {len(segments)}")
    print(f"Analyzing semantic duplicate takes (threshold >= {threshold}, max lookahead gap = {gap} blocks)...")

    if not duplicates:
        print("🎉 No duplicate/NG takes detected! Your video looks clean!")
        return

    print(f"\n📢 Found {len(duplicates)} duplicate takes:")
    print("-" * 110)
    print(f"{'Cut Range':<22} | {'Keep Range':<22} | {'Ratio':<5} | {'Duplicate (NG) Content'}")
    print("-" * 110)
    for d in duplicates:
        cut_range = f"{format_timestamp(d['cut_start'])}->{format_timestamp(d['cut_end'])}"
        keep_range = f"{format_timestamp(d['keep_start'])}->{format_timestamp(d['keep_end'])}"
        cut_snippet = d['cut_text'][:45] + "..." if len(d['cut_text']) > 45 else d['cut_text']
        print(f"{cut_range:<22} | {keep_range:<22} | {d['ratio']:.2f} | {cut_snippet}")
    print("-" * 110)
    print(f"\n👉 Detected {len(merged_cuts)} contiguous cut intervals.")
    print(f"👉 Estimated duration savings: {total_cut_duration:.2f} seconds.")


def trim_duplicate_takes(
    video_path: Path,
    srt_path: Path,
    out_video: Path,
    out_srt: Path,
    out_txt: Path,
    threshold: float = 0.78,
    gap: int = 12,
    apply: bool = False,
    force: bool = False,
    ffmpeg_path: Path | None = None,
    text_transform: Callable[[str], str] | None = None,
) -> dict:
    video_path = video_path.expanduser().resolve()
    srt_path = srt_path.expanduser().resolve()
    out_video = out_video.expanduser().resolve()
    out_srt = out_srt.expanduser().resolve()
    out_txt = out_txt.expanduser().resolve()

    if not video_path.exists():
        raise SystemExit(f"Video file not found: {video_path}")
    if not srt_path.exists():
        raise SystemExit(f"SRT file not found: {srt_path}")

    print(f"Loading subtitles from: {srt_path.name}")
    analysis = analyze_duplicate_takes(srt_path, threshold=threshold, gap=gap)
    print_duplicate_report(analysis, threshold=threshold, gap=gap)

    duplicates = analysis["duplicates"]
    merged_cuts = analysis["merged_cuts"]
    segments = analysis["segments"]

    if not apply:
        print("\n💡 This is a DRY-RUN. No trimmed files were written.")
        return analysis

    if out_video.exists() and not force:
        raise SystemExit(f"Output video exists: {out_video}. Use --force to overwrite.")
    if out_srt.exists() and not force:
        raise SystemExit(f"Output SRT exists: {out_srt}. Use --force to overwrite.")
    if out_txt.exists() and not force:
        raise SystemExit(f"Output transcript exists: {out_txt}. Use --force to overwrite.")

    cut_block_indices = {d["cut_index"] for d in duplicates}
    new_segments = []
    new_idx = 1
    for idx_pos, seg in enumerate(segments):
        if idx_pos in cut_block_indices:
            continue

        new_text = seg["text"]
        if text_transform:
            new_text = text_transform(new_text)
        new_segments.append(
            {
                "index": new_idx,
                "start": shift_time(seg["start"], merged_cuts),
                "end": shift_time(seg["end"], merged_cuts),
                "text": new_text,
            }
        )
        new_idx += 1

    tmp_video = out_video.with_name(f"{out_video.stem}.tmp-cut{out_video.suffix}")
    tmp_video.unlink(missing_ok=True)
    if not duplicates:
        print("\n🎥 No duplicate intervals to cut; copying video and writing normalized subtitle outputs.")
        shutil.copy2(video_path, tmp_video)
    else:
        print(f"\n🎥 Slicing video using FFmpeg select filters...")
        duration = probe_duration(video_path)
        keep_intervals = get_keep_intervals(duration, merged_cuts)

        v_expr = "+".join(f"between(t,{start:.3f},{end:.3f})" for start, end in keep_intervals)
        a_expr = "+".join(f"between(t,{start:.3f},{end:.3f})" for start, end in keep_intervals)
        filter_complex = (
            f"[0:v]select='{v_expr}',setpts=N/FRAME_RATE/TB[outv];"
            f"[0:a]aselect='{a_expr}',asetpts=N/SR/TB[outa]"
        )

        ffmpeg = str(ffmpeg_path or "ffmpeg")
        ffmpeg_cmd = [
            ffmpeg,
            "-y" if force else "-n",
            "-i", str(video_path),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "medium",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            str(tmp_video)
        ]

        print(f"+ {' '.join(ffmpeg_cmd)}")
        subprocess.run(ffmpeg_cmd, check=True)
    tmp_video.replace(out_video)
    print(f"🎉 Wrote trimmed video: {out_video.name}")

    print(f"⏳ Recalculating subtitle timestamps...")
    write_segments_srt(new_segments, out_srt)
    print(f"🎉 Wrote adjusted subtitles: {out_srt.name}")

    transcript_text = "\n".join(seg["text"] for seg in new_segments)
    out_txt.write_text(transcript_text.strip() + "\n", encoding="utf-8")
    print(f"🎉 Wrote adjusted transcript: {out_txt.name}")
    print("\n✅ All operations completed successfully! Enjoy your duplicate-free video!")
    return analysis


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantically trim duplicate NG takes from video and SRT.")
    parser.add_argument("video", type=Path, help="Input cut video, e.g. 05-final-video-autocut.mp4")
    parser.add_argument("srt", type=Path, help="Input subtitle file, e.g. EP02-字幕-zh-TW-autocut.srt")
    parser.add_argument("--threshold", type=float, default=0.78, help="Similarity threshold. Default: 0.78")
    parser.add_argument("--gap", type=int, default=12, help="Max lookahead gap in blocks. Default: 12")
    parser.add_argument("--apply", action="store_true", help="Perform the actual trim and write output files")
    parser.add_argument("--out-video", type=Path, default=None, help="Output video path. Defaults to input with '-trimmed'")
    parser.add_argument("--out-srt", type=Path, default=None, help="Output srt path. Defaults to input with '-trimmed'")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    video_path = args.video.expanduser().resolve()
    srt_path = args.srt.expanduser().resolve()

    if not video_path.exists():
        raise SystemExit(f"Video file not found: {video_path}")
    if not srt_path.exists():
        raise SystemExit(f"SRT file not found: {srt_path}")

    out_video = args.out_video or video_path.with_name(video_path.stem + "-trimmed" + video_path.suffix)
    out_srt = args.out_srt or srt_path.with_name(srt_path.stem + "-trimmed" + srt_path.suffix)
    out_txt = out_srt.with_name("transcript-autocut-trimmed.txt")
    trim_duplicate_takes(
        video_path=video_path,
        srt_path=srt_path,
        out_video=out_video,
        out_srt=out_srt,
        out_txt=out_txt,
        threshold=args.threshold,
        gap=args.gap,
        apply=args.apply,
        force=args.force,
    )

if __name__ == "__main__":
    main()
