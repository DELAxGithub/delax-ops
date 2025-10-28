"""Utilities for loading LLM prompt templates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import yaml


PIPELINE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_ROOT.parent
PROMPTS_ROOT = REPO_ROOT / "config" / "prompts"


@dataclass(frozen=True)
class PromptSet:
    """Container for prompt templates used during preprocessing."""

    name: str
    model: Optional[str]
    templates: Dict[str, str]
    source_path: Path

    def render(self, *, script_text: str) -> Dict[str, str]:
        """Fill templates with shared script context."""

        rendered: Dict[str, str] = {}
        placeholder = "{script}"

        for key, template in self.templates.items():
            if not template:
                continue

            if placeholder not in template:
                raise ValueError(
                    f"Prompt template '{self.source_path}' missing placeholder '{placeholder}'"
                )

            rendered[key] = template.replace(placeholder, script_text)

        return rendered


def load_prompt_set(project_dir: Path, profile: Optional[str] = None) -> PromptSet:
    """Resolve prompt template configuration for a project."""

    search_paths = _build_search_paths(project_dir, profile)
    for candidate in search_paths:
        if candidate.exists():
            data = _load_yaml(candidate)
            prompts = data.get("prompts", {}) if isinstance(data, dict) else {}
            # Normalise keys
            normalized = {
                key.lower(): str(value)
                for key, value in prompts.items()
                if isinstance(value, str)
            }
            name = str(data.get("profile", candidate.stem)) if isinstance(data, dict) else candidate.stem
            model = data.get("llm", {}).get("model") if isinstance(data, dict) else None
            return PromptSet(name=name, model=model, templates=normalized, source_path=candidate)

    raise FileNotFoundError(
        "No prompt definition found. Checked: "
        + ", ".join(str(p) for p in search_paths)
    )


def _build_search_paths(project_dir: Path, profile: Optional[str]) -> list[Path]:
    project_config_dir = project_dir / "config"
    paths: list[Path] = []

    if project_config_dir.exists():
        if profile:
            paths.append(project_config_dir / f"prompts_{profile}.yaml")
        paths.append(project_config_dir / "prompts.yaml")

    if profile:
        paths.append(PROMPTS_ROOT / f"{profile}.yaml")
    paths.append(PROMPTS_ROOT / "default.yaml")

    # De-duplicate while preserving order
    seen = set()
    ordered: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        ordered.append(path)
        seen.add(path)
    return ordered


def _load_yaml(path: Path) -> Dict[str, object]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Prompt file must contain a YAML mapping: {path}")
    return data
