#!/usr/bin/env python3
"""Wrapper around the shared timeline builder for Resolve prototyping.

Premiere 版 CLI と同じ出力を得られるようにし、Resolve スクリプト開発時の
地盤データとして活用する。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from projects.nle_autoedit.common.timeline_builder import build_timeline  # type: ignore  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python build_timeline_cli.py <csv> <template.yaml>")
        return 1

    csv_path = Path(sys.argv[1]).expanduser()
    tmpl_path = Path(sys.argv[2]).expanduser()
    if not csv_path.exists() or not tmpl_path.exists():
        print("Input files not found")
        return 2

    timeline = build_timeline(csv_path, tmpl_path)

    payload = {
        "fps": timeline.fps,
        "placements": [
            {
                "track": p.track_name,
                "source": p.source_name,
                "start": p.start_frames,
                "end": p.end_frames,
                "source_in": p.source_in,
                "source_out": p.source_out,
                "label": p.label,
                "transcript": p.transcript,
            }
            for p in timeline.placements
        ],
        "gaps": [
            {
                "start": g.start_frames,
                "end": g.end_frames,
                "color": g.color,
                "transcript": g.transcript,
            }
            for g in timeline.gaps
        ],
        "diagnostics": timeline.diagnostics,
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

