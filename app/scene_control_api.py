from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .pipeline import PROJECTS, load_project, save_json

router = APIRouter(prefix="/api")


def _find_scene(meta: dict, scene_id: int):
    return next(
        (row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id),
        None,
    )


@router.get("/projects/{project_id}/scenes/{scene_id}/preview")
def scene_preview(project_id: str, scene_id: int):
    """Serve the best available scene media for browser review."""
    try:
        meta = load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc

    scene = _find_scene(meta, scene_id)
    if scene is None:
        raise HTTPException(404, f"Scene {scene_id} not found")

    for key in (
        "review_candidate",
        "upscaled_clip",
        "lipsync_clip",
        "face_refined_clip",
        "generated_clip",
        "generated_image",
    ):
        value = str(scene.get(key, "") or "").strip()
        if not value:
            continue
        path = Path(value)
        if path.exists() and path.is_file():
            media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            return FileResponse(path, media_type=media_type)

    raise HTTPException(404, "Scene preview not available yet")


@router.post("/projects/{project_id}/scenes/{scene_id}/reset-generation")
def reset_scene_generation(project_id: str, scene_id: int):
    """Reset only one scene so it can be generated again without restarting the worker."""
    try:
        meta = load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc

    scene = _find_scene(meta, scene_id)
    if scene is None:
        raise HTTPException(404, f"Scene {scene_id} not found")

    transient_keys = {
        "generated_image",
        "generated_image_source",
        "image_generation_backend",
        "external_image_task_id",
        "external_image_error",
        "generated_clip",
        "generated_clip_source",
        "face_refined_clip",
        "lipsync_clip",
        "upscaled_clip",
        "review_candidate",
        "review_version",
        "comfyui_prompt_id",
        "comfyui_video_prompt_id",
        "comfyui_outputs",
        "comfyui_video_outputs",
        "generation_settings",
        "video_generation_settings",
        "video_generation_backend",
        "requested_video_engine",
        "external_video_task_id",
        "external_video_error",
        "external_video_fallback_used",
        "auto_pipeline_error",
        "auto_pipeline_log",
        "versions",
    }
    for key in transient_keys:
        scene.pop(key, None)

    scene["status"] = "planned"
    scene["approved"] = False
    scene["auto_pipeline_state"] = "idle"

    save_json(PROJECTS / project_id / "project.json", meta)
    return {
        "ok": True,
        "project_id": project_id,
        "scene_id": scene_id,
        "status": scene["status"],
        "auto_state": scene["auto_pipeline_state"],
        "approved": False,
    }
