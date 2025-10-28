#!/usr/bin/env python3
"""SRT (SubRip) format parser and validator.

Robust parser for .srt subtitle files with comprehensive validation.
Based on existing srt_merge.py but enhanced for production use.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Subtitle:
    """Represents a single subtitle entry."""

    index: int
    start_time: str  # Format: HH:MM:SS,mmm
    end_time: str    # Format: HH:MM:SS,mmm
    text: str

    def duration_ms(self) -> int:
        """Calculate duration in milliseconds."""
        return time_to_ms(self.end_time) - time_to_ms(self.start_time)

    def start_ms(self) -> int:
        """Get start time in milliseconds."""
        return time_to_ms(self.start_time)

    def end_ms(self) -> int:
        """Get end time in milliseconds."""
        return time_to_ms(self.end_time)

    def char_count(self) -> int:
        """Count characters excluding whitespace."""
        return len(re.sub(r"\s", "", self.text)) or 1

    def line_count(self) -> int:
        """Count number of lines in subtitle."""
        return len([line for line in self.text.splitlines() if line.strip()])

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate subtitle entry.

        Returns:
            (is_valid, error_message)
        """
        # Check timecode format
        if not _is_valid_timecode(self.start_time):
            return False, f"Invalid start_time format: {self.start_time}"
        if not _is_valid_timecode(self.end_time):
            return False, f"Invalid end_time format: {self.end_time}"

        # Check timecode logic
        if self.start_ms() >= self.end_ms():
            return False, f"start_time >= end_time: {self.start_time} >= {self.end_time}"

        # Check duration
        duration = self.duration_ms()
        if duration < 100:  # Minimum 0.1 second
            return False, f"Duration too short: {duration}ms"
        if duration > 15000:  # Maximum 15 seconds
            return False, f"Duration too long: {duration}ms"

        # Check text
        if not self.text.strip():
            return False, "Empty text"

        return True, None


# SRT timecode regex: HH:MM:SS,mmm
_TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")


def time_to_ms(time_str: str) -> int:
    """Convert SRT timestamp to milliseconds.

    Args:
        time_str: Timestamp in format HH:MM:SS,mmm

    Returns:
        Time in milliseconds

    Example:
        >>> time_to_ms("00:01:23,456")
        83456
    """
    match = _TIME_RE.match(time_str)
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")

    hours, minutes, seconds, milliseconds = map(int, match.groups())
    return (hours * 3_600_000 +
            minutes * 60_000 +
            seconds * 1_000 +
            milliseconds)


def ms_to_time(ms: int) -> str:
    """Convert milliseconds to SRT timestamp.

    Args:
        ms: Time in milliseconds

    Returns:
        Timestamp in format HH:MM:SS,mmm

    Example:
        >>> ms_to_time(83456)
        "00:01:23,456"
    """
    hours = ms // 3_600_000
    ms %= 3_600_000
    minutes = ms // 60_000
    ms %= 60_000
    seconds = ms // 1_000
    milliseconds = ms % 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _is_valid_timecode(time_str: str) -> bool:
    """Check if string is valid SRT timecode."""
    return _TIME_RE.match(time_str) is not None


