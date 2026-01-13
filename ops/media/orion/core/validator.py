#!/usr/bin/env python3
"""Input/output validation for Orion Pipeline v2.

Provides comprehensive validation for:
- Input files (SRT, YAML, Markdown, CSV)
- Output consistency (entry count, text similarity, timecode continuity)
- Pipeline configuration
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .parsers.srt import Subtitle, parse_srt_file, validate_srt_continuity


@dataclass
class ValidationResult:
    """Result of a validation check."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def __bool__(self) -> bool:
        return self.is_valid

    def summary(self) -> str:
        """Generate human-readable summary."""
        status = "✅ PASS" if self.is_valid else "❌ FAIL"
        lines = [status]

        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for error in self.errors:
                lines.append(f"    - {error}")

        if self.warnings:
            lines.append(f"  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"    - {warning}")

        return "\n".join(lines)


def validate_srt_file(path: Path) -> ValidationResult:
    """Validate SRT file format and structure.

    Checks:
    - File exists and is readable
    - Valid SRT syntax
    - Timecode format
    - Timecode continuity
    - Subtitle duration ranges

    Args:
        path: Path to .srt file

    Returns:
        ValidationResult with detailed errors/warnings
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Check file existence
    if not path.exists():
        errors.append(f"File not found: {path}")
        return ValidationResult(False, errors, warnings)

    # Check file extension
    if path.suffix.lower() != ".srt":
        warnings.append(f"Expected .srt extension, got {path.suffix}")

    # Parse SRT
    try:
        subtitles = parse_srt_file(path)
    except ValueError as e:
        errors.append(f"Parse error: {e}")
        return ValidationResult(False, errors, warnings)

    # Check entry count
    if len(subtitles) == 0:
        errors.append("No subtitle entries found")
        return ValidationResult(False, errors, warnings)

    if len(subtitles) < 10:
        warnings.append(f"Low entry count: {len(subtitles)}")

    # Check timecode continuity
    is_continuous, continuity_errors = validate_srt_continuity(subtitles)
    if not is_continuous:
        errors.extend(continuity_errors)

    # Check for suspicious patterns
    for sub in subtitles:
        # Very short duration
        if sub.duration_ms() < 800:
            warnings.append(
                f"Entry {sub.index}: Very short duration "
                f"({sub.duration_ms()}ms)"
            )

        # Very long duration
        if sub.duration_ms() > 10000:
            warnings.append(
                f"Entry {sub.index}: Very long duration "
                f"({sub.duration_ms()}ms)"
            )

        # Too many lines
        if sub.line_count() > 3:
            warnings.append(
                f"Entry {sub.index}: Too many lines ({sub.line_count()})"
            )

    is_valid = len(errors) == 0
    return ValidationResult(is_valid, errors, warnings)


def validate_yaml_config(path: Path, schema: Optional[Dict] = None) -> ValidationResult:
    """Validate YAML configuration file.

    Args:
        path: Path to .yaml file
        schema: Optional schema dictionary for validation

    Returns:
        ValidationResult
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Check file existence
    if not path.exists():
        errors.append(f"File not found: {path}")
        return ValidationResult(False, errors, warnings)

    # Parse YAML
    try:
        with path.open(encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
        return ValidationResult(False, errors, warnings)

    if config is None:
        errors.append("Empty YAML file")
        return ValidationResult(False, errors, warnings)

    # Schema validation (if provided)
    if schema:
        # Basic schema validation
        for required_key in schema.get("required", []):
            if required_key not in config:
                errors.append(f"Missing required key: {required_key}")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid, errors, warnings)


def validate_project_structure(project_dir: Path) -> ValidationResult:
    """Validate project directory structure.

    Checks for presence of required input files:
    - ep{N}.srt (required)
    - orinonep{N}.md or ep{N}nare.md (at least one)
    - orionep{N}_tts.yaml (recommended)

    Args:
        project_dir: Path to project directory

    Returns:
        ValidationResult
    """
    errors: List[str] = []
    warnings: List[str] = []

    inputs_dir = project_dir / "inputs"
    if not inputs_dir.exists():
        errors.append(f"inputs/ directory not found: {inputs_dir}")
        return ValidationResult(False, errors, warnings)

    # Check for ep{N}.srt
    srt_files = list(inputs_dir.glob("ep*.srt"))
    if not srt_files:
        errors.append("No ep*.srt file found in inputs/")
    elif len(srt_files) > 1:
        warnings.append(f"Multiple SRT files found: {[f.name for f in srt_files]}")

    # Check for narration source
    md_files = list(inputs_dir.glob("*nare*.md")) + list(inputs_dir.glob("orionon*.md"))
    yaml_files = list(inputs_dir.glob("*nareyaml*.yaml")) + list(inputs_dir.glob("*nare*.yaml"))

    if not md_files and not yaml_files:
        errors.append("No narration source found (*.md or *nareyaml*.yaml)")

    # Check for TTS config
    tts_yaml = list(inputs_dir.glob("*tts*.yaml"))
    if not tts_yaml:
        warnings.append("No TTS config file (*tts*.yaml) found")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid, errors, warnings)


