#!/usr/bin/env python3
"""Generic TTS generation script for Orion episodes.

Usage:
    python generate_tts.py --episode 12
    python generate_tts.py --episode 13 --limit 10  # Test first 10 segments
    python generate_tts.py --episode 12 --delay 5.0  # Increase delay between requests
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load .env from repository root (davinciauto/)
REPO_ROOT = Path(__file__).resolve().parent
ENV_FILE = REPO_ROOT.parent / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)  # Override existing env vars

PIPELINE_DIR = REPO_ROOT / "pipeline"
ENGINES_DIR = PIPELINE_DIR / "engines"

# Add pipeline/engines to path
if str(ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINES_DIR))

from tts_config_loader import load_merged_tts_config  # type: ignore  # noqa: E402
from orion_tts_generator import OrionTTSGenerator  # type: ignore  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_md_segments(md_path: Path, limit: int | None = None) -> list[str]:
    """Load plain text lines from MD file.

    Args:
        md_path: Path to MD file (e.g., ep1nare.md)
        limit: Maximum number of lines to load (None = all)

    Returns:
        List of plain text strings (1 line = 1 segment)
    """
    with md_path.open(encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    logger.info("Total lines in MD: %d", len(lines))

    if limit and limit < len(lines):
        logger.info("Loading first %d lines (limit specified)", limit)
        lines = lines[:limit]
    else:
        logger.info("Loading all %d lines", len(lines))

    return lines


def load_yaml_segments(yaml_path: Path, limit: int | None = None) -> list[dict]:
    """Load segments from YAML file (complete with SSML and settings).

    Args:
        yaml_path: Path to YAML file (e.g., ep12nare.yaml)
        limit: Maximum number of segments to load (None = all)

    Returns:
        List of segment dictionaries with speaker, voice, text, style_prompt
    """
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    segments = data.get("gemini_tts", {}).get("segments", [])
    if not segments:
        raise ValueError(f"No segments found in {yaml_path}")

    logger.info("Total segments in YAML: %d", len(segments))

    if limit and limit < len(segments):
        logger.info("Loading first %d segments (limit specified)", limit)
        return segments[:limit]

    logger.info("Loading all %d segments", len(segments))
    return segments


def extract_ssml_tags(yaml_text: str) -> dict[str, str]:
    """Extract SSML tags from YAML text.

    Args:
        yaml_text: Text from YAML containing SSML tags

    Returns:
        Dictionary mapping positions to SSML tags
        Example: {0: '<break time="1500ms"/>', 10: '<sub alias="おりおん">'}
    """
    import re

    # Find <sub> tags
    sub_pattern = r'<sub alias=[\'"]([^\'"]+)[\'"]>([^<]+)</sub>'
    # Find <break> tags
    break_pattern = r'<break time=[\'"]([^\'"]+)[\'"]/>'

    tags = {}
    for match in re.finditer(sub_pattern, yaml_text):
        tags[match.start()] = (match.group(0), match.group(2))  # (full tag, content)

    for match in re.finditer(break_pattern, yaml_text):
        tags[match.start()] = (match.group(0), None)

    return tags


def merge_md_yaml_segments(
    md_lines: list[str],
    yaml_segments: list[dict]
) -> list[dict]:
    """Merge MD text content with YAML formatting instructions.

    Strategy:
    - MD provides the clean text content (like HTML)
    - YAML provides voice settings, SSML tags, style prompts (like CSS)

    Args:
        md_lines: Plain text lines from MD file
        yaml_segments: Complete segments from YAML with SSML and settings

    Returns:
        List of merged segments with MD text + YAML formatting
    """
    if len(md_lines) != len(yaml_segments):
        logger.warning(
            "MD lines (%d) and YAML segments (%d) count mismatch",
            len(md_lines), len(yaml_segments)
        )
        logger.warning("Using YAML segments as-is (no merge)")
        return yaml_segments

    merged = []
    for md_text, yaml_seg in zip(md_lines, yaml_segments):
        # Extract SSML tags from YAML text
        yaml_text = yaml_seg.get("text", "")

        # Use MD text as base, but apply YAML's SSML formatting if present
        # Strategy: If YAML has SSML tags, use YAML text (with tags)
        #           Otherwise, use clean MD text
        has_ssml = "<" in yaml_text and ">" in yaml_text

        final_text = yaml_text if has_ssml else md_text

        merged.append({
            "speaker": yaml_seg.get("speaker", "ナレーター"),
            "voice": yaml_seg.get("voice", "kore"),
            "text": final_text,
            "style_prompt": yaml_seg.get("style_prompt", ""),
            "scene": yaml_seg.get("scene")
        })

    logger.info("✅ Merged %d segments (MD text + YAML formatting)", len(merged))
    return merged


def generate_tts_for_episode(
    episode_num: int,
    limit: int | None = None,
    request_delay: float = 3.0
) -> None:
    """Generate TTS audio for an episode.

    Args:
        episode_num: Episode number (e.g., 12)
        limit: Maximum number of segments to generate (None = all)
        request_delay: Delay in seconds between TTS requests (default: 3.0)
    """
    episode_name = f"OrionEp{episode_num:02d}"

    logger.info("=" * 64)
    logger.info("Orion TTS Generation - %s", episode_name)
    logger.info("=" * 64)

    # Project directory
    project_dir = REPO_ROOT / "projects" / episode_name
    if not project_dir.exists():
        logger.error("Project directory not found: %s", project_dir)
        logger.error("Please create the project directory first with:")
        logger.error("  mkdir -p %s/{inputs,output/audio,exports}", project_dir)
        return

    # Input files
    md_path = project_dir / "inputs" / f"ep{episode_num}nare.md"
    yaml_path = project_dir / "inputs" / f"ep{episode_num}nare.yaml"

    # Load TTS configuration
    try:
        config = load_merged_tts_config(episode_name)
        logger.info("✅ Loaded TTS configuration for %s", episode_name)
    except Exception as exc:
        logger.error("Failed to load TTS config: %s", exc)
        logger.info("Using default configuration")
        config = None

    # Load segments with MD+YAML merge strategy
    segments = None

    # Strategy 1: MD + YAML merge (HTML+CSS approach)
    if md_path.exists() and yaml_path.exists():
        logger.info("📄 Found both MD and YAML files - merging")
        logger.info("   MD (content):  %s", md_path.name)
        logger.info("   YAML (format): %s", yaml_path.name)
        try:
            md_lines = load_md_segments(md_path, limit=limit)
            yaml_segments = load_yaml_segments(yaml_path, limit=limit)
            segments = merge_md_yaml_segments(md_lines, yaml_segments)
        except Exception as exc:
            logger.error("Failed to merge MD+YAML: %s", exc)

    # Strategy 2: MD only (plain text, default settings)
    if segments is None and md_path.exists():
        logger.info("📄 Using MD file only (plain text): %s", md_path.name)
        try:
            md_lines = load_md_segments(md_path, limit=limit)
            segments = []
            for line in md_lines:
                segments.append({
                    "speaker": "ナレーター",
                    "voice": "kore",
                    "text": line,
                    "style_prompt": "Speak with intellectual depth and documentary-style narration, calm and authoritative."
                })
        except Exception as exc:
            logger.error("Failed to load MD segments: %s", exc)

    # Strategy 3: YAML only (complete with SSML)
    if segments is None and yaml_path.exists():
        logger.info("📄 Using YAML file only (complete with SSML): %s", yaml_path.name)
        try:
            segments = load_yaml_segments(yaml_path, limit=limit)
        except Exception as exc:
            logger.error("Failed to load YAML segments: %s", exc)

    if segments is None:
        logger.error("No valid input file found")
        logger.error("Expected: ep{N}nare.md and/or ep{N}nare.yaml")
        return

    # Setup output directory
    output_dir = project_dir / "output" / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("📁 Output directory: %s", output_dir)

    # Initialize TTS generator
    generator = OrionTTSGenerator(config)
    logger.info("⚙️  Request delay: %.1fs between segments", request_delay)

    # Generate audio
    success = 0
    prev_scene: str | None = None

    for idx, segment in enumerate(segments):
        segment_no = idx + 1
        speaker = segment.get("speaker", "ナレーター")
        text = segment.get("text", "")
        voice = segment.get("voice")
        style_prompt = segment.get("style_prompt")
        scene = segment.get("scene")

        # Scene transition marker
        if scene and scene != prev_scene:
            logger.info("")
            logger.info("=" * 64)
            logger.info("SCENE: %s", scene)
            logger.info("=" * 64)
            prev_scene = scene

        # Output filename
        output_file = output_dir / f"{episode_name}_{segment_no:03d}.mp3"

        # Skip if file already exists
        if output_file.exists():
            file_size = output_file.stat().st_size / 1024  # KB
            logger.info("")
            logger.info("[%03d/%03d] ⏭️  Skipping (already exists): %s (%.1f KB)",
                       segment_no, len(segments), output_file.name, file_size)
            success += 1
            continue

        logger.info("")
        logger.info("[%03d/%03d] Generating: %s", segment_no, len(segments), output_file.name)
        logger.info("  Speaker: %s", speaker)
        logger.info("  Voice: %s", voice or "default")
        logger.info("  Text: %s", text[:60] + "..." if len(text) > 60 else text)

        try:
            success_flag = generator.generate(
                text=text,
                character=speaker,
                output_path=output_file,
                segment_no=segment_no,
                scene=scene,
                prev_scene=prev_scene,
                gemini_voice=voice,
                gemini_style_prompt=style_prompt
            )

            if success_flag and output_file.exists():
                file_size = output_file.stat().st_size / 1024  # KB
                logger.info("  ✅ Generated: %s (%.1f KB)", output_file.name, file_size)
                success += 1

                # Delay between requests
                if segment_no < len(segments):
                    import time
                    time.sleep(request_delay)
            else:
                logger.warning("  ❌ Failed to generate audio")

        except Exception as exc:
            logger.error("  ❌ Error generating audio: %s", exc)
            continue

    logger.info("")
    logger.info("=" * 64)
    logger.info("✅ Generation complete: %d/%d segments successful", success, len(segments))
    logger.info("=" * 64)
    logger.info("📁 Audio files saved to: %s", output_dir)


def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio for Orion episodes")
    parser.add_argument(
        "--episode",
        type=int,
        required=True,
        help="Episode number (e.g., 12 for OrionEp12)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of segments to generate (for testing)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Delay in seconds between TTS requests (default: 3.0)"
    )

    args = parser.parse_args()

    generate_tts_for_episode(
        episode_num=args.episode,
        limit=args.limit,
        request_delay=args.delay
    )


if __name__ == "__main__":
    main()
