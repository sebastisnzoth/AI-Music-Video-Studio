from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any

from .comfyui import DEFAULT_BASE_URL, ComfyUIError, get_history, load_workflow, output_files, queue_prompt, render_workflow
from .pipeline import PROJECTS, load_project, save_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIDEO_WORKFLOW = ROOT / "workflows" / "scene-video-api.json"


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    item = next((x for x in meta.get("storyboard", []) if int(x.get("id", -1)) == scene_id), None)
    if item is None:
        raise KeyError(scene_id)
    return item


def queue_scene_video(
    project_id: str,
    scene_id: int,
    workflow_path: Path | None = None,
    base_url: str = DEFAULT_BASE_URL,
    seed: int | None = None,
    fps: int = 24,
) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    generated_image = scene.get("generated_image")
    if not generated_image:
        raise FileNotFoundError("generated_image is required before image-to-video")

    selected_workflow = workflow_path or Path(os.getenv("COMFYUI_VIDEO_WORKFLOW", str(DEFAULT_VIDEO_WORKFLOW)))
    if not selected_workflow.exists():
        raise FileNotFoundError(
            f"Video workflow not found: {selected_workflow}. Export a ComfyUI API workflow and set COMFYUI_VIDEO_WORKFLOW."
        )

    actual_seed = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    duration = max(1.0, float(scene.get("duration", 5.0)))
    frame_count = max(8, int(round(duration * fps)))
    variables = {
        "prompt": scene.get("director_prompt") or scene.get("prompt", ""),
        "negative_prompt": scene.get("negative_prompt", ""),
        "reference_path": str(generated_image),
        "audio_path": str(scene.get("scene_audio") or ""),
        "duration": duration,
        "fps": int(fps),
        "frame_count": frame_count,
        "seed": actual_seed,
        "scene_id": f"{scene_id:03d}",
    }

    workflow = render_workflow(load_workflow(selected_workflow), variables)
    prompt_id = queue_prompt(workflow, base_url=base_url)

    scene["status"] = "generating_video"
    scene["video_generation_backend"] = "comfyui"
    scene["comfyui_video_prompt_id"] = prompt_id
    scene["video_generation_settings"] = {
        "workflow": str(selected_workflow),
        "seed": actual_seed,
        "fps": int(fps),
        "frame_count": frame_count,
        "duration": duration,
    }
    save_json(PROJECTS / project_id / "project.json", meta)
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "backend": "comfyui",
        "prompt_id": prompt_id,
        "settings": scene["video_generation_settings"],
    }


def refresh_scene_video(project_id: str, scene_id: int, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    prompt_id = scene.get("comfyui_video_prompt_id")
    if not prompt_id:
        return {"project_id": project_id, "scene_id": scene_id, "status": scene.get("status", "planned"), "outputs": []}

    history = get_history(str(prompt_id), base_url=base_url)
    if history is None:
        return {"project_id": project_id, "scene_id": scene_id, "status": "generating_video", "outputs": []}

    files = output_files(history)
    video_candidates = [f for f in files if f.get("kind") in {"videos", "gifs"}]
    if video_candidates:
        scene["status"] = "video_ready"
        scene["comfyui_video_outputs"] = video_candidates
    else:
        status_info = history.get("status", {}) if isinstance(history, dict) else {}
        completed = bool(status_info.get("completed", True))
        scene["status"] = "generation_failed" if completed else "generating_video"
        scene["comfyui_video_outputs"] = files
    save_json(PROJECTS / project_id / "project.json", meta)
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "status": scene["status"],
        "outputs": scene.get("comfyui_video_outputs", []),
        "prompt_id": prompt_id,
    }