def validate_output_consistency(
    source_srt: Path,
    output_srt: Path,
    tolerance: float = 0.05,
    similarity_min: float = 0.95
) -> ValidationResult:
    """Validate output SRT consistency against source.

    Checks:
    - Entry count match (within tolerance)
    - Text similarity (configurable threshold)
    - Timecode continuity

    Args:
        source_srt: Original subtitle file
        output_srt: Pipeline output subtitle file
        tolerance: Acceptable entry count difference ratio
        similarity_min: Minimum acceptable text similarity ratio

    Returns:
        ValidationResult
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Parse both files
    try:
        source_subs = parse_srt_file(source_srt)
    except ValueError as e:
        errors.append(f"Source SRT error: {e}")
        return ValidationResult(False, errors, warnings)

    try:
        output_subs = parse_srt_file(output_srt)
    except ValueError as e:
        errors.append(f"Output SRT error: {e}")
        return ValidationResult(False, errors, warnings)

    # Check entry count
    source_count = len(source_subs)
    output_count = len(output_subs)

    count_diff_ratio = abs(output_count - source_count) / source_count

    if count_diff_ratio > tolerance:
        errors.append(
            f"Entry count mismatch: source={source_count}, "
            f"output={output_count} (diff={count_diff_ratio:.1%})"
        )
    elif count_diff_ratio > 0:
        warnings.append(
            f"Entry count difference: source={source_count}, "
            f"output={output_count} (diff={count_diff_ratio:.1%})"
        )

    # Check text similarity
    source_text = " ".join(sub.text for sub in source_subs)
    output_text = " ".join(sub.text for sub in output_subs)

    similarity = text_similarity(source_text, output_text)

    if similarity < similarity_min:
        errors.append(
            f"Low text similarity: {similarity:.2%} (expected ≥{similarity_min:.0%})"
        )
    else:
        warning_threshold = min(similarity_min + 0.02, 0.99)
        if similarity < warning_threshold:
            warnings.append(
                f"Moderate text similarity: {similarity:.2%}"
            )

    # Check output continuity
    is_continuous, continuity_errors = validate_srt_continuity(output_subs)
    if not is_continuous:
        errors.extend(continuity_errors)

    is_valid = len(errors) == 0
    return ValidationResult(is_valid, errors, warnings)


def validate_timeline_alignment(
    timeline_segments,
    audio_segments,
    duration_tolerance: float = 0.05
) -> ValidationResult:
    """Validate alignment between timeline segments and audio segments."""

    errors: List[str] = []
    warnings: List[str] = []

    if not timeline_segments:
        errors.append("No timeline segments available")
        return ValidationResult(False, errors, warnings)

    if not audio_segments:
        errors.append("No audio segments available for timeline validation")
        return ValidationResult(False, errors, warnings)

    if len(timeline_segments) != len(audio_segments):
        errors.append(
            f"Segment count mismatch: timeline={len(timeline_segments)} audio={len(audio_segments)}"
        )

    previous_end = None

    for idx, (timeline_seg, audio_seg) in enumerate(zip(timeline_segments, audio_segments), start=1):
        if timeline_seg.end_time_sec < timeline_seg.start_time_sec:
            errors.append(
                f"Timeline segment {idx}: end time before start time"
            )

        if previous_end is not None and timeline_seg.start_time_sec < previous_end - 1e-3:
            errors.append(
                f"Timeline segment {idx}: overlaps previous segment"
            )

        expected_duration = getattr(audio_seg, "duration_sec", None)
        actual_duration = timeline_seg.end_time_sec - timeline_seg.start_time_sec
        if expected_duration is not None and abs(actual_duration - expected_duration) > duration_tolerance:
            warnings.append(
                f"Timeline segment {idx}: duration mismatch (timeline={actual_duration:.2f}s audio={expected_duration:.2f}s)"
            )

        audio_filename = getattr(audio_seg, "filename", None)
        timeline_filename = getattr(timeline_seg, "audio_filename", None)
        if audio_filename and timeline_filename and audio_filename != timeline_filename:
            warnings.append(
                f"Timeline segment {idx}: filename mismatch ({timeline_filename} vs {audio_filename})"
            )

        previous_end = timeline_seg.end_time_sec

    is_valid = len(errors) == 0
    return ValidationResult(is_valid, errors, warnings)


def text_similarity(text1: str, text2: str) -> float:
    """Calculate text similarity ratio.

    Normalizes text (removes punctuation, lowercases) before comparison.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity ratio (0.0 to 1.0)

    Example:
        >>> text_similarity("Hello, world!", "Hello world")
        1.0
    """
    # Normalize: remove punctuation and whitespace, lowercase
    punct_re = re.compile(r"[、。，．,.！？!？\s\n「」『』（）()【】——…・※★]")

    norm1 = punct_re.sub("", text1).lower()
    norm2 = punct_re.sub("", text2).lower()

    if not norm1 or not norm2:
        return 0.0

    return SequenceMatcher(None, norm1, norm2).ratio()


def validate_pipeline_run(
    project_dir: Path,
    config: Dict
) -> Dict[str, ValidationResult]:
    """Validate complete pipeline run.

    Performs all validation checks:
    - Project structure
    - Input files
    - Output consistency
    - Configuration

    Args:
        project_dir: Path to project directory
        config: Pipeline configuration

    Returns:
        Dictionary of validation results by check name
    """
    results: Dict[str, ValidationResult] = {}

    # Structure check
    results["project_structure"] = validate_project_structure(project_dir)

    # Input file checks
    inputs_dir = project_dir / "inputs"
    srt_files = list(inputs_dir.glob("ep*.srt"))
    if srt_files:
        results["input_srt"] = validate_srt_file(srt_files[0])

    tts_yaml_files = list(inputs_dir.glob("*tts*.yaml"))
    if tts_yaml_files:
        results["tts_config"] = validate_yaml_config(tts_yaml_files[0])

    # Output checks (if output exists)
    output_dir = project_dir / "output"
    if output_dir.exists():
        output_srt_files = list(output_dir.glob("*timecode.srt"))
        if output_srt_files and srt_files:
            validation_cfg = config.get("validation", {}) if isinstance(config, dict) else {}
            results["output_consistency"] = validate_output_consistency(
                srt_files[0],
                output_srt_files[0],
                tolerance=validation_cfg.get("entry_count_tolerance", 0.05),
                similarity_min=validation_cfg.get("text_similarity_min", 0.95),
            )

    return results


def print_validation_report(results: Dict[str, ValidationResult]) -> None:
    """Print comprehensive validation report.

    Args:
        results: Dictionary of validation results
    """
    print("=" * 60)
    print("Orion Pipeline v2 - Validation Report")
    print("=" * 60)
    print()

    all_valid = all(result.is_valid for result in results.values())

    for check_name, result in results.items():
        print(f"[{check_name}]")
        print(result.summary())
        print()

    print("=" * 60)
    if all_valid:
        print("✅ ALL CHECKS PASSED")
    else:
        print("❌ VALIDATION FAILED")
    print("=" * 60)


if __name__ == "__main__":
    # Simple test
    print("Testing validator...")

    # Test text similarity
    assert text_similarity("Hello, world!", "Hello world") > 0.95
    assert text_similarity("専門を深めるべきか", "専門を深めるべきか") == 1.0
    print("✅ Text similarity tests passed")

    # Test SRT validation
    from pathlib import Path
    test_srt = Path("test.srt")
    test_srt.write_text("""1
00:00:00,000 --> 00:00:05,000
Test subtitle

2
00:00:05,000 --> 00:00:10,000
Second test
""", encoding="utf-8")

    result = validate_srt_file(test_srt)
    print(f"\n✅ SRT validation: {result.is_valid}")
    print(result.summary())

    test_srt.unlink()
    print("\n✅ All validator tests passed")
