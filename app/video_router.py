from __future__ import annotations

import os
from typing import Any

from .external_video import queue_wan22_scene_video, refresh_wan22_scene_video
from .pipeline import PROJECTS, load_project, save_json
from .video_generation import queue_scene_video as queue_local_video
from .video_generation import refresh_scene_video as refresh_local_video


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    scene = next((row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id), None)
    if scene is None:
        raise KeyError(scene_id)
    return scene


def _engine() -> str:
    return os.getenv("VIDEO_ENGINE", "local").strip().lower() or "local"


def _fallback_enabled() -> bool:
    return os.getenv("VIDEO_FALLBACK", "1").strip().lower() not in {"0", "false", "no", "off"}


def _save_external_error(project_id: str, scene_id: int, error: str) -> None:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    scene["external_video_error"] = error
    save_json(PROJECTS / project_id / "project.json", meta)


def queue_scene_video(project_id: str, scene_id: int, *, fps: int = 24, **kwargs: Any) -> dict[str, Any]:
    if _engine() not in {"wan22-hf", "wan22", "hf", "huggingface"}:
        return queue_local_video(project_id, scene_id, fps=fps, **kwargs)

    try:
        return queue_wan22_scene_video(project_id, scene_id, fps=fps)
    except Exception as exc:
        _save_external_error(project_id, scene_id, str(exc))
        if not _fallback_enabled():
            raise
        result = queue_local_video(project_id, scene_id, fps=fps, **kwargs)
        result["external_error"] = str(exc)
        return result


def refresh_scene_video(project_id: str, scene_id: int, **kwargs: Any) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    backend = str(scene.get("video_generation_backend") or "").lower()
    task_id = scene.get("external_video_task_id")

    if backend != "huggingface-wan22" and not task_id:
        return refresh_local_video(project_id, scene_id, **kwargs)

    result = refresh_wan22_scene_video(project_id, scene_id)
    if result.get("status") != "generation_failed" or not _fallback_enabled():
        return result

    error = str(result.get("error") or "WAN 2.2 externo falló")
    _save_external_error(project_id, scene_id, error)

    # No ComfyUI video workflow is required: the existing local generator
    # automatically uses the FFmpeg motion fallback when no workflow is installed.
    fallback = queue_local_video(project_id, scene_id, fps=24)
    fallback["external_error"] = error
    return fallback
