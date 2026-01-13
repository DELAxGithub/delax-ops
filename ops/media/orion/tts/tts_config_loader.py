"""Utility functions for loading shared TTS configuration."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List
import os
import sys

import yaml


DEFAULT_STYLE_PROMPTS = {
    "openai": (
        "Please read the following text slowly and warmly, with clear articulation "
        "suitable for shared educational storytelling."
    ),
    "gemini": (
        "Please narrate the script in a composed, insightful tone with deliberate pacing "
        "and gentle engagement."
    ),
    "google": (
        "Deliver the narration with a calm, educational tone, keeping the cadence steady "
        "and welcoming."
    ),
}


@dataclass(frozen=True)
class PronunciationHint:
    term: str
    reading: str


@dataclass(frozen=True)
class TTSConfig:
    pronunciation_hints: List[PronunciationHint]
    pronunciation_hint_map: Dict[str, str]
    sentence_pause_ms: int
    paragraph_pause_ms: int | None
    style_prompts: Dict[str, str]
    style_prompt_overrides: Dict[str, Dict[str, str]]
    google_use_ssml: bool
    google_break_ms: int
    google_default_break_ms: int
    google_custom_breaks: Dict[str, int]
    google_voices: Dict[str, Dict[str, Any]]
    raw: Dict[str, Any]


_FILE_PATH = Path(__file__).resolve()
# tts/ -> orion/ -> media/ -> ops/ -> delax-ops/
_ORION_ROOT = _FILE_PATH.parents[1]
_WORKSPACE_ROOT = _FILE_PATH.parents[4]
_ROOT_CANDIDATES: List[Path] = []
for candidate in (_WORKSPACE_ROOT, _ORION_ROOT, Path.cwd()):
    resolved = candidate.resolve()
    if resolved not in _ROOT_CANDIDATES:
        _ROOT_CANDIDATES.append(resolved)

_PROJECT_ROOTS: List[Path] = []
for base in (_WORKSPACE_ROOT, _ORION_ROOT, _WORKSPACE_ROOT / "prototype/orion-v2"):
    projects_dir = base / "projects"
    if projects_dir.exists():
        resolved = projects_dir.resolve()
        if resolved not in _PROJECT_ROOTS:
            _PROJECT_ROOTS.append(resolved)


def _resolve_relative_path(relative: Path) -> Path:
    relative = relative.expanduser()
    if relative.is_absolute():
        return relative.resolve()
    for root in _ROOT_CANDIDATES:
        candidate = (root / relative).resolve()
        if candidate.exists():
            return candidate
    # Fall back to the first candidate to preserve debug output even if missing.
    return (_ROOT_CANDIDATES[0] / relative).resolve()


def load_tts_config() -> TTSConfig:
    """Load TTS configuration from YAML files listed in `TTS_CONFIG_PATHS`."""
    raw_config = _load_merged_config()

    pacing = raw_config.get("pacing", {}) if isinstance(raw_config.get("pacing"), dict) else {}
    sentence_pause_ms = _ensure_positive_int(pacing.get("sentence_pause_ms", 500), fallback=500)
    paragraph_pause_ms = pacing.get("paragraph_pause_ms")
    if paragraph_pause_ms is not None:
        paragraph_pause_ms = _ensure_positive_int(paragraph_pause_ms, fallback=None)

    hints_raw = raw_config.get("pronunciation_hints", [])
    hints = _dedupe_hints(_normalize_pronunciation_hints(hints_raw))
    hint_map = {hint.term: hint.reading for hint in hints}

    styles = DEFAULT_STYLE_PROMPTS.copy()
    style_overrides: Dict[str, Dict[str, str]] = {}
    style_raw = raw_config.get("style_prompts", {})
    if isinstance(style_raw, dict):
        for provider, value in style_raw.items():
            if isinstance(value, str):
                styles[provider] = value
            elif isinstance(value, dict):
                base_prompt = value.get("_base")
                if isinstance(base_prompt, str):
                    styles[provider] = base_prompt
                overrides = {
                    key: val
                    for key, val in value.items()
                    if key != "_base" and isinstance(val, str)
                }
                if overrides:
                    style_overrides[provider] = overrides

    google_settings = raw_config.get("google_tts", {})
    google_settings = google_settings if isinstance(google_settings, dict) else {}
    google_use_ssml = bool(google_settings.get("use_ssml", True))
    google_break_ms = _ensure_positive_int(
        google_settings.get("break_ms", sentence_pause_ms), fallback=sentence_pause_ms
    )
    google_default_break_ms = _ensure_positive_int(
        google_settings.get("default_break_ms", google_break_ms), fallback=google_break_ms
    )
    custom_breaks_raw = google_settings.get("custom_breaks", {})
    google_custom_breaks: Dict[str, int] = {}
    if isinstance(custom_breaks_raw, dict):
        for symbol, duration in custom_breaks_raw.items():
            google_custom_breaks[str(symbol)] = _ensure_positive_int(
                duration, fallback=google_default_break_ms
            )

    voices_raw = google_settings.get("voices", {})
    google_voices: Dict[str, Dict[str, Any]] = {}
    if isinstance(voices_raw, dict):
        for character, params in voices_raw.items():
            if isinstance(params, dict):
                google_voices[str(character)] = dict(params)

    return TTSConfig(
        pronunciation_hints=hints,
        pronunciation_hint_map=hint_map,
        sentence_pause_ms=sentence_pause_ms,
        paragraph_pause_ms=paragraph_pause_ms,
        style_prompts=styles,
        style_prompt_overrides=style_overrides,
        google_use_ssml=google_use_ssml,
        google_break_ms=google_break_ms,
        google_default_break_ms=google_default_break_ms,
        google_custom_breaks=google_custom_breaks,
        google_voices=google_voices,
        raw=_deepcopy_raw_config(raw_config),
    )


def load_merged_tts_config(project: str | None = None) -> Dict[str, Any]:
    """Return merged raw TTS configuration as a dictionary.

    Args:
        project: Optional project slug whose project-specific YAML should be
            merged in addition to paths listed in ``TTS_CONFIG_PATHS``.
    """

    extra_paths: List[Path] = []
    if project:
        slug = project.lower()
        for projects_dir in _PROJECT_ROOTS:
            candidate = projects_dir / project / "inputs" / f"{slug}_tts.yaml"
            if candidate.exists():
                extra_paths.append(candidate.resolve())

    raw_config = _load_merged_config(extra_paths)
    merged = _deepcopy_raw_config(raw_config)

    hints_map = {
        item["term"]: item["reading"]
        for item in _normalize_pronunciation_hints(merged.get("pronunciation_hints", []))
    }
    merged["pronunciation_hints"] = hints_map

    pacing = merged.get("pacing")
    if not isinstance(pacing, dict):
        pacing = {}
    pacing.setdefault("sentence_pause_ms", 500)
    pacing.setdefault("paragraph_pause_ms", None)
    merged["pacing"] = pacing

    # Ensure google_tts exists and has defaults, but preserve existing nested configs like gemini_dialogue
    if "google_tts" not in merged:
        merged["google_tts"] = {}
    google_settings = merged["google_tts"]

    if not isinstance(google_settings, dict):
        google_settings = {}
        merged["google_tts"] = google_settings

    google_settings.setdefault("use_ssml", True)
    google_settings.setdefault("break_ms", pacing.get("sentence_pause_ms", 500))
    google_settings.setdefault("default_break_ms", google_settings.get("break_ms"))
    google_settings.setdefault("custom_breaks", {})
    google_settings.setdefault("voices", {})
    # NOTE: Do NOT setdefault gemini_dialogue - it should come from config files only

    style_prompts = merged.get("style_prompts")
    if not isinstance(style_prompts, dict):
        style_prompts = {}
    merged["style_prompts"] = style_prompts

    return merged


def annotate_text_with_hints(text: str, hints: Iterable[PronunciationHint]) -> str:
    updated = text
    for hint in hints:
        if hint.term in updated:
            updated = updated.replace(hint.term, f"{hint.term}（{hint.reading}）")
    return updated


def extend_prompt(prompt: str, hints: Iterable[PronunciationHint], pause_ms: int) -> str:
    additions: List[str] = []
    effective_pause = max(pause_ms, 0)
    hints_list = list(hints)
    if hints_list:
        formatted = "、".join(f"「{hint.term}」は「{hint.reading}」" for hint in hints_list)
        additions.append(f"Pronounce the following terms carefully: {formatted}.")
    if effective_pause:
        seconds = effective_pause / 1000
        additions.append(
            "Add roughly " + f"{seconds:.1f}" + " second pause after Japanese punctuation such as '。' and '、'."
        )
    if additions:
        return prompt.rstrip() + " " + " ".join(additions)
    return prompt


def _iter_config_paths(extra_paths: Iterable[Path] | None = None) -> Iterable[Path]:
    raw = os.getenv("TTS_CONFIG_PATHS", "")
    workspace_root = _ROOT_CANDIDATES[0]
    print(f"[TTS config DEBUG] workspace_root = {workspace_root}", file=sys.stderr)
    seen: set[Path] = set()

    if raw.strip():
        for part in raw.split(","):
            trimmed = part.strip()
            if not trimmed:
                continue
            path = Path(trimmed).expanduser()
            if not path.is_absolute():
                path = _resolve_relative_path(path)
            else:
                path = path.resolve()
            if path not in seen:
                seen.add(path)
                yield path

    if extra_paths:
        for path in extra_paths:
            resolved = path
            if not resolved.is_absolute():
                resolved = _resolve_relative_path(resolved)
            else:
                resolved = resolved.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield resolved


def _load_merged_config(extra_paths: Iterable[Path] | None = None) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for path in _iter_config_paths(extra_paths):
        print(f"[TTS config DEBUG] Loading: {path}", file=sys.stderr)
        data = _read_yaml(path)
        if not data:
            continue
        print(f"[TTS config DEBUG] google_tts keys in {path.name}: {list(data.get('google_tts', {}).keys())}", file=sys.stderr)
        _merge_config(merged, data)
    print(f"[TTS config DEBUG] Final google_tts keys: {list(merged.get('google_tts', {}).keys())}", file=sys.stderr)
    return merged


def _read_yaml(path: Path) -> Dict:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"[TTS config] Skipping missing config: {path}", file=sys.stderr)
        return {}
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _merge_config(base: Dict, incoming: Dict) -> None:
    for key, value in incoming.items():
        if key == "pronunciation_hints":
            base.setdefault(key, [])
            normalized = _normalize_pronunciation_hints(value)
            if normalized:
                base[key].extend(normalized)
        elif isinstance(value, dict):
            target = base.setdefault(key, {})
            if isinstance(target, dict):
                _merge_config(target, value)
            else:
                base[key] = value
        else:
            base[key] = value


def _dedupe_hints(items: List[Dict]) -> List[PronunciationHint]:
    merged: Dict[str, str] = {}
    for item in items:
        term = str(item.get("term", "")).strip()
        reading = str(item.get("reading", "")).strip()
        if term and reading:
            merged[term] = reading
    return [PronunciationHint(term=term, reading=reading) for term, reading in merged.items()]


def _ensure_positive_int(value, fallback: int | None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback if fallback is not None else 0
    return max(number, 0)


def _normalize_pronunciation_hints(value: Any) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    if isinstance(value, dict):
        for term, reading in value.items():
            term_str = str(term).strip()
            reading_str = str(reading).strip()
            if term_str and reading_str:
                normalized.append({"term": term_str, "reading": reading_str})
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                term = str(item.get("term", "")).strip()
                reading = str(item.get("reading", "")).strip()
                if term and reading:
                    normalized.append({"term": term, "reading": reading})
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                term = str(item[0]).strip()
                reading = str(item[1]).strip()
                if term and reading:
                    normalized.append({"term": term, "reading": reading})
            elif isinstance(item, str):
                parts = [part.strip() for part in item.split(":", 1)]
                if len(parts) == 2 and all(parts):
                    normalized.append({"term": parts[0], "reading": parts[1]})
    elif isinstance(value, str):
        parts = [part.strip() for part in value.split(":", 1)]
        if len(parts) == 2 and all(parts):
            normalized.append({"term": parts[0], "reading": parts[1]})
    return normalized


def _deepcopy_raw_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return copy.deepcopy(raw)
    except TypeError:
        # Fall back to shallow copy if deepcopy fails for any object.
        return dict(raw)
