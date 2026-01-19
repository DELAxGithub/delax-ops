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
export GEMINI_API_KEY_1="..."  # optional: rotate keys when quota hits
export GEMINI_API_KEY_2="..."
export GEMINI_API_KEY_3="..."
```

3) Run
```bash
cd /Users/delaxstudio/src/delax-ops/ops/media/orion
python generate_tts.py --episode 13
```

Outputs land in `projects/<EP>/output/audio/`.
