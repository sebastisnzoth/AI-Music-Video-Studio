from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .pipeline import PROJECTS, load_project, save_json

router = APIRouter(prefix="/api")


@router.post("/projects/{project_id}/scenes/{scene_id}/reset-generation")
def reset_scene_generation(project_id: str, scene_id: int):
    """Reset only one scene so it can be generated again without restarting the worker."""
    try:
        meta = load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc

    scene = next(
        (row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id),
        None,
    )
    if scene is None:
        raise HTTPException(404, f"Scene {scene_id} not found")

    transient_keys = {
        "generated_image",
        "generated_image_source",
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
