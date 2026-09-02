from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from . import generation_service as image_generation
from .external_image import (
    external_image_status,
    queue_flux2_scene_image,
    refresh_flux2_scene_image,
)
from .pipeline import PROJECTS, load_project, save_json

# Single worker process: serialize only the tiny "check state + enqueue" window.
_image_queue_lock = threading.Lock()


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    scene = next(
        (row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id),
        None,
    )
    if scene is None:
        raise KeyError(scene_id)
    return scene


def _preferred_engine() -> str:
    return os.getenv("IMAGE_ENGINE", "flux2-hf").strip().lower() or "flux2-hf"


def _fallback_enabled() -> bool:
    return os.getenv("IMAGE_FALLBACK_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


def _local_queue(
    project_id: str,
    scene_id: int,
    *,
    checkpoint: str,
    base_url: str,
    workflow_path: Path,
    seed: int | None,
    steps: int,
    cfg: float,
) -> dict[str, Any]:
    meta = load_project(project_id)
    quality = str(meta.get("quality", "preview")).strip().lower()
    actual_steps = int(steps)
    if quality == "preview" and actual_steps >= 24:
        actual_steps = 8
    result = image_generation.queue_scene_image(
        project_id,
        scene_id,
        checkpoint=checkpoint,
        base_url=base_url,
        workflow_path=workflow_path,
        seed=seed,
        steps=max(1, actual_steps),
        cfg=float(cfg),
    )
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    scene["image_generation_backend"] = "comfyui"
    save_json(PROJECTS / project_id / "project.json", meta)
    return result


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
                "backend": scene.get("image_generation_backend"),
            }

        engine = _preferred_engine()
        if engine in {"flux2-hf", "flux2", "huggingface", "external", "auto"}:
            status = external_image_status()
            if status.get("available"):
                try:
                    return queue_flux2_scene_image(
                        project_id,
                        scene_id,
                        fallback_checkpoint=checkpoint,
                        seed=seed,
                    )
                except Exception as exc:
                    # A schema/queue/network failure should not kill the scene. Keep
                    # the reason for diagnostics and immediately use the local path.
                    meta = load_project(project_id)
                    scene = _scene(meta, scene_id)
                    scene["external_image_error"] = str(exc)
                    save_json(PROJECTS / project_id / "project.json", meta)
                    if not _fallback_enabled():
                        raise

        return _local_queue(
            project_id,
            scene_id,
            checkpoint=checkpoint,
            base_url=base_url,
            workflow_path=workflow_path,
            seed=seed,
            steps=steps,
            cfg=cfg,
        )


def refresh_scene_generation(
    project_id: str,
    scene_id: int,
    base_url: str = image_generation.DEFAULT_BASE_URL,
) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    prompt_id = str(scene.get("comfyui_prompt_id") or "").strip()

    if prompt_id.startswith("external-image:") or scene.get("external_image_task_id"):
        result = refresh_flux2_scene_image(project_id, scene_id)
        if result.get("status") != "generation_failed":
            return result

        # ZeroGPU may be full, sleeping, or its public Gradio signature may change.
        # Fall back once to the already-installed local ComfyUI instead of leaving
        # the scene stuck. The checkpoint is persisted when the remote job starts.
        meta = load_project(project_id)
        scene = _scene(meta, scene_id)
        settings = scene.get("generation_settings") or {}
        checkpoint = str(settings.get("fallback_checkpoint") or "").strip()
        if _fallback_enabled() and checkpoint:
            external_error = str(result.get("error") or scene.get("external_image_error") or "FLUX.2 failed")
            for key in ("external_image_task_id", "comfyui_prompt_id"):
                scene.pop(key, None)
            scene["external_image_error"] = external_error
            scene["status"] = "planned"
            save_json(PROJECTS / project_id / "project.json", meta)
            queued = _local_queue(
                project_id,
                scene_id,
                checkpoint=checkpoint,
                base_url=base_url,
                workflow_path=image_generation.DEFAULT_IMAGE_WORKFLOW,
                seed=settings.get("seed"),
                steps=8,
                cfg=6.0,
            )
            queued["fallback_from"] = "huggingface-flux2-klein"
            queued["external_error"] = external_error
            return queued
        return result

    return image_generation.refresh_scene_generation(project_id, scene_id, base_url=base_url)
