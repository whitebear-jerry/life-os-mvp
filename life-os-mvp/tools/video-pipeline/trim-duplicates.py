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
import subprocess
from pathlib import Path

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

def detect_ng_takes(segments: list[dict], threshold: float = 0.78, max_block_gap: int = 12) -> list[dict]:
    n = len(segments)
    edges = {}  # maps source block index -> target block index (source is cut, target is keep)
    
    # Collect all matches
    matches = []
    for w in range(6, 0, -1):  # Longest windows first
        for i in range(n - w):
            # We look ahead up to max_block_gap blocks
            for j in range(i + w, min(i + w + max_block_gap, n - w + 1)):
                group_a = segments[i : i + w]
                group_b = segments[j : j + w]
                
                text_a = "".join(s["text"] for s in group_a)
                text_b = "".join(s["text"] for s in group_b)
                
                clean_a = re.sub(r"[^\w]", "", text_a)
                clean_b = re.sub(r"[^\w]", "", text_b)
                
                if len(clean_a) < 4 or len(clean_b) < 4:
                    continue
                    
                ratio = difflib.SequenceMatcher(None, clean_a, clean_b).ratio()
                if ratio >= threshold:
                    matches.append({
                        "i": i,
                        "j": j,
                        "w": w,
                        "ratio": ratio,
                        "text_a": text_a,
                        "text_b": text_b
                    })
                    
    # Greedy edge selection: select matches by window size w (longest first) and ratio
    matches.sort(key=lambda x: (x["w"], x["ratio"]), reverse=True)
    
    linked_src = set()
    linked_tgt = set()
    
    for m in matches:
        i, j, w = m["i"], m["j"], m["w"]
        src_blocks = list(range(i, i + w))
        tgt_blocks = list(range(j, j + w))
        
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
            for k in range(w):
                edges[i + k] = j + k
                linked_src.add(i + k)
                linked_tgt.add(j + k)
                
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
                "ratio": difflib.SequenceMatcher(None, re.sub(r"[^\w]", "", segments[c]["text"]), re.sub(r"[^\w]", "", keep_text)).ratio()
            })
            
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

    print(f"Loading subtitles from: {srt_path.name}")
    segments = parse_srt(srt_path)
    print(f"Total subtitle segments parsed: {len(segments)}")

    print(f"Analyzing semantic duplicate takes (threshold >= {args.threshold}, max lookahead gap = {args.gap} blocks)...")
    duplicates = detect_ng_takes(segments, threshold=args.threshold, max_block_gap=args.gap)

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

    # Calculate cut intervals
    raw_cuts = [(d["cut_start"], d["cut_end"]) for d in duplicates]
    merged_cuts = merge_intervals(raw_cuts)
    
    total_cut_duration = sum(end - start for start, end in merged_cuts)
    print(f"\n👉 Detected {len(merged_cuts)} contiguous cut intervals.")
    print(f"👉 Estimated duration savings: {total_cut_duration:.2f} seconds.")

    if not args.apply:
        print("\n💡 This is a DRY-RUN. To perform the actual trim and generate new files, run:")
        print(f"   python3 tools/video-pipeline/{Path(__file__).name} \"{args.video}\" \"{args.srt}\" --apply")
        return

    # Execute cuts
    out_video = args.out_video or video_path.with_name(video_path.stem + "-trimmed" + video_path.suffix)
    out_srt = args.out_srt or srt_path.with_name(srt_path.stem + "-trimmed" + srt_path.suffix)
    out_txt = out_srt.with_name("transcript-autocut-trimmed.txt")

    if out_video.exists() and not args.force:
        raise SystemExit(f"Output video exists: {out_video}. Use --force to overwrite.")
    if out_srt.exists() and not args.force:
        raise SystemExit(f"Output SRT exists: {out_srt}. Use --force to overwrite.")

    print(f"\n🎥 Slicing video using FFmpeg select filters...")
    duration = probe_duration(video_path)
    keep_intervals = get_keep_intervals(duration, merged_cuts)
    
    v_expr = "+".join(f"between(t,{start:.3f},{end:.3f})" for start, end in keep_intervals)
    a_expr = "+".join(f"between(t,{start:.3f},{end:.3f})" for start, end in keep_intervals)
    filter_complex = f"[0:v]select='{v_expr}',setpts=N/FRAME_RATE/TB[outv];[0:a]aselect='{a_expr}',asetpts=N/SR/TB[outa]"
    
    ffmpeg_cmd = [
        "ffmpeg",
        "-y" if args.force else "-n",
        "-i", str(video_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "192k",
        str(out_video)
    ]
    
    print(f"+ {' '.join(ffmpeg_cmd)}")
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"🎉 Wrote trimmed video: {out_video.name}")

    # Re-build subtitles
    print(f"⏳ Recalculating subtitle timestamps...")
    cut_block_indices = {d["cut_index"] for d in duplicates}
    new_segments = []
    new_idx = 1
    
    for seg in segments:
        if seg["index"] in cut_block_indices:
            continue
        
        new_start = shift_time(seg["start"], merged_cuts)
        new_end = shift_time(seg["end"], merged_cuts)
        
        new_segments.append({
            "index": new_idx,
            "start": new_start,
            "end": new_end,
            "text": seg["text"]
        })
        new_idx += 1

    # Write SRT
    srt_entries = []
    for seg in new_segments:
        srt_entries.append(
            f"{seg['index']}\n"
            f"{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n"
            f"{seg['text']}\n"
        )
    out_srt.write_text("\n".join(srt_entries) + "\n", encoding="utf-8")
    print(f"🎉 Wrote adjusted subtitles: {out_srt.name}")

    # Write transcript
    transcript_text = "\n".join(seg["text"] for seg in new_segments)
    out_txt.write_text(transcript_text.strip() + "\n", encoding="utf-8")
    print(f"🎉 Wrote adjusted transcript: {out_txt.name}")
    print("\n✅ All operations completed successfully! Enjoy your duplicate-free video!")

if __name__ == "__main__":
    main()
