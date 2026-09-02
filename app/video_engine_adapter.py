from __future__ import annotations

import os
from typing import Any

from . import video_generation as local_video
from .external_video import external_video_status, queue_wan22_scene_video, refresh_wan22_scene_video
from .pipeline import PROJECTS, load_project, save_json


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    scene = next(
        (row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id),
        None,
    )
    if scene is None:
        raise KeyError(scene_id)
    return scene


def _fallback_enabled() -> bool:
    return os.getenv("VIDEO_FALLBACK", "1").strip().lower() not in {"0", "false", "no", "off"}


def selected_video_engine() -> str:
    return os.getenv("VIDEO_ENGINE", "wan22-hf").strip().lower() or "wan22-hf"


def video_engines_status() -> dict[str, Any]:
    external = external_video_status()
    return {
        "selected": selected_video_engine(),
        "engines": [
            external,
            {
                "id": "local",
                "name": "ComfyUI / FFmpeg local",
                "available": True,
                "fallback": True,
            },
        ],
        "fallback_enabled": _fallback_enabled(),
    }


def queue_scene_video(
    project_id: str,
    scene_id: int,
    workflow_path=None,
    base_url: str = local_video.DEFAULT_BASE_URL,
    seed: int | None = None,
    fps: int = 24,
) -> dict[str, Any]:
    """Queue WAN 2.2 ZeroGPU first, preserving the existing local fallback."""
    engine = selected_video_engine()
    if engine in {"wan22-hf", "wan22", "external", "huggingface", "auto"}:
        try:
            result = queue_wan22_scene_video(project_id, scene_id, fps=fps)
            # The existing resumable orchestrator uses this field only as a
            # queue marker. A synthetic value prevents it from re-queuing WAN
            # on every polling request.
            meta = load_project(project_id)
            scene = _scene(meta, scene_id)
            scene["comfyui_video_prompt_id"] = f"external:{result['task_id']}"
            scene["requested_video_engine"] = "wan22-hf"
            save_json(PROJECTS / project_id / "project.json", meta)
            return result
        except Exception as exc:
            meta = load_project(project_id)
            scene = _scene(meta, scene_id)
            scene["external_video_error"] = str(exc)
            scene["external_video_fallback_used"] = bool(_fallback_enabled())
            save_json(PROJECTS / project_id / "project.json", meta)
            if not _fallback_enabled():
                raise

    result = local_video.queue_scene_video(
        project_id,
        scene_id,
        workflow_path=workflow_path,
        base_url=base_url,
        seed=seed,
        fps=fps,
    )
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    scene["requested_video_engine"] = engine
    save_json(PROJECTS / project_id / "project.json", meta)
    return result


def refresh_scene_video(
    project_id: str,
    scene_id: int,
    base_url: str = local_video.DEFAULT_BASE_URL,
) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    backend = str(scene.get("video_generation_backend") or "")

    if backend == "huggingface-wan22":
        result = refresh_wan22_scene_video(project_id, scene_id)
        if result.get("status") != "generation_failed":
            return result

        if not _fallback_enabled():
            return result

        # External generation can fail because a public ZeroGPU Space is busy,
        # paused or out of quota. Fall back without discarding the generated
        # still image or restarting anything.
        meta = load_project(project_id)
        scene = _scene(meta, scene_id)
        scene["external_video_error"] = result.get("error") or scene.get("external_video_error")
        scene["external_video_fallback_used"] = True
        scene.pop("external_video_task_id", None)
        scene.pop("comfyui_video_prompt_id", None)
        scene["status"] = "image_ready"
        settings = scene.get("video_generation_settings") or {}
        fps = max(1, int(settings.get("fps", 24)))
        save_json(PROJECTS / project_id / "project.json", meta)
        return local_video.queue_scene_video(project_id, scene_id, base_url=base_url, fps=fps)

    return local_video.refresh_scene_video(project_id, scene_id, base_url=base_url)
