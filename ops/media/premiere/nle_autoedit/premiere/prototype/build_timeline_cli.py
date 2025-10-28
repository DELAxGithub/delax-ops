#!/usr/bin/env python3
"""Simple CLI to generate timeline placement summary from CSV + template.

Usage:
    python build_timeline_cli.py path/to/case.csv path/to/template.yaml

This tool relies on the shared timeline builder so that Premiere / Resolve
front-ends can compare results during development. It does not emit XML; the
output is a human readable summary + diagnostics JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.nle_autoedit.common.timeline_builder import build_timeline  # type: ignore  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1

    csv_path = Path(sys.argv[1]).expanduser()
    tmpl_path = Path(sys.argv[2]).expanduser()

    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 2
    if not tmpl_path.exists():
        print(f"Template not found: {tmpl_path}")
        return 3

    timeline = build_timeline(csv_path, tmpl_path)

    print(f"FPS: {timeline.fps}")
    print(f"Total placements: {len(timeline.placements)}")
    print(f"Captured gaps: {len(timeline.gaps)}\n")

    for placement in timeline.placements:
        print(
            f"[{placement.track_name}] {placement.source_name}"
            f"  timeline {placement.start_frames}->{placement.end_frames}"
            f"  source {placement.source_in}->{placement.source_out}"
            f"  label={placement.label}"
        )

    print("\nDiagnostics:")
    print(json.dumps(timeline.diagnostics, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

