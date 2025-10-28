#!/usr/bin/env python3
"""SRT writer with timeline timecodes.

Generates timecode.srt by applying calculated timeline timecodes
to the original source SRT subtitles.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import List, Optional, Set
from difflib import SequenceMatcher

# Timeline framerate (NTSC drop-frame approximation used across pipeline)
FPS = 29.97


def srt_timecode_from_seconds(seconds: float) -> str:
    """Convert seconds to SRT timecode format.

    Args:
        seconds: Time in seconds

    Returns:
        Timecode string in format HH:MM:SS,mmm

    Example:
        >>> srt_timecode_from_seconds(3661.5)
        '01:01:01,500'
    """
    total_ms = int(seconds * 1000)

    milliseconds = total_ms % 1000
    total_seconds = total_ms // 1000

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def frames_to_srt_timecode(frames: int, fps: float = FPS) -> str:
    """Convert timeline frames to SRT timecode."""
    total_ms = round((frames / fps) * 1000.0)

    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    seconds = total_ms // 1_000
    milliseconds = total_ms % 1_000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def normalize_text(text: str) -> str:
    """Normalize text for comparison (remove punctuation, whitespace, newlines, SSML tags)."""
    # Remove SSML tags (e.g., <sub alias='...'>, <break time='...'/>, etc.)
    text = re.sub(r'<[^>]+>', '', text)
    # Remove all whitespace and newlines
    text = re.sub(r'\s+', '', text)
    # Remove common punctuation
    text = re.sub(r'[、。，．？！…—―「」『』（）]', '', text)
    return text


def text_similarity(a: str, b: str) -> float:
    """Calculate text similarity ratio (0.0 to 1.0)."""
    return SequenceMatcher(None, a, b).ratio()

def _segment_durations(timeline_segments: List) -> List[float]:
    """Return per-segment durations in seconds (never negative)."""
    durations: List[float] = []
    for segment in timeline_segments:
        duration = max(0.0, segment.end_time_sec - segment.start_time_sec)
        durations.append(duration)
    return durations


def _distribute_counts_by_duration(
    total_items: int,
    durations: List[float]
) -> List[int]:
    """Distribute item counts across buckets proportionally to duration.

    Ensures each bucket with non-zero duration gets at least 1 item when possible.
    Uses largest remainder method on the remaining pool.
    """
    bucket_count = len(durations)
    if bucket_count == 0 or total_items <= 0:
        return [0] * bucket_count

    total_duration = sum(durations)
    if total_duration <= 0:
        # Fallback to even distribution when durations are zero
        durations = [1.0] * bucket_count
        total_duration = float(bucket_count)

    counts = [0] * bucket_count

    if total_items >= bucket_count:
        # Give each bucket at least one item to avoid gaps
        counts = [1] * bucket_count
        remaining = total_items - bucket_count
    else:
        # Fewer items than buckets: allocate to longest durations
        sorted_indices = sorted(range(bucket_count), key=lambda idx: durations[idx], reverse=True)
        for i in range(total_items):
            counts[sorted_indices[i]] += 1
        return counts

    weights = [duration / total_duration for duration in durations]
    raw_extra = [weight * remaining for weight in weights]
    extra_floor = [math.floor(value) for value in raw_extra]

    counts = [base + extra for base, extra in zip(counts, extra_floor)]
    assigned = sum(counts)
    leftovers = total_items - assigned

    if leftovers > 0:
        remainders = [
            (raw_extra[idx] - extra_floor[idx], idx)
            for idx in range(bucket_count)
        ]
        remainders.sort(reverse=True)
        for i in range(leftovers):
            _, idx = remainders[i]
            counts[idx] += 1

    return counts


def write_timecode_srt(
    output_path: Path,
    source_subtitles: List,  # List[Subtitle]
    timeline_segments: List,  # List[TimelineSegment]
    nare_script_path: Path = None,
    nare_segments: Optional[List] = None,  # List[NarrationSegment]
    encoding: str = "utf-8"
) -> bool:
    """Write timecode SRT file.

    Aligns SRT subtitles to timeline using Nare script as reference.
    Maps SRT entries to audio segments by matching SRT text with Nare script lines.

    Args:
        output_path: Output SRT file path
        source_subtitles: Original subtitle entries from ep{N}.srt (DO NOT MODIFY)
        timeline_segments: Calculated timeline with timecodes (audio-based)
        nare_script_path: Path to Nare script (ep{N}nare.md) for text matching
        encoding: Output file encoding (default: utf-8)

    Returns:
        True if successful, False otherwise

    Design:
        - Matches each Nare line (= audio segment) to corresponding SRT subtitles
        - Uses text similarity matching (normalized text comparison)
        - Distributes matched SRT subtitles within each segment's timeline
        - Preserves original SRT text/formatting exactly
    """
    total_subs = len(source_subtitles)
    total_clips = len(timeline_segments)

    if total_subs == 0 or total_clips == 0:
        print("❌ No subtitles or timeline segments to process")
        return False

    # Parse Nare script for text matching
    nare_lines = []
    nare_normalized = []

    if nare_segments:
        nare_lines = [getattr(seg, "text", str(seg)) for seg in nare_segments]
        nare_normalized = [normalize_text(line) for line in nare_lines]
        print(f"  → Loaded {len(nare_lines)} Nare lines from narration segments")
    elif nare_script_path and nare_script_path.exists():
        nare_content = nare_script_path.read_text(encoding='utf-8').strip()
        nare_lines = nare_content.split('\n')
        nare_normalized = [normalize_text(line) for line in nare_lines]
        print(f"  → Loaded {len(nare_lines)} Nare lines from {nare_script_path.name}")
    else:
        print(f"  ⚠️ Nare script not found, using proportional distribution fallback")

    # Normalize subtitle text for matching
    for sub in source_subtitles:
        sub.normalized = normalize_text(sub.text)

    # Map each Nare line to SRT subtitles
    nare_to_srt: List[List[int]] = [[] for _ in range(max(len(nare_lines), total_clips))]
    used_srt: Set[int] = set()

    if nare_lines:
        for nare_idx, nare_norm in enumerate(nare_normalized):
            if nare_idx >= total_clips:
                break

            # Find SRT subtitles that match this Nare line
            best_matches = []

            for srt_idx, sub in enumerate(source_subtitles):
                if srt_idx in used_srt:
                    continue

                srt_norm = sub.normalized

                # Check if SRT text is substring of Nare or vice versa
                if srt_norm in nare_norm or nare_norm in srt_norm:
                    similarity = 1.0
                else:
                    # Calculate similarity
                    similarity = text_similarity(srt_norm, nare_norm)

                if similarity > 0.5:
                    best_matches.append((srt_idx, similarity))

            # Sort by similarity and assign
            best_matches.sort(key=lambda x: x[1], reverse=True)

            for srt_idx, sim in best_matches[:5]:  # Take top 5 matches
                if srt_idx not in used_srt:
                    nare_to_srt[nare_idx].append(srt_idx)
                    used_srt.add(srt_idx)
    else:
        # Fallback: proportional distribution without Nare matching
        remaining_subs = total_subs
        sub_idx = 0

        for clip_idx in range(total_clips):
            remaining_clips = total_clips - clip_idx
            assign = max(1, remaining_subs // remaining_clips)

            for _ in range(assign):
                if sub_idx < total_subs:
                    nare_to_srt[clip_idx].append(sub_idx)
                    used_srt.add(sub_idx)
                    sub_idx += 1

            remaining_subs = total_subs - sub_idx

    # Ensure all subtitles are assigned by falling back to duration-based distribution
    segment_count = min(len(timeline_segments), len(nare_to_srt))
    segment_durations = _segment_durations(timeline_segments[:segment_count])

    desired_counts = _distribute_counts_by_duration(total_subs, segment_durations)
    text_matched = len(used_srt)
    if text_matched and text_matched != total_subs:
        print(f"  ⚠️ Text match covered {text_matched}/{total_subs} subtitles; switching to sequential duration mapping")
    elif text_matched == 0:
        print(f"  ⚠️ No reliable text matches; using sequential duration mapping")

    segment_to_srt: List[List[int]] = [[] for _ in range(segment_count)]
    cursor = 0

    for seg_idx, desired in enumerate(desired_counts):
        if cursor >= total_subs:
            break

        take = max(0, min(desired, total_subs - cursor))

        if take == 0 and (total_subs - cursor) > 0:
            # Ensure we keep progressing when subtitles remain
            take = min(1, total_subs - cursor)

        if take:
            indices = list(range(cursor, cursor + take))
            segment_to_srt[seg_idx].extend(indices)
            cursor += take

    if cursor < total_subs and segment_to_srt:
        # Assign any leftover subtitles to the final segment
        remaining_indices = list(range(cursor, total_subs))
        segment_to_srt[-1].extend(remaining_indices)
        cursor = total_subs

    if cursor < total_subs:
        print(f"  ⚠️ Unable to allocate {total_subs - cursor} subtitles; please review inputs")
        return False

    # Fill in any empty mapping lists to keep downstream logic simple
    if not segment_to_srt:
        segment_to_srt = [[] for _ in range(total_clips)]

    # Generate aligned SRT
    output_lines = []
    cue_number = 1

    try:
        for nare_idx in range(min(len(segment_to_srt), total_clips)):
            segment = timeline_segments[nare_idx]
            srt_indices = segment_to_srt[nare_idx]

            if not srt_indices:
                continue

            # Distribute SRT subtitles within this segment's timeline
            seg_start = segment.start_time_sec
            seg_end = segment.end_time_sec
            seg_duration = seg_end - seg_start  # Calculate duration from start/end
            num_subs = len(srt_indices)

            for j, srt_idx in enumerate(srt_indices):
                subtitle = source_subtitles[srt_idx]

                # Calculate timecode within segment
                if num_subs == 1:
                    start_sec = seg_start
                    end_sec = seg_end
                else:
                    start_sec = seg_start + (seg_duration * j) / num_subs
                    end_sec = seg_start + (seg_duration * (j + 1)) / num_subs

                # Write SRT entry (preserve original text exactly)
                output_lines.append(f"{cue_number}")
                output_lines.append(f"{srt_timecode_from_seconds(start_sec)} --> {srt_timecode_from_seconds(end_sec)}")
                output_lines.append(subtitle.text)
                output_lines.append("")

                cue_number += 1

        # Write to file
        with output_path.open("w", encoding=encoding) as f:
            f.write("\n".join(output_lines))

        print(f"  → Mapped {cue_number - 1} subtitles to {total_clips} segments")
        if len(used_srt) < total_subs:
            print(f"  ⚠️ {total_subs - len(used_srt)} subtitles could not be matched")

        return True

    except Exception as e:
        print(f"❌ Failed to write timecode SRT: {e}")
        return False


def write_merged_srt(
    output_path: Path,
    source_subtitles: List,  # List[Subtitle]
    timeline_segments: List,  # List[TimelineSegment]
    nare_script_path: Path = None,
    nare_segments: Optional[List] = None,
    encoding: str = "utf-8"
) -> bool:
    """Write merged SRT file (for exports/).

    This is identical to timecode SRT but placed in exports/ directory
    for compatibility with existing workflow.

    Args:
        output_path: Output SRT file path in exports/
        source_subtitles: Original subtitle entries
        timeline_segments: Calculated timeline
        nare_script_path: Path to Nare script for text matching
        encoding: Output file encoding

    Returns:
        True if successful, False otherwise
    """
    return write_timecode_srt(
        output_path,
        source_subtitles,
        timeline_segments,
        nare_script_path,
        nare_segments=nare_segments,
        encoding=encoding
    )


if __name__ == "__main__":
    # Test timecode conversion
    print("SRT Writer Test")
    print("=" * 60)

    test_seconds = [0.0, 5.5, 65.25, 3661.5]
    for sec in test_seconds:
        tc = srt_timecode_from_seconds(sec)
        print(f"{sec:8.2f}s → {tc}")
