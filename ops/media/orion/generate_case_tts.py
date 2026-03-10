#!/usr/bin/env python3
"""TTS generation from Case-based YAML (e.g. TTS音声割り当て_Case16-30.yaml).

Reads the case/quote/dialogue YAML format and generates audio using Gemini TTS.

Usage:
    python generate_case_tts.py --yaml path/to/yaml --case 16
    python generate_case_tts.py --yaml path/to/yaml --all
    python generate_case_tts.py --yaml path/to/yaml --case 16 --dry-run
    python generate_case_tts.py --yaml path/to/yaml --list
"""
from __future__ import annotations

import argparse
import base64
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_FILE = SCRIPT_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Voice mapping: Japanese role name -> Gemini TTS voice ID
# ---------------------------------------------------------------------------
VOICE_MAP: dict[str, str] = {
    "老年男性A": "Charon",
    "老年男性B": "Orus",
    "老年男性C": "Fenrir",
    "老年男性D": "Puck",
    "若手女性":  "Aoede",
    "若手女性B": "Leda",
    "若手男性":  "Kore",
    "中年男性":  "Perseus",
    "中年男性B": "Zephyr",
    "中年女性":  "Coral",
}

DEFAULT_VOICE = "Kore"
TTS_MODEL = "gemini-2.5-flash-preview-tts"


def load_case_yaml(yaml_path: Path) -> dict:
    with yaml_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_cases(data: dict) -> list[tuple[int, str]]:
    """Return sorted list of (case_number, key_name) from YAML data."""
    cases = []
    for key in data:
        m = re.match(r"case(\d+)_(.+)", key)
        if m:
            cases.append((int(m.group(1)), key))
    return sorted(cases)


def extract_segments(data: dict, case_key: str) -> list[dict]:
    """Extract flat list of TTS segments from a case entry."""
    case_data = data[case_key]
    segments = []

    for entry in case_data.get("引用", []) or []:
        segments.append({
            "text": entry["text"],
            "voice": entry.get("voice", "老年男性A"),
            "category": "引用",
            "source": entry.get("source", ""),
            "note": entry.get("note", ""),
        })

    for entry in case_data.get("セリフ", []) or []:
        segments.append({
            "text": entry["text"],
            "voice": entry.get("voice", "若手女性"),
            "category": "セリフ",
            "role": entry.get("role", ""),
            "note": entry.get("note", ""),
        })

    return segments


def resolve_voice(role_name: str) -> str:
    return VOICE_MAP.get(role_name, DEFAULT_VOICE)


def _gather_api_keys() -> list[str]:
    keys: list[str] = []
    primary = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if primary and primary not in keys:
        keys.append(primary)
    for idx in range(1, 10):
        k = os.getenv(f"GEMINI_API_KEY_{idx}")
        if k and k not in keys:
            keys.append(k)
    return keys


def generate_audio(
    text: str,
    voice: str,
    output_path: Path,
    *,
    client,
    max_attempts: int = 5,
) -> bool:
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=TTS_MODEL,
                contents=text,
                config={
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {"voice_name": voice}
                        }
                    },
                },
            )
        except Exception as exc:
            msg = str(exc)
            if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                delay = min(5.0 * attempt, 15.0)
                logger.warning("Rate limit hit, retrying in %.1fs (%d/%d)", delay, attempt, max_attempts)
                time.sleep(delay)
                continue
            logger.error("TTS request failed: %s", exc)
            return False

        if not response or not response.candidates:
            if attempt < max_attempts:
                time.sleep(2.0)
                continue
            return False

        parts = (
            response.candidates[0].content.parts
            if response.candidates[0].content
            else []
        )
        if not parts:
            if attempt < max_attempts:
                time.sleep(2.0)
                continue
            return False

        inline_data = getattr(parts[0], "inline_data", None)
        raw_data = getattr(inline_data, "data", b"") if inline_data else b""
        pcm_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data

        if not pcm_bytes:
            logger.warning("Empty audio payload")
            return False

        _save_pcm_as_mp3(pcm_bytes, output_path)
        return True

    return False


