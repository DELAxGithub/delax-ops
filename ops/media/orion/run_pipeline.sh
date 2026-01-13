#!/bin/zsh
set -euo pipefail

ORION_ROOT="$(cd "$(dirname "$0")" && pwd)"
PROJECT="${1:-}"
shift || true

if [ -z "$PROJECT" ]; then
  echo "Usage: ./run_pipeline.sh <ProjectName> [--validate-only|--report]"
  exit 1
fi

PROJECT_DIR="$ORION_ROOT/projects/$PROJECT"
INPUTS_DIR="$PROJECT_DIR/inputs"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "Project not found: $PROJECT_DIR"
  exit 1
fi

if [ ! -d "$INPUTS_DIR" ]; then
  echo "Inputs directory not found: $INPUTS_DIR"
  exit 1
fi

# Basic input checks
if ! ls "$INPUTS_DIR"/ep*.srt >/dev/null 2>&1; then
  echo "Missing ep*.srt in $INPUTS_DIR"
  exit 1
fi

# Run pipeline
cd "$ORION_ROOT"
python3 pipeline/core.py --project "$PROJECT" "$@"
