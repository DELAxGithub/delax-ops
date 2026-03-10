Generate TTS audio from a Case-based YAML file using Gemini TTS.

This skill reads YAML files with the case/quote/dialogue format (e.g. TTS音声割り当て_Case16-30.yaml) and generates MP3 audio via Gemini TTS API.

## Instructions

1. Ask the user which YAML file to use if not obvious from context. Look for files matching `*Case*.yaml` or `*TTS*.yaml` in the `script/` directory.

2. Run `--list` first to show available cases:
```bash
cd /Users/delaxpro/src/delax-ops/ops/media/orion && python generate_case_tts.py --yaml <YAML_PATH> --list
```

3. Ask the user which case(s) to generate, or if they want `--all`.

4. Run a `--dry-run` first to preview:
```bash
python generate_case_tts.py --yaml <YAML_PATH> --case <N> --dry-run
```

5. After user confirms, run the actual generation:
```bash
python generate_case_tts.py --yaml <YAML_PATH> --case <N> --delay 3.0
```

## Voice mapping

| Role | Gemini Voice |
|------|-------------|
| 老年男性A | Charon |
| 老年男性B | Orus |
| 老年男性C | Fenrir |
| 老年男性D | Puck |
| 若手女性 | Aoede |
| 若手女性B | Leda |
| 若手男性 | Kore |
| 中年男性 | Perseus |
| 中年男性B | Zephyr |
| 中年女性 | Coral |

## Requirements

- `GEMINI_API_KEY` in environment or `ops/media/orion/.env`
- `pip install pyyaml python-dotenv google-genai`
- `ffmpeg` installed (for PCM to MP3 conversion)

## Output

Audio files are saved to `<yaml_dir>/tts_output/case<NN>/case<NN>_<SEQ>.mp3` by default. Use `--output <dir>` to override.
