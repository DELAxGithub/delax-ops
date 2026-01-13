#!/usr/bin/env python3
"""Audio-to-subtitle mapping engine.

Maps audio segments to multiple subtitles and distributes duration
based on character count proportion.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class SubtitleMapping:
    """Maps audio segment to subtitle with duration proportion."""

    audio_index: int
    subtitle_index: int
    proportion: float  # 0.0-1.0, based on character count
    allocated_duration_sec: float


def normalize_text(text: str) -> str:
    """Normalize text for comparison.

    Args:
        text: Original text

    Returns:
        Normalized text (remove punctuation, whitespace, lowercase)
    """
    # Remove all punctuation and symbols
    text = re.sub(r'[、。！？,.!?「」『』…——\s]', '', text)
    # Lowercase for comparison
    return text.lower()


def calculate_char_count(text: str) -> int:
    """Calculate character count excluding whitespace and punctuation.

    Args:
        text: Text to count

    Returns:
        Character count
    """
    normalized = normalize_text(text)
    return len(normalized)


def find_audio_subtitle_mapping(
    narration_segments: List,  # List[NarrationSegment]
    subtitles: List,  # List[Subtitle]
    audio_segments: List  # List[AudioSegment]
) -> List[SubtitleMapping]:
    """Map audio segments to subtitles with duration allocation.

    Algorithm:
        1. For each audio segment (narration):
           - Find all subtitles that match the narration text
           - Calculate character count for each matching subtitle
           - Allocate audio duration proportionally based on char count

    Args:
        narration_segments: Narration segments (1 line = 1 audio file)
        subtitles: Subtitle entries from SRT (may be multiple per audio)
        audio_segments: Audio segments with duration info

    Returns:
        List of SubtitleMapping objects
    """
    mappings = []
    subtitle_idx = 0  # Track current subtitle position

    for audio_seg in audio_segments:
        # Find corresponding narration
        narration = narration_segments[audio_seg.index - 1]
        narration_text = normalize_text(narration.text)

        # Find matching subtitles
        matching_subtitles = []
        temp_idx = subtitle_idx

        # Look ahead to find all subtitles that belong to this audio
        while temp_idx < len(subtitles):
            subtitle = subtitles[temp_idx]
            subtitle_text = normalize_text(subtitle.text)

            # Check if subtitle text is part of narration text
            if subtitle_text in narration_text or is_fuzzy_match(subtitle_text, narration_text):
                matching_subtitles.append((temp_idx, subtitle))
                temp_idx += 1
            else:
                # Stop when we hit a subtitle that doesn't match
                break

        # If no matches found, try 1:1 mapping as fallback
        if not matching_subtitles and subtitle_idx < len(subtitles):
            matching_subtitles = [(subtitle_idx, subtitles[subtitle_idx])]
            subtitle_idx += 1

        # Calculate character count proportion
        total_chars = sum(calculate_char_count(sub.text) for _, sub in matching_subtitles)

        if total_chars == 0:
            # Edge case: empty subtitles
            total_chars = len(matching_subtitles)

        for sub_idx, subtitle in matching_subtitles:
            char_count = calculate_char_count(subtitle.text)
            proportion = char_count / total_chars if total_chars > 0 else 1.0 / len(matching_subtitles)
            allocated_duration = audio_seg.duration_sec * proportion

            mapping = SubtitleMapping(
                audio_index=audio_seg.index,
                subtitle_index=sub_idx + 1,  # 1-indexed
                proportion=proportion,
                allocated_duration_sec=allocated_duration
            )
            mappings.append(mapping)

        # Update subtitle index for next audio segment
        subtitle_idx = temp_idx

    return mappings


def is_fuzzy_match(text1: str, text2: str, threshold: float = 0.8) -> bool:
    """Check if two texts are similar enough.

    Args:
        text1: First text (normalized)
        text2: Second text (normalized)
        threshold: Similarity threshold (0.0-1.0)

    Returns:
        True if texts are similar enough
    """
    # Simple fuzzy match: check if one is substring of the other
    # or if they share significant overlap
    if text1 in text2 or text2 in text1:
        return True

    # Calculate overlap ratio
    overlap = sum(1 for c in text1 if c in text2)
    ratio = overlap / max(len(text1), len(text2), 1)

    return ratio >= threshold


if __name__ == "__main__":
    # Test text normalization
    print("Text Normalization Test")
    print("=" * 60)

    test_cases = [
        "専門を深めるべきか？視野を広げるべきか？",
        "専門を深めるべきか 視野を広げるべきか",
        "キャリアプランの迷いは、優柔不断なのか、それとも時代の要請なのか？",
    ]

    for text in test_cases:
        normalized = normalize_text(text)
        char_count = calculate_char_count(text)
        print(f"Original:   {text}")
        print(f"Normalized: {normalized}")
        print(f"Char count: {char_count}")
        print()
