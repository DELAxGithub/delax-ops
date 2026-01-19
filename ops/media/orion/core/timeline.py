#!/usr/bin/env python3
"""Timeline calculation engine for Orion Pipeline v2.

Calculates timecodes for audio segments based on:
- Audio segment durations
- Scene lead-in intervals (default: 3.0 seconds)
- NTSC framerate (29.97 fps)
- Dynamic gap calculation (role, question, long text, scene transition)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


# Gap calculation constants (from build_timeline_orionep2.py)
BASE_GAP_NA = 0.35       # Narration base gap
BASE_GAP_DL = 0.60       # Dialogue base gap
SCENE_GAP = 1.80         # Scene transition minimum gap
QUESTION_BONUS = 0.30    # Question mark bonus
LONG_TEXT_COEF = 0.004   # Long text coefficient (sec per char)
LONG_TEXT_MAX = 0.40     # Long text gap maximum


def compute_gap(text: str, role: str = "NA", is_scene_end: bool = False) -> float:
    """Calculate gap duration after a segment.

    Args:
        text: Segment text content
        role: Role type ("NA" for narration, "DL" for dialogue)
        is_scene_end: Whether this segment ends a scene

    Returns:
        Gap duration in seconds

    Rules:
        - Base: 0.35s (narration) or 0.60s (dialogue)
        - Question mark: +0.30s
        - Long text: +min(0.40s, len(text) × 0.004s)
        - Scene end: max(calculated, 1.80s)
    """
    role_upper = role.upper()
    base = BASE_GAP_DL if role_upper in ('DL', 'Q', 'DIALOGUE') else BASE_GAP_NA

    bonus = 0.0

    # Question bonus
    if '？' in text or '?' in text:
        bonus += QUESTION_BONUS

    # Long text bonus
    if text:
        bonus += min(LONG_TEXT_MAX, len(text) * LONG_TEXT_COEF)

    gap = base + bonus

    # Scene transition minimum
    if is_scene_end:
        gap = max(gap, SCENE_GAP)

    return round(gap, 3)


@dataclass
class TimelineSegment:
    """Timeline segment with timecode information."""

    index: int
    audio_filename: str
    audio_duration_sec: float

    # Timecodes in seconds
    start_time_sec: float
    end_time_sec: float

    # Scene metadata
    is_scene_start: bool = False
    scene_lead_in_sec: float = 0.0

    # Audio file trimming (for when one audio maps to multiple subtitles)
    audio_in_offset_sec: float = 0.0  # Offset into audio file to start playback
    audio_out_offset_sec: float = 0.0  # Offset into audio file to end playback (0 = use full duration)

    # Narration content
    speaker: str = ""  # Speaker name (e.g., "ナレーター", "主人公")
    text: str = ""  # Original narration text

    def start_timecode(self, fps: float) -> str:
        """Convert start time to NTSC timecode format.

        Args:
            fps: Frames per second (e.g., 29.97 for NTSC)

        Returns:
            Timecode string in format HH:MM:SS:FF
        """
        return seconds_to_timecode(self.start_time_sec, fps)

    def end_timecode(self, fps: float) -> str:
        """Convert end time to NTSC timecode format.

        Args:
            fps: Frames per second (e.g., 29.97 for NTSC)

        Returns:
            Timecode string in format HH:MM:SS:FF
        """
        return seconds_to_timecode(self.end_time_sec, fps)

    def duration_frames(self, fps: float) -> int:
        """Calculate segment duration in frames.

        Args:
            fps: Frames per second

        Returns:
            Duration in frames
        """
        return int((self.end_time_sec - self.start_time_sec) * fps)


def seconds_to_timecode(seconds: float, fps: float) -> str:
    """Convert seconds to NTSC timecode format.

    Args:
        seconds: Time in seconds
        fps: Frames per second (e.g., 29.97)

    Returns:
        Timecode string in format HH:MM:SS:FF

    Example:
        >>> seconds_to_timecode(3661.5, 29.97)
        '01:01:01:15'
    """
    total_frames = int(seconds * fps)

    # Use rounded fps (30 for NTSC 29.97) for frame counting
    fps_rounded = int(round(fps))
    frames = total_frames % fps_rounded
    total_seconds = total_frames // fps_rounded

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


def timecode_to_seconds(timecode: str, fps: float) -> float:
    """Convert NTSC timecode to seconds.

    Args:
        timecode: Timecode string in format HH:MM:SS:FF
        fps: Frames per second

    Returns:
        Time in seconds

    Example:
        >>> timecode_to_seconds('01:01:01:15', 29.97)
        3661.5
    """
    parts = timecode.split(":")
    if len(parts) != 4:
        raise ValueError(f"Invalid timecode format: {timecode}")

    hours, minutes, seconds, frames = map(int, parts)

    total_seconds = hours * 3600 + minutes * 60 + seconds
    total_seconds += frames / fps

    return total_seconds


class TimelineCalculator:
    """Calculate timeline with scene transitions."""

    def __init__(
        self,
        fps: float,
        scene_lead_in_sec: float = 3.0,
        clip_gap_frames: int = 0
    ):
        """Initialize timeline calculator.

        Args:
            fps: Frames per second (e.g., 29.97 for NTSC)
            scene_lead_in_sec: Lead-in time before each scene (default: 3.0s)
            clip_gap_frames: Gap in frames between audio clips (default: 0)
        """
        self.fps = fps
        self.scene_lead_in_sec = scene_lead_in_sec
        self.clip_gap_frames = clip_gap_frames
        self.clip_gap_sec = clip_gap_frames / fps if fps > 0 else 0.0

    def calculate_timeline(
        self,
        audio_segments: List,  # List[AudioSegment]
        narration_segments: List = None,  # List[NarrationSegment]
        scene_markers: List[int] = None,
        scene_end_indices: List[int] = None
    ) -> List[TimelineSegment]:
        """Calculate timeline for audio segments with dynamic gaps.

        Args:
            audio_segments: List of AudioSegment objects from TTS engine
            narration_segments: List of NarrationSegment objects for text content (optional)
            scene_markers: List of segment indices that start new scenes (optional)
            scene_end_indices: List of segment indices that end scenes (optional)

        Returns:
            List of TimelineSegment objects with calculated timecodes
        """
        if scene_markers is None:
            scene_markers = []
        if scene_end_indices is None:
            scene_end_indices = []

        timeline_segments = []
        current_time = 0.0

        for i, audio_seg in enumerate(audio_segments):
            # Check if this is a scene start
            is_scene_start = i in scene_markers
            lead_in = self.scene_lead_in_sec if is_scene_start and i > 0 else 0.0

            # Add lead-in time for scene transitions
            current_time += lead_in

            # Calculate segment timecodes
            start_time = current_time
            end_time = current_time + audio_seg.duration_sec

            # Get speaker and text from narration segments if available
            speaker = ""
            text = ""
            if narration_segments and i < len(narration_segments):
                nare_seg = narration_segments[i]
                speaker = getattr(nare_seg, 'speaker', '')
                text = getattr(nare_seg, 'text', '')

            timeline_seg = TimelineSegment(
                index=audio_seg.index,
                audio_filename=audio_seg.filename,
                audio_duration_sec=audio_seg.duration_sec,
                start_time_sec=start_time,
                end_time_sec=end_time,
                is_scene_start=is_scene_start,
                scene_lead_in_sec=lead_in,
                speaker=speaker,
                text=text
            )

            timeline_segments.append(timeline_seg)

            # Advance current time with optional clip gap
            current_time = end_time
            if self.clip_gap_sec > 0 and i < len(audio_segments) - 1:
                current_time += self.clip_gap_sec

        return timeline_segments

    def get_total_duration(self, timeline: List[TimelineSegment]) -> float:
        """Get total timeline duration in seconds.

        Args:
            timeline: List of TimelineSegment objects

        Returns:
            Total duration in seconds
        """
        if not timeline:
            return 0.0

        return timeline[-1].end_time_sec

    def format_timeline_summary(self, timeline: List[TimelineSegment]) -> str:
        """Format timeline summary for display.

        Args:
            timeline: List of TimelineSegment objects

        Returns:
            Formatted summary string
        """
        total_duration = self.get_total_duration(timeline)
        scene_count = sum(1 for seg in timeline if seg.is_scene_start)

        lines = [
            f"Timeline Summary:",
            f"  Total segments: {len(timeline)}",
            f"  Total duration: {total_duration:.2f}s ({total_duration/60:.1f}min)",
            f"  Scene transitions: {scene_count}",
            f"  Final timecode: {seconds_to_timecode(total_duration, self.fps)}",
        ]

        return "\n".join(lines)

    def calculate_subtitle_timeline(
        self,
        mappings: List,  # List[SubtitleMapping]
        scene_markers: List[int] = None
    ) -> List[TimelineSegment]:
        """Calculate timeline for subtitles based on audio-subtitle mapping.

        Args:
            mappings: List of SubtitleMapping objects with duration allocation
            scene_markers: List of subtitle indices that start new scenes (optional)

        Returns:
            List of TimelineSegment objects with subtitle timecodes
        """
        if scene_markers is None:
            scene_markers = []

        timeline_segments = []
        current_time = 0.0

        # Track audio file offsets for multiple subtitles per audio
        audio_offset_tracker = {}  # {audio_index: cumulative_offset_sec}

        for mapping in mappings:
            # Check if this subtitle starts a scene
            is_scene_start = mapping.subtitle_index in scene_markers
            lead_in = self.scene_lead_in_sec if is_scene_start and len(timeline_segments) > 0 else 0.0

            # Add lead-in time for scene transitions
            current_time += lead_in

            # Calculate subtitle timecodes based on allocated duration
            start_time = current_time
            end_time = current_time + mapping.allocated_duration_sec

            # Calculate audio file in/out offsets
            audio_idx = mapping.audio_index
            audio_in_offset = audio_offset_tracker.get(audio_idx, 0.0)
            audio_out_offset = audio_in_offset + mapping.allocated_duration_sec

            # Update tracker for next subtitle using same audio
            audio_offset_tracker[audio_idx] = audio_out_offset

            timeline_seg = TimelineSegment(
                index=mapping.subtitle_index,
                audio_filename=f"audio_{mapping.audio_index:03d}",  # Reference to audio
                audio_duration_sec=mapping.allocated_duration_sec,
                start_time_sec=start_time,
                end_time_sec=end_time,
                is_scene_start=is_scene_start,
                scene_lead_in_sec=lead_in,
                audio_in_offset_sec=audio_in_offset,
                audio_out_offset_sec=audio_out_offset
            )

            timeline_segments.append(timeline_seg)

            # Advance current time
            current_time = end_time

        return timeline_segments


def detect_scene_markers(
    subtitles: List,  # List[Subtitle]
    gap_threshold_sec: float = 5.0
) -> List[int]:
    """Detect potential scene markers from subtitle gaps.

    Args:
        subtitles: List of Subtitle objects from SRT parser
        gap_threshold_sec: Minimum gap to consider a scene transition (default: 5.0s)

    Returns:
        List of subtitle indices that likely start new scenes
    """
    scene_markers = []

    for i in range(1, len(subtitles)):
        prev_sub = subtitles[i - 1]
        curr_sub = subtitles[i]

        # Calculate gap between subtitles
        prev_end_ms = prev_sub.end_ms()
        curr_start_ms = curr_sub.start_ms()

        gap_sec = (curr_start_ms - prev_end_ms) / 1000.0

        # If gap exceeds threshold, mark as scene transition
        if gap_sec >= gap_threshold_sec:
            scene_markers.append(i)

    return scene_markers


if __name__ == "__main__":
    # Example usage
    print("Timeline Calculator Test")
    print("=" * 60)

    # Test timecode conversion
    test_seconds = 3661.5  # 1 hour, 1 minute, 1.5 seconds
    test_fps = 29.97

    timecode = seconds_to_timecode(test_seconds, test_fps)
    print(f"Seconds: {test_seconds} → Timecode: {timecode}")

    back_to_seconds = timecode_to_seconds(timecode, test_fps)
    print(f"Timecode: {timecode} → Seconds: {back_to_seconds:.2f}")
    print()

    # Test timeline calculation
    from dataclasses import dataclass as mock_dataclass

    @mock_dataclass
    class MockAudioSegment:
        index: int
        filename: str
        duration_sec: float

    mock_segments = [
        MockAudioSegment(1, "test_001.mp3", 5.0),
        MockAudioSegment(2, "test_002.mp3", 7.5),
        MockAudioSegment(3, "test_003.mp3", 4.2),  # Scene transition
        MockAudioSegment(4, "test_004.mp3", 6.3),
    ]

    calculator = TimelineCalculator(fps=29.97, scene_lead_in_sec=3.0)
    timeline = calculator.calculate_timeline(mock_segments, scene_markers=[2])

    print("Timeline Calculation:")
    print("-" * 60)
    for seg in timeline:
        scene_marker = " [SCENE]" if seg.is_scene_start else ""
        print(f"[{seg.index:03d}] {seg.start_timecode(29.97)} - {seg.end_timecode(29.97)}"
              f" ({seg.audio_duration_sec:.2f}s){scene_marker}")

    print()
    print(calculator.format_timeline_summary(timeline))
