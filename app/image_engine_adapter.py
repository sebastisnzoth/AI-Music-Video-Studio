from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from . import generation_service as image_generation
from .pipeline import load_project

# Single worker process: serialize only the tiny "check state + enqueue" window.
# This prevents browser retries/concurrent polling calls from queuing the same
# scene image more than once.
_image_queue_lock = threading.Lock()


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    scene = next(
        (row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id),
        None,
    )
    if scene is None:
        raise KeyError(scene_id)
    return scene


def queue_scene_image(
    project_id: str,
    scene_id: int,
    checkpoint: str,
    base_url: str = image_generation.DEFAULT_BASE_URL,
    workflow_path: Path = image_generation.DEFAULT_IMAGE_WORKFLOW,
    seed: int | None = None,
    steps: int = 24,
    cfg: float = 6.0,
) -> dict[str, Any]:
    with _image_queue_lock:
        meta = load_project(project_id)
        scene = _scene(meta, scene_id)

        existing_prompt = str(scene.get("comfyui_prompt_id") or "").strip()
        generated_image = str(scene.get("generated_image") or "").strip()
        if existing_prompt and not generated_image:
            settings = scene.get("generation_settings") or {}
            return {
                "project_id": project_id,
                "scene_id": scene_id,
                "prompt_id": existing_prompt,
                "status": scene.get("status", "generating_image"),
                "settings": settings,
                "deduplicated": True,
            }

        # CPU-only Intel Macs need a fast preview path. 8 Euler steps is enough
        # to validate composition/identity before WAN 2.2 animates the frame.
        quality = str(meta.get("quality", "preview")).strip().lower()
        actual_steps = int(steps)
        if quality == "preview" and actual_steps >= 24:
            actual_steps = 8

        return image_generation.queue_scene_image(
            project_id,
            scene_id,
            checkpoint=checkpoint,
            base_url=base_url,
            workflow_path=workflow_path,
            seed=seed,
            steps=max(1, actual_steps),
            cfg=float(cfg),
        )
