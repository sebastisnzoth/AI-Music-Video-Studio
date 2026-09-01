from __future__ import annotations

from typing import Any

from .pipeline import load_project
from .scene_package import prepare_scene_package


def prepare_batch(project_id: str, only_unprepared: bool = True) -> dict[str, Any]:
    meta = load_project(project_id)
    prepared = []
    skipped = []
    for scene in meta.get("storyboard", []):
        scene_id = int(scene["id"])
        if only_unprepared and scene.get("scene_package"):
            skipped.append(scene_id)
            continue
        prepared.append(prepare_scene_package(project_id, scene_id))
    return {
        "project_id": project_id,
        "prepared_count": len(prepared),
        "skipped_scene_ids": skipped,
        "scenes": prepared,
    }


def generation_queue(project_id: str) -> dict[str, Any]:
    meta = load_project(project_id)
    rows = []
    for scene in meta.get("storyboard", []):
        rows.append({
            "scene_id": int(scene.get("id", -1)),
            "status": scene.get("status", "planned"),
            "approved": bool(scene.get("approved", False)),
            "needs_lipsync": bool(scene.get("needs_lipsync", False)),
            "toolchain": scene.get("toolchain", {}),
            "prompt_id": scene.get("comfyui_prompt_id"),
        })
    return {"project_id": project_id, "queue": rows}
