from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .pipeline import PROJECTS, load_project, save_json


def build_identity_profile(project_id: str, description: str = "") -> dict[str, Any]:
    """Create a reusable identity profile from the project's uploaded reference.

    The profile itself is model-agnostic. ComfyUI workflows such as IPAdapter
    FaceID or InstantID can consume the same reference image and identity rules.
    """
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    visual_name = meta.get("visual")
    if not visual_name:
        raise FileNotFoundError("reference media not registered")
    reference = project_dir / str(visual_name)
    if not reference.exists():
        raise FileNotFoundError(reference)

    profile = {
        "project_id": project_id,
        "reference_path": str(reference),
        "description": description.strip(),
        "identity_rules": [
            "preserve the same person across every shot",
            "keep face shape, eye spacing, nose, jawline and skin tone consistent",
            "keep apparent age and body proportions consistent",
            "avoid identity drift between camera angles",
            "do not add duplicate versions of the performer unless explicitly requested",
        ],
        "preferred_backends": ["ipadapter", "instantid"],
    }
    profile_path = project_dir / "identity.json"
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    meta["identity_profile"] = str(profile_path)
    save_json(project_dir / "project.json", meta)
    return profile


def identity_prompt_suffix(profile: dict[str, Any]) -> str:
    rules = "; ".join(profile.get("identity_rules", []))
    description = str(profile.get("description", "")).strip()
    prefix = f"Identity description: {description}. " if description else ""
    return prefix + "Identity lock: " + rules
