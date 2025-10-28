#!/usr/bin/env python3
"""Orion Production Pipeline v2 - Core orchestrator.

Main entry point for the production pipeline.
Coordinates input parsing, TTS generation, timeline calculation, and output writing.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# Add parent directory to path for imports
# __file__ = orion/pipeline/core.py
# parent = orion/pipeline/
# parent.parent = orion/
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from parsers.srt import (
    Subtitle,
    parse_srt_file,
    write_srt
)
from parsers.markdown import parse_narration_file, parse_narration_yaml, parse_script_section_markers, validate_audio_files
from engines.tts import TTSEngine, AudioSegment
from engines.timeline import TimelineCalculator, TimelineSegment, detect_scene_markers
from engines.mapper import find_audio_subtitle_mapping, SubtitleMapping
from pipeline.preprocess.generator import generate_inputs_from_script
from writers.srt import write_timecode_srt, write_merged_srt
from writers.csv import write_timeline_csv
from writers.xml import write_fcp7_xml
from validator import (
    validate_pipeline_run,
    print_validation_report,
    validate_output_consistency,
    validate_timeline_alignment
)


@dataclass
class PipelineConfig:
    """Pipeline configuration loaded from YAML."""

    # Text processing
    preserve_spaces: bool = True
    auto_finalize: bool = False
    ssml_to_punctuation: bool = True

    # Timeline
    timebase: int = 30
    ntsc: bool = True
    scene_lead_in_sec: float = 3.0

    # Validation
    entry_count_tolerance: float = 0.05
    text_similarity_min: float = 0.95
    fail_fast: bool = True

    # TTS
    tts_engine: str = "gemini"
    tts_request_delay: float = 5.0

    # Debug
    debug_enabled: bool = False
    output_intermediate: bool = False

    @classmethod
    def from_yaml(cls, path: Path) -> PipelineConfig:
        """Load configuration from YAML file."""
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls(
            preserve_spaces=data.get("text_processing", {}).get("preserve_spaces", True),
            auto_finalize=data.get("text_processing", {}).get("auto_finalize", False),
            ssml_to_punctuation=data.get("text_processing", {}).get("ssml_to_punctuation", True),
            timebase=data.get("timeline", {}).get("timebase", 30),
            ntsc=data.get("timeline", {}).get("ntsc", True),
            scene_lead_in_sec=data.get("timeline", {}).get("scene_lead_in_sec", 3.0),
            entry_count_tolerance=data.get("validation", {}).get("entry_count_tolerance", 0.05),
            text_similarity_min=data.get("validation", {}).get("text_similarity_min", 0.95),
            fail_fast=data.get("validation", {}).get("fail_fast", True),
            tts_engine=data.get("tts", {}).get("default_engine", "gemini"),
            tts_request_delay=data.get("tts", {}).get("request_delay_sec", 5.0),
            debug_enabled=data.get("debug", {}).get("enabled", False),
            output_intermediate=data.get("debug", {}).get("output_intermediate", False),
        )


@dataclass
class PipelineContext:
    """Runtime context for pipeline execution."""

    project: str
    project_dir: Path
    inputs_dir: Path
    output_dir: Path
    exports_dir: Path
    generated_dir: Path

    # Input files
    source_srt: Optional[Path] = None
    narration_md: Optional[Path] = None
    narration_yaml: Optional[Path] = None
    script_csv: Optional[Path] = None
    tts_config: Optional[Path] = None
    script_md: Optional[Path] = None

    # Output files
    output_srt: Optional[Path] = None
    timeline_csv: Optional[Path] = None
    timeline_xml: Optional[Path] = None
    merged_srt: Optional[Path] = None
    audio_dir: Optional[Path] = None

    # Configuration
    config: PipelineConfig = field(default_factory=PipelineConfig)

    # Runtime data
    fps: float = field(init=False)

    def __post_init__(self) -> None:
        """Calculate derived fields."""
        self.fps = (
            self.config.timebase * 1000 / 1001
            if self.config.ntsc
            else float(self.config.timebase)
        )

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> PipelineContext:
        """Create context from CLI arguments."""
        # REPO_ROOT is now orion/ directory
        project_dir = REPO_ROOT / "projects" / args.project

        inputs_dir = project_dir / "inputs"
        output_dir = project_dir / "output"
        exports_dir = project_dir / "exports"
        generated_dir = project_dir / "generated"

        # Load configuration
        config_path = REPO_ROOT / "config" / "global.yaml"
        config = PipelineConfig.from_yaml(config_path)

        # Discover input files
        source_srt = cls._find_file(inputs_dir, "ep*.srt")
        narration_md = cls._find_file(inputs_dir, "*nare*.md", "*ep*.md")
        narration_yaml = cls._find_file(inputs_dir, "*nareyaml*.yaml", "*nare*.yaml")
        script_csv = cls._find_file(inputs_dir, "*script.csv")
        tts_config = cls._find_file(inputs_dir, "*tts*.yaml")

        episode_suffix = cls._extract_episode_suffix(args.project)
        script_patterns: List[str] = []
        if episode_suffix:
            script_patterns.extend([
                f"orinonep{episode_suffix}.md",
                f"OrionEp{episode_suffix}.md",
                f"Ep{episode_suffix}.md",
                f"ep{episode_suffix}.md",
            ])
        script_patterns.extend([
            "*script*.md",
            "*_script.md",
        ])
        script_md = cls._find_file(inputs_dir, *script_patterns)

        # Define output files
        snake_name = args.project.lower()
        output_srt = output_dir / f"{args.project}_timecode.srt"
        timeline_csv = output_dir / f"{args.project}_timeline.csv"
        timeline_xml = output_dir / f"{args.project}_timeline.xml"
        merged_srt = exports_dir / f"{snake_name}_merged.srt"
        audio_dir = output_dir / "audio"

        return cls(
            project=args.project,
            project_dir=project_dir,
            inputs_dir=inputs_dir,
            output_dir=output_dir,
            exports_dir=exports_dir,
            generated_dir=generated_dir,
            source_srt=source_srt,
            narration_md=narration_md,
            narration_yaml=narration_yaml,
            script_csv=script_csv,
            tts_config=tts_config,
            script_md=script_md,
            output_srt=output_srt,
            timeline_csv=timeline_csv,
            timeline_xml=timeline_xml,
            merged_srt=merged_srt,
            audio_dir=audio_dir,
            config=config,
        )

    @staticmethod
    def _find_file(directory: Path, *patterns: str) -> Optional[Path]:
        """Find first file matching any of the patterns."""
        for pattern in patterns:
            matches = list(directory.glob(pattern))
            if matches:
                return matches[0]
        return None

    @staticmethod
    def _extract_episode_suffix(project_name: str) -> str:
        digits = "".join(ch for ch in project_name if ch.isdigit())
        return digits

    def print_summary(self) -> None:
        """Print pipeline context summary."""
        print("=" * 60)
        print(f"Orion Pipeline v2 - {self.project}")
        print("=" * 60)
        print()
        print("[Input Files]")
        print(f"  source_srt:     {self._format_path(self.source_srt)}")
        print(f"  narration_md:   {self._format_path(self.narration_md)}")
        print(f"  narration_yaml: {self._format_path(self.narration_yaml)}")
        print(f"  script_md:      {self._format_path(self.script_md)}")
        print(f"  script_csv:     {self._format_path(self.script_csv)}")
        print(f"  tts_config:     {self._format_path(self.tts_config)}")
        print()
        print("[Output Files]")
        print(f"  output_srt:     {self._format_path(self.output_srt)}")
        print(f"  timeline_csv:   {self._format_path(self.timeline_csv)}")
        print(f"  timeline_xml:   {self._format_path(self.timeline_xml)}")
        print(f"  merged_srt:     {self._format_path(self.merged_srt)}")
        print(f"  audio_dir:      {self._format_path(self.audio_dir)}")
        print(f"  generated_dir:  {self.generated_dir}")
        print()
        print("[Configuration]")
        print(f"  preserve_spaces: {self.config.preserve_spaces}")
        print(f"  auto_finalize:   {self.config.auto_finalize}")
        print(f"  timebase:        {self.config.timebase} {'(NTSC)' if self.config.ntsc else ''}")
        print(f"  fps:             {self.fps:.3f}")
        print("=" * 60)
        print()

    def _format_path(self, path: Optional[Path]) -> str:
        """Format path for display."""
        if path is None:
            return "❌ Not found"
        elif path.exists():
            return f"✅ {path.name}"
        else:
            return f"⏳ {path.name}"


def run_pipeline(ctx: PipelineContext) -> bool:
    """Execute the complete pipeline.

    Args:
        ctx: Pipeline context

    Returns:
        True if successful, False otherwise
    """
    ctx.print_summary()
    overall_success = True

    # Phase 1: Validation
    print("[Phase 1] Input Validation")
    print("-" * 60)

    validation_results = validate_pipeline_run(
        ctx.project_dir,
        {"validation": {"entry_count_tolerance": ctx.config.entry_count_tolerance}}
    )

    # Check critical validations
    if "input_srt" in validation_results and not validation_results["input_srt"]:
        print("❌ Input SRT validation failed")
        print(validation_results["input_srt"].summary())
        if ctx.config.fail_fast:
            return False

    print("✅ Input validation passed")
    print()

    # Phase 2: Parse source SRT (Single Source of Truth)
    print("[Phase 2] Parse Source SRT")
    print("-" * 60)

    if ctx.source_srt is None or not ctx.source_srt.exists():
        print(f"❌ Source SRT not found: {ctx.source_srt}")
        return False

    try:
        source_subtitles = parse_srt_file(ctx.source_srt)
        print(f"✅ Parsed {len(source_subtitles)} subtitle entries from {ctx.source_srt.name}")
    except ValueError as e:
        print(f"❌ Failed to parse source SRT: {e}")
        return False

    print()

    # Phase 3: TTS Generation
    print("[Phase 3] TTS Generation")
    print("-" * 60)

    # Parse narration markdown
    narration_segments = []
    narration_reference_path: Optional[Path] = None
    narration_reference_segments: Optional[List] = None
    narration_source_kind: Optional[str] = None

    narration_sources = [
        ("yaml", ctx.narration_yaml),
        ("markdown", ctx.narration_md),
    ]

    for source_kind, source_path in narration_sources:
        if not source_path or not source_path.exists():
            continue

        try:
            if source_kind == "yaml":
                narration_segments = parse_narration_yaml(source_path)
            else:
                narration_segments = parse_narration_file(source_path)
            narration_reference_path = source_path if source_kind == "markdown" else None
            narration_reference_segments = narration_segments if source_kind == "yaml" else None
            narration_source_kind = source_kind
            print(f"✅ Parsed {len(narration_segments)} narration segments from {source_path.name}")
            break
        except (ValueError, FileNotFoundError) as exc:
            print(f"❌ Failed to parse {source_kind} narration ({source_path}): {exc}")
            narration_segments = []

    if not narration_segments:
        print("❌ No valid narration source found (.md or *nareyaml*.yaml)")
        if ctx.config.fail_fast:
            return False
        overall_success = False
        audio_segments = []
        narration_segments = []
    else:
        # Initialize TTS engine with existing audio reuse mode
        if ctx.audio_dir.exists() and any(ctx.audio_dir.glob("*.mp3")):
            print(f"  → Using existing audio from: {ctx.audio_dir}")
            tts_engine = TTSEngine(
                use_existing=True,
                existing_audio_dir=ctx.audio_dir,
                request_delay_sec=ctx.config.tts_request_delay
            )
        else:
            print(f"  → No existing audio found, will generate new TTS")
            print(f"  → Request delay: {ctx.config.tts_request_delay}s (quota protection)")
            tts_engine = TTSEngine(
                use_existing=False,
                request_delay_sec=ctx.config.tts_request_delay
            )

        ctx.audio_dir.mkdir(parents=True, exist_ok=True)

        audio_segments = tts_engine.generate_segments(
            narration_segments,
            ctx.audio_dir,
            ctx.project
        )
        print(f"✅ Processed {len(audio_segments)} audio segments")

        total_duration = sum(seg.duration_sec for seg in audio_segments)
        print(f"  → Total audio duration: {total_duration:.2f}s ({total_duration/60:.1f}min)")

    nare_matching_path = narration_reference_path if narration_source_kind == "markdown" else None
    nare_matching_segments = (
        narration_reference_segments if narration_reference_segments is not None else narration_segments
    )

    print()

    # Phase 4: Timeline Calculation (Audio-based with gaps)
    print("[Phase 4] Timeline Calculation")
    print("-" * 60)

    if not audio_segments:
        print("⚠️  No audio segments available, skipping timeline calculation")
        overall_success = False
        timeline_segments = []
    else:
        print(f"  → Building timeline for {len(audio_segments)} audio segments")

        # Detect scene markers from original script (orinonep{N}.md)
        # Check if original script file exists alongside narration markdown
        if ctx.narration_md:
            original_script_path = ctx.narration_md.parent / f"orinonep{ctx.project[-2:]}.md"
            if original_script_path.exists():
                scene_markers = parse_script_section_markers(original_script_path)
                # Convert to 0-based indices for internal use
                scene_markers = [idx - 1 for idx in scene_markers if idx > 1]  # Skip first section (no lead-in needed)
                print(f"  → Detected {len(scene_markers)} section markers from {original_script_path.name}")
                print(f"  → Scene lead-in: {ctx.config.scene_lead_in_sec:.1f}s at sections")
            else:
                scene_markers = []
                print(f"  → No section markers (original script not found)")
        else:
            scene_markers = []

        # Initialize timeline calculator
        calculator = TimelineCalculator(
            fps=ctx.fps,
            scene_lead_in_sec=ctx.config.scene_lead_in_sec
        )

        # Calculate audio-based timeline with dynamic gaps
        timeline_segments = calculator.calculate_timeline(
            audio_segments,
            narration_segments=narration_segments,
            scene_markers=scene_markers,
            scene_end_indices=[]  # TODO: detect from content
        )

        print(f"✅ Calculated timeline for {len(timeline_segments)} audio segments")
        print(calculator.format_timeline_summary(timeline_segments))

    print()

    # Phase 5: Output Writing
    print("[Phase 5] Output Writing")
    print("-" * 60)

    if not timeline_segments:
        print("⚠️  No timeline segments available, skipping output writing")
        overall_success = False
    else:
        # Ensure output directories exist
        ctx.output_dir.mkdir(parents=True, exist_ok=True)
        ctx.exports_dir.mkdir(parents=True, exist_ok=True)

        output_success = True

        # 1. Write timecode SRT (output/)
        # Apply timeline timecodes to existing SRT (preserves LLM-generated text)
        # Uses Nare script for text matching to ensure correct alignment
        print(f"  → Writing timecode SRT: {ctx.output_srt.name}")
        if write_timecode_srt(
            ctx.output_srt,
            source_subtitles,
            timeline_segments,
            nare_script_path=nare_matching_path,
            nare_segments=nare_matching_segments
        ):
            print(f"    ✅ {ctx.output_srt}")
        else:
            print(f"    ❌ Failed to write timecode SRT")
            output_success = False

        # 2. Write timeline CSV (output/)
        print(f"  → Writing timeline CSV: {ctx.timeline_csv.name}")
        if write_timeline_csv(ctx.timeline_csv, timeline_segments, ctx.fps):
            print(f"    ✅ {ctx.timeline_csv}")
        else:
            print(f"    ❌ Failed to write timeline CSV")
            output_success = False

        # 3. Write FCP7 XML (output/)
        print(f"  → Writing FCP7 XML: {ctx.timeline_xml.name}")
        if write_fcp7_xml(
            ctx.timeline_xml,
            timeline_segments,
            audio_segments,
            ctx.project,
            ctx.fps,
            audio_sample_rate=24000,
            timebase=ctx.config.timebase,
            audio_dir=ctx.audio_dir
        ):
            print(f"    ✅ {ctx.timeline_xml}")
        else:
            print(f"    ❌ Failed to write FCP7 XML")
            output_success = False

        # 4. Write merged SRT (exports/)
        print(f"  → Writing merged SRT: {ctx.merged_srt.name}")
        if write_merged_srt(
            ctx.merged_srt,
            source_subtitles,
            timeline_segments,
            nare_script_path=nare_matching_path,
            nare_segments=nare_matching_segments
        ):
            print(f"    ✅ {ctx.merged_srt}")
        else:
            print(f"    ❌ Failed to write merged SRT")
            output_success = False

        if output_success:
            print("\n✅ All output files written successfully")
        else:
            print("\n⚠️  Some output files failed to write")
            overall_success = False
            if ctx.config.fail_fast:
                return False

    print()

    # Phase 6: Validation
    print("[Phase 6] Output Validation")
    print("-" * 60)

    phase6_success = True

    if ctx.output_srt and ctx.output_srt.exists() and ctx.source_srt:
        srt_result = validate_output_consistency(
            ctx.source_srt,
            ctx.output_srt,
            tolerance=ctx.config.entry_count_tolerance,
            similarity_min=ctx.config.text_similarity_min,
        )
        print(srt_result.summary())
        print()
        phase6_success &= srt_result.is_valid
    else:
        print(f"❌ Output SRT not found: {ctx.output_srt}")
        print()
        phase6_success = False

    if narration_segments:
        audio_ok, missing_audio = validate_audio_files(narration_segments, ctx.audio_dir, ctx.project)
        if audio_ok:
            print("✅ All narration segments have corresponding audio files")
        else:
            phase6_success = False
            print("❌ Missing audio files:")
            for filename in missing_audio:
                print(f"    - {filename}")
        print()
    else:
        print("⚠️  Skipping audio coverage check (no narration segments)")
        print()

    if timeline_segments and audio_segments:
        timeline_result = validate_timeline_alignment(timeline_segments, audio_segments)
        print(timeline_result.summary())
        print()
        phase6_success &= timeline_result.is_valid
    else:
        print("⚠️  Skipping timeline alignment check (insufficient data)")
        print()
        if not timeline_segments or not audio_segments:
            phase6_success = False

    required_outputs = {
        "Timeline CSV": ctx.timeline_csv,
        "Timeline XML": ctx.timeline_xml,
        "Merged SRT": ctx.merged_srt,
    }

    for label, path_obj in required_outputs.items():
        if path_obj and path_obj.exists():
            print(f"✅ {label}: {path_obj.name}")
        else:
            phase6_success = False
            print(f"❌ {label} missing: {path_obj}")

    print()

    overall_success &= phase6_success

    print("=" * 60)
    if overall_success:
        print("✅ Pipeline execution completed")
    else:
        print("❌ Pipeline execution completed with validation issues")
    print("=" * 60)

    return overall_success


def _check_phase0_completion(ctx: PipelineContext) -> bool:
    """Check if Phase 0 (input generation) has been completed.

    Args:
        ctx: Pipeline context

    Returns:
        True if Phase 0 is complete or not required, False if required but incomplete
    """
    # If script.md doesn't exist, Phase 0 is not required
    if ctx.script_md is None or not ctx.script_md.exists():
        return True

    # Check if generated/status.json exists and inputs have been applied
    status_file = ctx.generated_dir / "status.json"
    if status_file.exists():
        try:
            import json
            with status_file.open(encoding="utf-8") as f:
                status = json.load(f)
                if status.get("applied_inputs", False):
                    return True
        except (json.JSONDecodeError, OSError):
            pass

    # Check if required input files exist
    # If all inputs exist, assume Phase 0 was completed manually
    required_inputs = [
        ctx.source_srt,
        ctx.narration_yaml,
    ]

    if all(inp and inp.exists() for inp in required_inputs):
        return True

    # Phase 0 required but not completed
    return False


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Orion Production Pipeline v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 pipeline/core.py --project OrionEp11
  python3 pipeline/core.py --project OrionEp11 --validate-only
        """
    )

    parser.add_argument(
        "--project",
        required=True,
        help="Project name (e.g., OrionEp11)"
    )

    parser.add_argument(
        "--generate-inputs",
        action="store_true",
        help="Run preprocessing phase only (generate prompts/drafts from script)"
    )

    parser.add_argument(
        "--prompt-profile",
        help="Prompt profile name to use for preprocessing"
    )

    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Overwrite existing generated artifacts during preprocessing"
    )

    parser.add_argument(
        "--apply-generated-inputs",
        action="store_true",
        help="After preprocessing, copy reviewed generated inputs into the inputs directory"
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run validation, skip pipeline execution"
    )

    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed validation report"
    )

    args = parser.parse_args(argv)

    try:
        # Create pipeline context
        ctx = PipelineContext.from_args(args)

        # Preprocessing only mode
        if args.generate_inputs:
            generated = generate_inputs_from_script(
                ctx,
                prompt_profile=args.prompt_profile,
                force=args.force_regenerate,
                apply=bool(args.apply_generated_inputs)
            )
            return 0 if generated else 1

        # Validate only mode
        if args.validate_only or args.report:
            results = validate_pipeline_run(
                ctx.project_dir,
                {"validation": {"entry_count_tolerance": ctx.config.entry_count_tolerance}}
            )
            print_validation_report(results)
            return 0 if all(r.is_valid for r in results.values()) else 1

        # Check if Phase 0 is required
        if not _check_phase0_completion(ctx):
            print()
            print("=" * 60)
            print("⚠️  Phase 0 (Input Generation) Required")
            print("=" * 60)
            print()
            print("This project requires prompt-based input generation.")
            print()
            print("Required steps:")
            print("  1. Generate prompts:")
            print(f"     python orion/pipeline/core.py --project {ctx.project} --generate-inputs")
            print()
            print("  2. Review and execute prompts in generated/prompts/:")
            print(f"     - srt_prompt.md  → Create teleop_raw.srt")
            print(f"     - nare_prompt.md → Create nare.md")
            print(f"     - yaml_prompt.md → Create nare.yaml")
            print()
            print("  3. Place generated files in generated/ directory")
            print()
            print("  4. Apply generated inputs:")
            print(f"     python orion/pipeline/core.py --project {ctx.project} --apply-generated-inputs")
            print()
            print("  5. Run pipeline again")
            print()
            return 1

        # Run pipeline
        success = run_pipeline(ctx)
        return 0 if success else 1

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        if ctx.config.debug_enabled:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
