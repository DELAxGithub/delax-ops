"""Core timeline builder shared by Premiere/Resolve auto-edit kits.

This module focuses on data preparation (CSV → segments → track placements)
so that front-ends (Premiere CEP/UXP panel, Resolve script) can consume the
same intermediate structure. XML / API specific emission is handled by the
NLE-specific layers.
"""

from __future__ import annotations

import csv
import dataclasses
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import yaml

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FpsSpec:
    timebase: int
    ntsc: bool = True

    @property
    def fps(self) -> float:
        if self.ntsc:
            return self.timebase * 1000 / 1001
        return float(self.timebase)


@dataclass
class TemplateTrack:
    name: str
    source: Optional[str] = None
    source_channel: Optional[int] = None


@dataclass
class TemplateDefinition:
    template_id: str
    version: str
    fps: FpsSpec
    gap_seconds: float
    video_tracks: List[TemplateTrack]
    audio_tracks: List[TemplateTrack]
    color_map: Dict[str, str]
    path_map: Dict[str, str] = dataclasses.field(default_factory=dict)


@dataclass
class CsvRow:
    speaker: str
    in_timecode: str
    out_timecode: str
    transcript: str
    color: str


@dataclass
class Segment:
    """Normalized block or gap derived from CSV."""

    kind: str  # "block" or "gap"
    start_frames: int
    end_frames: int
    color: Optional[str] = None
    transcript: Optional[str] = None
    raw_rows: List[CsvRow] = field(default_factory=list)

    @property
    def duration_frames(self) -> int:
        return max(0, self.end_frames - self.start_frames)


@dataclass
class ClipPlacement:
    track_name: str
    source_name: str
    start_frames: int
    end_frames: int
    source_in: int
    source_out: int
    label: Optional[str] = None
    transcript: Optional[str] = None


@dataclass
class Timeline:
    fps: float
    placements: List[ClipPlacement]
    gaps: List[Segment]
    diagnostics: Dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# CSV Utilities
# ---------------------------------------------------------------------------


TARGET_HEADERS = [
    "Speaker Name",
    "イン点",
    "アウト点",
    "文字起こし",
    "色選択",
]


class CsvFormatError(ValueError):
    pass


def load_csv_rows(csv_path: Path) -> List[CsvRow]:
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [h for h in TARGET_HEADERS if h not in reader.fieldnames]
        if missing:
            raise CsvFormatError(f"Missing headers: {missing}")
        rows: List[CsvRow] = []
        for raw in reader:
            if not raw:
                continue
            speaker = (raw.get("Speaker Name") or "").strip()
            in_tc = (raw.get("イン点") or "").strip()
            out_tc = (raw.get("アウト点") or "").strip()
            text = (raw.get("文字起こし") or "").strip()
            color = (raw.get("色選択") or "").strip()
            if not in_tc and not out_tc and not color:
                continue
            rows.append(
                CsvRow(
                    speaker=speaker,
                    in_timecode=in_tc,
                    out_timecode=out_tc,
                    transcript=text,
                    color=color,
                )
            )
    return rows


# ---------------------------------------------------------------------------
# Timecode helpers
# ---------------------------------------------------------------------------


def normalize_timecode(tc: str) -> str:
    return tc.replace(";", ":")


def timecode_to_frames(tc: str, fps: float) -> int:
    tc = normalize_timecode(tc)
    parts = tc.split(":")
    if len(parts) != 4:
        raise CsvFormatError(f"Invalid timecode: {tc}")
    hours, minutes, seconds, frames = [int(p or 0) for p in parts]
    total_seconds = hours * 3600 + minutes * 60 + seconds
    base_frames = total_seconds * fps
    return int(round(base_frames + frames))


# ---------------------------------------------------------------------------
# Segment builder
# ---------------------------------------------------------------------------


