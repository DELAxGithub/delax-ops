#!/usr/bin/env python3
"""Markdown narration script parser.

Parses simple line-by-line narration scripts (ep{N}nare.md).
Each non-empty line becomes one TTS segment.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class NarrationSegment:
    """Represents a single narration segment for TTS."""

    index: int
    text: str
    speaker: str = "ナレーター"

    def __post_init__(self) -> None:
        """Validate segment."""
        if not self.text.strip():
            raise ValueError(f"Segment {self.index}: Empty text")

    def char_count(self) -> int:
        """Count characters excluding whitespace."""
        return len(re.sub(r"\s", "", self.text))

    def audio_filename(self, project: str) -> str:
        """Generate audio filename for this segment.

        Args:
            project: Project name (e.g., "OrionEp11")

        Returns:
            Filename like "OrionEp11_001.mp3"
        """
        return f"{project}_{self.index:03d}.mp3"


def parse_narration_markdown(content: str) -> List[NarrationSegment]:
    """Parse narration markdown into segments.

    Format: Simple line-by-line narration.
    - Each non-empty line = 1 segment
    - Empty lines are ignored
    - Comments (lines starting with #) are ignored

    Args:
        content: Markdown file content

    Returns:
        List of NarrationSegment objects

    Example:
        >>> content = '''
        ... 専門を深めるべきか？
        ... キャリアプランの迷いは、優柔不断なのか。
        ... '''
        >>> segments = parse_narration_markdown(content)
        >>> len(segments)
        2
    """
    segments: List[NarrationSegment] = []
    index = 1

    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip comments
        if line.startswith("#"):
            continue

        # Skip markdown headings (##, ###, etc.)
        if re.match(r"^#{1,6}\s+", line):
            continue

        # Skip horizontal rules
        if re.fullmatch(r"[-—━─]{3,}", line):
            continue

        # Create segment
        segment = NarrationSegment(
            index=index,
            text=line,
            speaker="ナレーター"
        )

        segments.append(segment)
        index += 1

    if not segments:
        raise ValueError("No narration segments found")

    return segments


def parse_narration_file(path: Path) -> List[NarrationSegment]:
    """Parse narration markdown file.

    Args:
        path: Path to .md file

    Returns:
        List of NarrationSegment objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If parsing fails
    """
    if not path.exists():
        raise FileNotFoundError(f"Narration file not found: {path}")

    content = path.read_text(encoding="utf-8")

    try:
        return parse_narration_markdown(content)
    except ValueError as e:
        raise ValueError(f"Failed to parse {path.name}: {e}")


def parse_narration_yaml(path: Path) -> List[NarrationSegment]:
    """Parse narration YAML (ep{N}nare.yaml) into segments.

    Args:
        path: Path to YAML file

    Returns:
        List of NarrationSegment objects
    """
    if not path.exists():
        raise FileNotFoundError(f"Narration YAML not found: {path}")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse YAML: {path}") from exc

    segments_data = []
    if isinstance(data, dict):
        segments_data = data.get("gemini_tts", {}).get("segments", [])
        if not segments_data:
            segments_data = data.get("segments", [])

        # Support episodes structure (e.g., episodes[0].segments)
        if not segments_data and "episodes" in data and isinstance(data["episodes"], list):
            if len(data["episodes"]) > 0 and "segments" in data["episodes"][0]:
                segments_data = data["episodes"][0]["segments"]

    if not segments_data:
        raise ValueError(f"No segments found in narration YAML: {path.name}")

    segments: List[NarrationSegment] = []

    for index, entry in enumerate(segments_data, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid YAML segment #{index} in {path.name}")

        text = entry.get("text")
        if not text or not str(text).strip():
            raise ValueError(f"Segment #{index} has empty text in {path.name}")

        speaker = entry.get("speaker") or "ナレーター"

        segments.append(
            NarrationSegment(
                index=index,
                text=str(text).strip(),
                speaker=str(speaker)
            )
        )

    return segments


def parse_script_section_markers(script_path: Path) -> List[int]:
    """Parse original script file to find section markers.

    Detects lines with time-coded section headers like 【00:00-01:00】アバン
    and maps them to narration segment indices.

    Args:
        script_path: Path to original script .md file (e.g., orinonep11.md)

    Returns:
        List of segment indices (1-based) where sections start
        Empty list if file doesn't exist or has no markers

    Example:
        >>> markers = parse_script_section_markers(Path("orinonep11.md"))
        >>> markers
        [1, 9, 17, 29, 35, 51, 57, 63, 75]
    """
    if not script_path.exists():
        return []

    try:
        content = script_path.read_text(encoding="utf-8")
    except Exception:
        return []

    section_indices = []
    narration_line_count = 0

    for line in content.splitlines():
        line_stripped = line.strip()

        # Skip empty lines
        if not line_stripped:
            continue

        # Check if this is a time-coded section header
        # Pattern: 【HH:MM-HH:MM】タイトル
        if re.match(r"^【\d{2}:\d{2}-\d{2}:\d{2}】", line_stripped):
            # This is a section header - mark the NEXT narration line
            # (narration_line_count + 1 because we haven't incremented yet)
            section_indices.append(narration_line_count + 1)
            continue

        # Check if this is a テロップ marker (skip, not narration)
        if line_stripped.startswith("【テロップ】"):
            continue

        # Check if this is a comment or heading (skip, not narration)
        if line_stripped.startswith("#"):
            continue

        # Check if this is a horizontal rule (skip)
        if re.fullmatch(r"[-—━─]{3,}", line_stripped):
            continue

        # Check if this contains speaker annotation (e.g., "上司（男声・真剣に）：")
        # These are narration lines but may have special formatting
        # For now, count them as regular narration

        # This is a narration line
        narration_line_count += 1

    return section_indices


def validate_audio_files(
    segments: List[NarrationSegment],
    audio_dir: Path,
    project: str
) -> tuple[bool, List[str]]:
    """Validate that audio files exist for all segments.

    Args:
        segments: List of narration segments
        audio_dir: Directory containing audio files
        project: Project name (e.g., "OrionEp11")

    Returns:
        (all_exist, list_of_missing_files)
    """
    missing: List[str] = []

    if not audio_dir.exists():
        return False, [f"Audio directory not found: {audio_dir}"]

    for segment in segments:
        filename = segment.audio_filename(project)
        audio_path = audio_dir / filename

        if not audio_path.exists():
            missing.append(filename)

    return len(missing) == 0, missing


if __name__ == "__main__":
    # Simple test
    test_md = """
# Test Narration

専門を深めるべきか？視野を広げるべきか？
キャリアプランの迷いは、優柔不断なのか、それとも時代の要請なのか？

---

ようこそ、オリオンの会議室へ。
"""

    segments = parse_narration_markdown(test_md)
    print(f"Parsed {len(segments)} narration segment(s)")

    for seg in segments:
        print(f"  [{seg.index:03d}] {seg.text[:50]}...")
        print(f"         → {seg.audio_filename('OrionEp11')}")

    print("\n✅ Markdown parser test passed")
