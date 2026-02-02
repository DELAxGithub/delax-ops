#!/usr/bin/env python3
"""Compress narration YAML segments to a target count.

Rules:
- Only merge adjacent segments with the same speaker.
- Prefer merging the shortest adjacent pair to keep pacing balanced.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


def _load_segments(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    if "gemini_tts" in data and isinstance(data["gemini_tts"], dict):
        segments = data["gemini_tts"].get("segments", [])
        if isinstance(segments, list):
            return segments, "gemini_tts"
    segments = data.get("segments", [])
    if isinstance(segments, list):
        return segments, "root"
    return [], "root"


def _merge_pair(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(left)
    left_text = str(left.get("text", "")).strip()
    right_text = str(right.get("text", "")).strip()
    joiner = " " if left_text and not left_text.endswith(("—", "——", "…", "。", "？", "！", "」")) else ""
    merged["text"] = f"{left_text}{joiner}{right_text}".strip()

    # Preserve the latter segment's break/pause if present.
    if "break_after" in right:
        merged["break_after"] = right.get("break_after")
    return merged


def _segment_length(seg: Dict[str, Any]) -> int:
    return len(str(seg.get("text", "")))


def compress_segments(segments: List[Dict[str, Any]], target: int) -> List[Dict[str, Any]]:
    if target <= 0:
        raise ValueError("target must be > 0")
    if len(segments) <= target:
        return segments

    working = list(segments)
    while len(working) > target:
        best_idx = None
        best_score = None

        for i in range(len(working) - 1):
            left = working[i]
            right = working[i + 1]
            if left.get("speaker") != right.get("speaker"):
                continue
            score = _segment_length(left) + _segment_length(right)
            if best_score is None or score < best_score:
                best_score = score
                best_idx = i

        if best_idx is None:
            # No mergeable adjacent pair left.
            break

        merged = _merge_pair(working[best_idx], working[best_idx + 1])
        working[best_idx : best_idx + 2] = [merged]

    return working


def main() -> int:
    parser = argparse.ArgumentParser(description="Compress narration YAML segments.")
    parser.add_argument("input", type=Path, help="Input YAML path")
    parser.add_argument("--target", type=int, required=True, help="Target segment count")
    parser.add_argument("--output", type=Path, required=True, help="Output YAML path")
    args = parser.parse_args()

    data = yaml.safe_load(args.input.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")

    segments, location = _load_segments(data)
    if not segments:
        raise ValueError("No segments found in YAML")

    compressed = compress_segments(segments, args.target)
    if location == "gemini_tts":
        data["gemini_tts"]["segments"] = compressed
    else:
        data["segments"] = compressed

    args.output.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"segments: {len(segments)} -> {len(compressed)}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