def build_segments(rows: Sequence[CsvRow], fps: float) -> Tuple[List[Segment], List[str]]:
    segments: List[Segment] = []
    warnings: List[str] = []
    current_color: Optional[str] = None
    current_block: Optional[Segment] = None

    for row in rows:
        color = row.color
        if color.upper().startswith("GAP"):
            if current_block:
                segments.append(current_block)
                current_block = None
                current_color = None
            if not row.in_timecode or not row.out_timecode:
                warnings.append(f"GAP 行にイン/アウトが未設定: {row}")
                continue
            start = timecode_to_frames(row.in_timecode, fps)
            end = timecode_to_frames(row.out_timecode, fps)
            if end <= start:
                warnings.append(f"GAP 行のアウトがイン以下: {row}")
                continue
            segments.append(
                Segment(
                    kind="gap",
                    start_frames=start,
                    end_frames=end,
                    color=color,
                    transcript=row.transcript,
                    raw_rows=[row],
                )
            )
            continue

        if not row.in_timecode or not row.out_timecode or not color:
            warnings.append(f"ブロック行の必須項目欠落: {row}")
            continue

        in_frames = timecode_to_frames(row.in_timecode, fps)
        out_frames = timecode_to_frames(row.out_timecode, fps)
        if out_frames <= in_frames:
            warnings.append(f"アウトがイン以下: {row}")
            continue

        if current_color != color:
            if current_block:
                segments.append(current_block)
            current_color = color
            current_block = Segment(
                kind="block",
                start_frames=in_frames,
                end_frames=out_frames,
                color=color,
                transcript=row.transcript,
                raw_rows=[row],
            )
        else:
            assert current_block is not None
            current_block.end_frames = out_frames
            current_block.raw_rows.append(row)

    if current_block:
        segments.append(current_block)

    return segments, warnings


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------


def load_template(template_path: Path) -> TemplateDefinition:
    data = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    fps_data = data.get("fps", {})
    video_tracks = [TemplateTrack(**track) for track in data.get("tracks", {}).get("video", [])]
    audio_tracks = [TemplateTrack(**track) for track in data.get("tracks", {}).get("audio", [])]
    color_map = data.get("color_map", {})
    return TemplateDefinition(
        template_id=data.get("id", template_path.stem),
        version=str(data.get("version", "0.0.0")),
        fps=FpsSpec(
            timebase=int(fps_data.get("timebase", 24)),
            ntsc=bool(fps_data.get("ntsc", True)),
        ),
        gap_seconds=float(data.get("gap_seconds", 5.0)),
        video_tracks=video_tracks,
        audio_tracks=audio_tracks,
        color_map={k.lower(): v for k, v in color_map.items()},
        path_map=data.get("path_map", {}),
    )


# ---------------------------------------------------------------------------
# Placement builder
# ---------------------------------------------------------------------------


def apply_color_map(color: str, color_map: Dict[str, str]) -> str:
    if not color:
        return ""
    if color in color_map.values():  # already normalized
        return color
    return color_map.get(color.lower(), "") or ""


def build_timeline(csv_path: Path, template_path: Path) -> Timeline:
    template = load_template(template_path)
    rows = load_csv_rows(csv_path)
    fps = template.fps.fps
    segments, warnings = build_segments(rows, fps)

    gap_frames = int(round(template.gap_seconds * fps))

    placements: List[ClipPlacement] = []
    timeline_position = 0
    gap_segments: List[Segment] = []

    for segment in segments:
        if segment.kind == "gap":
            gap_segments.append(segment)
            timeline_position += segment.duration_frames
            continue

        # block
        label = apply_color_map(segment.color or "", template.color_map)
        for track in template.video_tracks:
            source_name = track.source or track.name
            placements.append(
                ClipPlacement(
                    track_name=track.name,
                    source_name=source_name,
                    start_frames=timeline_position,
                    end_frames=timeline_position + segment.duration_frames,
                    source_in=segment.start_frames,
                    source_out=segment.end_frames,
                    label=label,
                    transcript=segment.transcript,
                )
            )
        for track in template.audio_tracks:
            source_name = track.source or track.name
            placements.append(
                ClipPlacement(
                    track_name=track.name,
                    source_name=source_name,
                    start_frames=timeline_position,
                    end_frames=timeline_position + segment.duration_frames,
                    source_in=segment.start_frames,
                    source_out=segment.end_frames,
                    label=label,
                    transcript=segment.transcript,
                )
            )
        timeline_position += segment.duration_frames + gap_frames

    diagnostics = {
        "csv_path": str(csv_path),
        "template_id": template.template_id,
        "template_version": template.version,
        "warnings": warnings,
        "segments": len(segments),
    }

    return Timeline(
        fps=fps,
        placements=placements,
        gaps=gap_segments,
        diagnostics=diagnostics,
    )


__all__ = [
    "FpsSpec",
    "TemplateTrack",
    "TemplateDefinition",
    "CsvRow",
    "Segment",
    "ClipPlacement",
    "Timeline",
    "load_csv_rows",
    "build_segments",
    "load_template",
    "build_timeline",
]