def _save_pcm_as_mp3(pcm_data: bytes, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "s16le", "-ar", "24000", "-ac", "1",
        "-i", "-",
        "-filter:a", "atempo=0.9",
        str(output_path),
    ]
    proc = subprocess.run(cmd, input=pcm_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore"))


def process_case(
    data: dict,
    case_num: int,
    case_key: str,
    output_dir: Path,
    *,
    client,
    dry_run: bool = False,
    delay: float = 3.0,
) -> tuple[int, int]:
    segments = extract_segments(data, case_key)
    if not segments:
        logger.warning("No segments found for %s", case_key)
        return 0, 0

    case_dir = output_dir / f"case{case_num:02d}"
    case_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 64)
    logger.info("Case %d: %s (%d segments)", case_num, case_key, len(segments))
    logger.info("=" * 64)

    success = 0
    for idx, seg in enumerate(segments):
        seg_no = idx + 1
        voice_role = seg["voice"]
        voice_id = resolve_voice(voice_role)
        text = seg["text"]
        category = seg["category"]
        label = seg.get("source") or seg.get("role") or ""

        output_file = case_dir / f"case{case_num:02d}_{seg_no:03d}.mp3"

        logger.info("")
        logger.info("[%03d/%03d] %s | %s -> %s", seg_no, len(segments), category, voice_role, voice_id)
        logger.info("  %s", label)
        logger.info("  \"%s\"", text[:80] + "..." if len(text) > 80 else text)

        if dry_run:
            logger.info("  [DRY RUN] Would generate: %s", output_file.name)
            success += 1
            continue

        if output_file.exists():
            size_kb = output_file.stat().st_size / 1024
            logger.info("  Skipping (exists): %s (%.1f KB)", output_file.name, size_kb)
            success += 1
            continue

        ok = generate_audio(text, voice_id, output_file, client=client)
        if ok and output_file.exists():
            size_kb = output_file.stat().st_size / 1024
            logger.info("  Generated: %s (%.1f KB)", output_file.name, size_kb)
            success += 1
            if seg_no < len(segments):
                time.sleep(delay)
        else:
            logger.warning("  Failed to generate audio")

    return success, len(segments)


def main():
    parser = argparse.ArgumentParser(description="Generate TTS from Case-based YAML")
    parser.add_argument("--yaml", required=True, help="Path to case YAML file")
    parser.add_argument("--case", type=int, help="Case number to generate (e.g. 16)")
    parser.add_argument("--all", action="store_true", help="Generate all cases")
    parser.add_argument("--list", action="store_true", help="List available cases and exit")
    parser.add_argument("--output", default=None, help="Output directory (default: next to YAML)")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between requests (sec)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    args = parser.parse_args()

    yaml_path = Path(args.yaml).resolve()
    if not yaml_path.exists():
        logger.error("YAML file not found: %s", yaml_path)
        sys.exit(1)

    data = load_case_yaml(yaml_path)
    cases = list_cases(data)

    if not cases:
        logger.error("No case entries found in %s", yaml_path.name)
        sys.exit(1)

    if args.list:
        print(f"\nCases in {yaml_path.name}:")
        print("-" * 50)
        for num, key in cases:
            segs = extract_segments(data, key)
            quotes = sum(1 for s in segs if s["category"] == "引用")
            lines = sum(1 for s in segs if s["category"] == "セリフ")
            print(f"  Case {num:2d}: {key}  ({quotes} quotes, {lines} lines)")
        print(f"\nTotal: {len(cases)} cases")
        return

    if not args.case and not args.all:
        parser.error("Specify --case N or --all (use --list to see available cases)")

    output_dir = Path(args.output) if args.output else yaml_path.parent / "tts_output"

    # Init Gemini client
    client = None
    if not args.dry_run:
        api_keys = _gather_api_keys()
        if not api_keys:
            logger.error("GEMINI_API_KEY not set. Set it in .env or environment.")
            sys.exit(1)

        try:
            from google import genai
        except ImportError:
            logger.error("google-genai package required. Install: pip install google-genai")
            sys.exit(1)

        client = genai.Client(api_key=api_keys[0])
        logger.info("Gemini API configured (%d key(s))", len(api_keys))

    # Filter cases
    if args.all:
        targets = cases
    else:
        targets = [(n, k) for n, k in cases if n == args.case]
        if not targets:
            logger.error("Case %d not found. Use --list to see available cases.", args.case)
            sys.exit(1)

    total_success = 0
    total_segments = 0

    for case_num, case_key in targets:
        s, t = process_case(
            data, case_num, case_key, output_dir,
            client=client, dry_run=args.dry_run, delay=args.delay,
        )
        total_success += s
        total_segments += t

    logger.info("")
    logger.info("=" * 64)
    logger.info("Complete: %d/%d segments", total_success, total_segments)
    logger.info("Output: %s", output_dir)
    logger.info("=" * 64)


if __name__ == "__main__":
    main()
