# Orion One-Shot Pipeline

Run the full pipeline end-to-end for a project in one command.

## Usage
```bash
cd /Users/delaxstudio/src/delax-ops/ops/media/orion
./run_pipeline.sh OrionEp13
```

## Validate only
```bash
./run_pipeline.sh OrionEp13 --validate-only
```

## Requirements
- Python 3.11+
- Inputs in `projects/<Project>/inputs/`
  - ep*.srt (required)
  - ep*nare.md (recommended)
  - ep*nare.yaml (optional)

## Notes
- TTS keys are required only when generating audio.
- Use `TTS_ONLY.md` if you only need audio generation.
