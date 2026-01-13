# Media Module Triage (davinciauto)

Goal: keep only modules that are verifiably runnable. Others stay in davinciauto until validated.

## Working candidates (low coupling)
- ops/media/orion/* (pipeline + docs)
  - Requires: Python 3.11+, Gemini API key
  - Entry: ops/media/orion/README.md
- ops/media/premiere/nle_autoedit/*
  - Requires: Python + Premiere-compatible XML workflow
  - Entry: ops/media/premiere/README.md
- AAFexport/Batch_Export_AAF.jsx (still in davinciauto)
  - Requires: Adobe Premiere (ExtendScript)

## Needs validation before extraction
- davinciauto/scripts/*
  - README references missing script (docs drift)
  - Many scripts depend on external APIs or DaVinci Resolve
- davinciauto/projects/* and davinciauto/premiere/projects/*
  - Likely sample data; keep in source repo
- davinciauto/archive/*
  - Legacy; do not extract unless explicitly needed

## Next validation steps
1) Run minimal smoke tests with real inputs (no API calls) for:
   - ops/media/premiere/nle_autoedit/common/timeline_builder.py
   - ops/media/premiere/tools/autocut/csv_xml_cutter.py
2) If OK, extract additional scripts from davinciauto/scripts by explicit list.
