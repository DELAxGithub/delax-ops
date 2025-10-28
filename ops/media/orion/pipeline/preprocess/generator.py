"""Phase 0 preprocessing utilities (script → draft inputs)."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .prompt_loader import load_prompt_set


EXPECTED_OUTPUTS = {
    "srt": "teleop_raw.srt",
    "nare": "nare.md",
    "yaml": "nare.yaml",
}

PROMPT_FILENAMES = {
    "srt": "srt_prompt.md",
    "nare": "nare_prompt.md",
    "yaml": "yaml_prompt.md",
}


@dataclass
class GenerationStatus:
    """Metadata describing preprocessing artefacts."""

    project: str
    prompt_profile: str
    prompts: Dict[str, str]
    applied_inputs: bool
    updated_at: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "project": self.project,
                "prompt_profile": self.prompt_profile,
                "prompts": self.prompts,
                "applied_inputs": self.applied_inputs,
                "updated_at": self.updated_at,
            },
            indent=2,
            ensure_ascii=False,
        )


def generate_inputs_from_script(
    ctx,
    *,
    prompt_profile: Optional[str] = None,
    force: bool = False,
    apply: bool = False,
) -> bool:
    """Generate draft inputs/prompts from the source script."""

    if ctx.script_md is None or not ctx.script_md.exists():
        print(f"❌ Script markdown not found for {ctx.project}: {ctx.script_md}")
        return False

    script_text = ctx.script_md.read_text(encoding="utf-8")
    prompt_set = load_prompt_set(ctx.project_dir, profile=prompt_profile)

    generated_dir = ctx.generated_dir
    prompts_dir = generated_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)

    rendered_prompts = prompt_set.render(script_text=script_text)

    prompt_records: Dict[str, str] = {}
    for key, content in rendered_prompts.items():
        filename = PROMPT_FILENAMES.get(key, f"{key}_prompt.md")
        path = prompts_dir / filename
        if path.exists() and not force:
            print(f"⏭️  {filename} already exists (use --force-regenerate to overwrite)")
        else:
            path.write_text(content, encoding="utf-8")
            print(f"✅  Wrote {filename} in {prompts_dir.relative_to(ctx.project_dir)}")
        prompt_records[key] = str(path.relative_to(ctx.project_dir))

    status = GenerationStatus(
        project=ctx.project,
        prompt_profile=prompt_set.name,
        prompts=prompt_records,
        applied_inputs=False,
        updated_at=datetime.now().isoformat(timespec="seconds"),
    )

    status_path = generated_dir / "status.json"
    status_path.write_text(status.to_json(), encoding="utf-8")

    if apply:
        applied = _apply_generated_outputs(ctx, force=force)
        status.applied_inputs = applied
        status.updated_at = datetime.now().isoformat(timespec="seconds")
        status_path.write_text(status.to_json(), encoding="utf-8")
        if applied:
            print("✅  Generated inputs copied into inputs/ directory")
        else:
            print("⚠️  No generated inputs were applied")
        return applied

    print(
        "ℹ️  Review prompt files in generated/prompts/, run Sonnet 4.5 manually, "
        "then place the resulting drafts into generated/ before re-running with "
        "--apply-generated-inputs."
    )
    return True


def _apply_generated_outputs(ctx, *, force: bool) -> bool:
    episode_suffix = "".join(ch for ch in ctx.project if ch.isdigit())
    if not episode_suffix:
        episode_suffix = ctx.project.lower()

    expected_paths = {
        key: ctx.generated_dir / filename
        for key, filename in EXPECTED_OUTPUTS.items()
    }

    mapping = {
        "srt": _determine_destination(
            existing=ctx.source_srt,
            root=ctx.inputs_dir,
            default_name=f"ep{episode_suffix}.srt",
        ),
        "nare": _determine_destination(
            existing=ctx.narration_md,
            root=ctx.inputs_dir,
            default_name=f"ep{episode_suffix}nare.md",
        ),
        "yaml": _determine_destination(
            existing=ctx.narration_yaml,
            root=ctx.inputs_dir,
            default_name=f"ep{episode_suffix}nare.yaml",
        ),
    }

    applied = False
    for key, src in expected_paths.items():
        dest = mapping.get(key)
        if dest is None:
            continue
        if not src.exists():
            print(f"⚠️  Expected generated file not found: {src.relative_to(ctx.project_dir)}")
            continue
        if dest.exists() and not force:
            print(f"⏭️  {dest.relative_to(ctx.project_dir)} already exists (use --force-regenerate to overwrite)")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"✅  Copied {src.relative_to(ctx.project_dir)} → {dest.relative_to(ctx.project_dir)}")
        applied = True

    return applied


def _determine_destination(*, existing: Optional[Path], root: Path, default_name: str) -> Path:
    if existing is not None:
        return existing
    return root / default_name
