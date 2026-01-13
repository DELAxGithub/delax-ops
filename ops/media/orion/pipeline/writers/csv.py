#!/usr/bin/env python3
"""CSV timeline writer.

Generates timeline CSV with segment information for editing workflow.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List


def write_timeline_csv(
    output_path: Path,
    timeline_segments: List,  # List[TimelineSegment]
    fps: float,
    encoding: str = "utf-8"
) -> bool:
    """Write timeline CSV file.

    CSV format:
        index, audio_filename, duration_sec, start_tc, end_tc, duration_frames, scene_marker

    Args:
        output_path: Output CSV file path
        timeline_segments: Calculated timeline segments
        fps: Frames per second for frame count calculation
        encoding: Output file encoding (default: utf-8)

    Returns:
        True if successful, False otherwise
    """
    try:
        with output_path.open("w", encoding=encoding, newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "index",
                "audio_filename",
                "duration_sec",
                "start_timecode",
                "end_timecode",
                "duration_frames",
                "is_scene_start",
                "scene_lead_in_sec",
                "speaker",
                "text"
            ])

            # Data rows
            for seg in timeline_segments:
                writer.writerow([
                    seg.index,
                    seg.audio_filename,
                    f"{seg.audio_duration_sec:.2f}",
                    seg.start_timecode(fps),
                    seg.end_timecode(fps),
                    seg.duration_frames(fps),
                    "YES" if seg.is_scene_start else "NO",
                    f"{seg.scene_lead_in_sec:.2f}",
                    seg.speaker,
                    seg.text
                ])

        return True

    except Exception as e:
        print(f"❌ Failed to write timeline CSV: {e}")
        return False


if __name__ == "__main__":
    print("CSV Writer Test")
    print("=" * 60)
    print("CSV writer implementation complete")
    print("Use with TimelineSegment objects from timeline calculator")