def parse_srt(content: str) -> List[Subtitle]:
    """Parse SRT content into list of Subtitle objects.

    Args:
        content: Raw SRT file content

    Returns:
        List of Subtitle objects

    Raises:
        ValueError: If SRT format is invalid

    Example:
        >>> content = '''1
        ... 00:00:00,000 --> 00:00:05,000
        ... Hello, world!
        ...
        ... 2
        ... 00:00:05,000 --> 00:00:10,000
        ... Second subtitle.
        ... '''
        >>> subtitles = parse_srt(content)
        >>> len(subtitles)
        2
    """
    # Remove markdown code fences if present
    content = re.sub(r"```srt\s*", "", content)
    content = re.sub(r"```\s*$", "", content, flags=re.MULTILINE)

    # Split into blocks by double newline
    blocks = re.split(r"\n\s*\n", content.strip())

    subtitles: List[Subtitle] = []

    for block_idx, block in enumerate(blocks, start=1):
        lines = block.strip().splitlines()

        if len(lines) < 3:
            # Skip malformed blocks
            continue

        # Parse index
        try:
            idx = int(lines[0].strip())
        except ValueError:
            raise ValueError(
                f"Block {block_idx}: Invalid index '{lines[0]}'"
            )

        # Parse timecode line
        timecode_match = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
            lines[1]
        )
        if not timecode_match:
            raise ValueError(
                f"Block {block_idx}: Invalid timecode format '{lines[1]}'"
            )

        start_time, end_time = timecode_match.groups()

        # Parse text (lines 2+)
        text = "\n".join(lines[2:]).strip()

        subtitle = Subtitle(
            index=idx,
            start_time=start_time,
            end_time=end_time,
            text=text
        )

        # Validate subtitle
        is_valid, error = subtitle.validate()
        if not is_valid:
            raise ValueError(
                f"Block {block_idx} (index {idx}): {error}"
            )

        subtitles.append(subtitle)

    if not subtitles:
        raise ValueError("No valid subtitle entries found")

    return subtitles


def parse_srt_file(path: Path) -> List[Subtitle]:
    """Parse SRT file into list of Subtitle objects.

    Args:
        path: Path to .srt file

    Returns:
        List of Subtitle objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If SRT format is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"SRT file not found: {path}")

    content = path.read_text(encoding="utf-8")

    try:
        return parse_srt(content)
    except ValueError as e:
        raise ValueError(f"Failed to parse {path.name}: {e}")


def write_srt(subtitles: List[Subtitle], path: Path) -> None:
    """Write list of Subtitle objects to SRT file.

    Args:
        subtitles: List of Subtitle objects
        path: Output file path

    Example:
        >>> subs = [
        ...     Subtitle(1, "00:00:00,000", "00:00:05,000", "Hello"),
        ...     Subtitle(2, "00:00:05,000", "00:00:10,000", "World")
        ... ]
        >>> write_srt(subs, Path("output.srt"))
    """
    lines: List[str] = []

    for idx, sub in enumerate(subtitles, start=1):
        lines.append(str(idx))
        lines.append(f"{sub.start_time} --> {sub.end_time}")
        lines.append(sub.text)
        lines.append("")  # Blank line separator

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def validate_srt_continuity(subtitles: List[Subtitle]) -> tuple[bool, List[str]]:
    """Validate timecode continuity in subtitle sequence.

    Checks:
    - Timecodes are in ascending order
    - No overlaps between adjacent subtitles

    Args:
        subtitles: List of Subtitle objects

    Returns:
        (is_valid, list_of_errors)
    """
    errors: List[str] = []

    for i in range(len(subtitles) - 1):
        current = subtitles[i]
        next_sub = subtitles[i + 1]

        # Check ascending order
        if current.start_ms() >= next_sub.start_ms():
            errors.append(
                f"Entry {current.index} → {next_sub.index}: "
                f"Timecodes not in ascending order "
                f"({current.start_time} >= {next_sub.start_time})"
            )

        # Check for overlaps
        if current.end_ms() > next_sub.start_ms():
            errors.append(
                f"Entry {current.index} → {next_sub.index}: "
                f"Overlapping timecodes "
                f"({current.end_time} > {next_sub.start_time})"
            )

    return len(errors) == 0, errors


if __name__ == "__main__":
    # Simple test
    test_srt = """1
00:00:00,000 --> 00:00:05,000
Hello, world!

2
00:00:05,000 --> 00:00:10,000
Second subtitle.
Multiple lines.
"""

    subtitles = parse_srt(test_srt)
    print(f"Parsed {len(subtitles)} subtitle(s)")

    for sub in subtitles:
        print(f"  [{sub.index}] {sub.start_time} → {sub.end_time}")
        print(f"       {sub.text[:50]}...")

    is_valid, errors = validate_srt_continuity(subtitles)
    print(f"\nContinuity check: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        for error in errors:
            print(f"  - {error}")
