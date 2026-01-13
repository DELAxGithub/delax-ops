# Orion Modules (proposed split)

Goal: reduce coupling by separating core processing, TTS adapters, and pipeline orchestration.

## Current layout (now)
- core/: parsers + writers + validator + timeline + mapper (no external API calls)
- tts/: TTS engines and config loaders (external API boundary)
- pipeline/: orchestration + preprocess
- config/: global config and prompts
- generate_tts.py: convenience entrypoint

## Target split (phase 1)
- core/
  - parsers/ (SRT, markdown, script markers)
  - writers/ (SRT, CSV, XML)
  - validator.py
  - timeline.py
  - mapper.py
- tts/
  - tts_config_loader.py
  - orion_tts_generator.py
  - orion_ssml_builder.py
  - tts.py (engine + providers)
- pipeline/
  - core.py (CLI + orchestration)
  - preprocess/
  - (no engines inside)

## Migration rules
- core must stay API-only (no network calls)
- tts is the only layer that touches external APIs
- pipeline orchestrates and wires the modules together

## Next steps
1) Move parsers/writers/validator into core/
2) Move TTS-related engines into tts/
3) Move timeline/mapper into core/
4) Update imports and run validate-only smoke test
