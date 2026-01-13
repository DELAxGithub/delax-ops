# Orion TTS-Only Quick Use

Goal: generate narration audio without running the full pipeline.

## Requirements
- Python 3.11+
- `pip install --user pyyaml python-dotenv`
- Google credentials for TTS (Gemini / Google Cloud)

## Minimal steps
1) Prepare files
- `ops/media/orion/projects/<EP>/inputs/ep<N>nare.md`
- `ops/media/orion/projects/<EP>/inputs/ep<N>nare.yaml`

2) Export env vars (example)
```bash
export GEMINI_API_KEY="..."
```

3) Run
```bash
cd /Users/delaxstudio/src/delax-ops/ops/media/orion
python generate_tts.py --episode 13
```

Outputs land in `projects/<EP>/output/audio/`.
