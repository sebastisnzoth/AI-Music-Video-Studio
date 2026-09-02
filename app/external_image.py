from __future__ import annotations

import os
import random
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

from .pipeline import PROJECTS, load_project, save_json

DEFAULT_SPACE = os.getenv("HF_IMAGE_SPACE", "black-forest-labs/FLUX.2-klein-4B").strip()
DEFAULT_API_NAME = os.getenv("HF_IMAGE_API_NAME", "/infer").strip() or "/infer"

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    scene = next(
        (row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id),
        None,
    )
    if scene is None:
        raise KeyError(scene_id)
    return scene


def external_image_status() -> dict[str, Any]:
    enabled = os.getenv("HF_IMAGE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
    try:
        import gradio_client  # noqa: F401
        client_installed = True
        error = None
    except Exception as exc:  # pragma: no cover
        client_installed = False
        error = str(exc)
    return {
        "id": "flux2-klein-hf",
        "name": "FLUX.2 Klein 4B · Hugging Face ZeroGPU",
        "enabled": enabled,
        "client_installed": client_installed,
        "available": bool(enabled and client_installed and DEFAULT_SPACE),
        "space": DEFAULT_SPACE,
        "api_name": DEFAULT_API_NAME,
        "authenticated": bool(os.getenv("HF_TOKEN", "").strip()),
        "error": error,
    }


def _extract_path(value: Any) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value if value.exists() else None
    if isinstance(value, str):
        path = Path(value)
        return path if path.exists() else None
    if isinstance(value, dict):
        for key in ("path", "name"):
            candidate = value.get(key)
            if isinstance(candidate, str) and Path(candidate).exists():
                return Path(candidate)
        for candidate in value.values():
            found = _extract_path(candidate)
            if found:
                return found
    if isinstance(value, (list, tuple)):
        for candidate in value:
            found = _extract_path(candidate)
            if found:
                return found
    return None


def _reference_image(project_id: str, meta: dict[str, Any]) -> Path | None:
    visual_name = str(meta.get("visual") or "").strip()
    if not visual_name:
        return None
    source = PROJECTS / project_id / visual_name
    if not source.exists():
        return None
    if str(meta.get("visual_kind") or "").lower() == "image":
        return source

    # A video reference is reduced to one clean frame. This is very cheap compared
    # with diffusion and lets the remote image editor preserve the artist identity.
    frame = PROJECTS / project_id / "reference-frame.jpg"
    if frame.exists():
        return frame
    proc = subprocess.run(
        [
            "ffmpeg", "-y", "-ss", "0.5", "-i", str(source),
            "-frames:v", "1", "-q:v", "2", str(frame),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return frame if proc.returncode == 0 and frame.exists() else None


def _dimensions(meta: dict[str, Any]) -> tuple[int, int]:
    # Stay comfortably inside the ZeroGPU demo limits while keeping video aspect.
    return (1024, 576) if str(meta.get("aspect") or "16:9") == "16:9" else (576, 1024)


def queue_flux2_scene_image(
    project_id: str,
    scene_id: int,
    *,
    fallback_checkpoint: str = "",
    seed: int | None = None,
) -> dict[str, Any]:
    status = external_image_status()
    if not status["available"]:
        raise RuntimeError(status.get("error") or "Motor FLUX.2 externo no disponible")

    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    reference = _reference_image(project_id, meta)

    try:
        from gradio_client import Client, handle_file
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"gradio_client no disponible: {exc}") from exc

    prompt = str(scene.get("director_prompt") or scene.get("prompt") or "").strip()
    if not prompt:
        prompt = "cinematic music video still, realistic artist, professional lighting, no text"

    if reference:
        prompt = (
            "Use the person in image 1 as the same artist. Preserve the same face, age, hair, "
            "body proportions and recognizable identity. " + prompt
        )

    width, height = _dimensions(meta)
    actual_seed = int(seed) if seed is not None else random.randint(1, 2**31 - 1)
    token = os.getenv("HF_TOKEN", "").strip() or None
    client_kwargs: dict[str, Any] = {"verbose": False}
    if token:
        client_kwargs["token"] = token
    client = Client(DEFAULT_SPACE, **client_kwargs)

    gallery = [handle_file(str(reference))] if reference else None
    # Current official Space signature:
    # prompt, input_images, mode, seed, randomize_seed, width, height,
    # num_inference_steps, guidance_scale, prompt_upsampling.
    job = client.submit(
        prompt,
        gallery,
        "Distilled (4 steps)",
        actual_seed,
        False,
        width,
        height,
        4,
        1.0,
        False,
        api_name=DEFAULT_API_NAME,
    )

    task_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[task_id] = {
            "client": client,
            "job": job,
            "project_id": project_id,
            "scene_id": scene_id,
        }

    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    scene["status"] = "generating_external_image"
    scene["image_generation_backend"] = "huggingface-flux2-klein"
    scene["external_image_task_id"] = task_id
    # Keep the legacy field because the resumable orchestrator uses it as its
    # generic image-task handle. routed refresh knows how to resolve this prefix.
    scene["comfyui_prompt_id"] = f"external-image:{task_id}"
    scene["generation_settings"] = {
        "provider": "huggingface",
        "space": DEFAULT_SPACE,
        "api_name": DEFAULT_API_NAME,
        "mode": "Distilled (4 steps)",
        "steps": 4,
        "seed": actual_seed,
        "width": width,
        "height": height,
        "reference_image": str(reference) if reference else None,
        "fallback_checkpoint": fallback_checkpoint,
    }
    save_json(PROJECTS / project_id / "project.json", meta)
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "prompt_id": scene["comfyui_prompt_id"],
        "task_id": task_id,
        "backend": "huggingface-flux2-klein",
        "status": scene["status"],
        "settings": scene["generation_settings"],
    }


def refresh_flux2_scene_image(project_id: str, scene_id: int) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    task_id = str(scene.get("external_image_task_id") or "").strip()
    if not task_id:
        return {"project_id": project_id, "scene_id": scene_id, "status": "generation_failed", "error": "No hay tarea externa de imagen"}

    with _jobs_lock:
        record = _jobs.get(task_id)
    if record is None:
        return {"project_id": project_id, "scene_id": scene_id, "status": "generation_failed", "error": "La tarea FLUX.2 se perdió al reiniciar el worker", "task_id": task_id}

    job = record["job"]
    if not job.done():
        queue_rank = None
        queue_size = None
        provider_status = "queued"
        try:
            info = job.status()
            queue_rank = getattr(info, "rank", None)
            queue_size = getattr(info, "queue_size", None)
            code = getattr(info, "code", None)
            provider_status = str(getattr(code, "name", code) or "queued").lower()
        except Exception:
            pass
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": "generating_external_image",
            "backend": "huggingface-flux2-klein",
            "task_id": task_id,
            "queue_rank": queue_rank,
            "queue_size": queue_size,
            "provider_status": provider_status,
        }

    try:
        result = job.result()
        source = _extract_path(result)
        if source is None or not source.exists():
            raise RuntimeError(f"FLUX.2 terminó sin devolver una imagen utilizable: {result!r}")
        scene_dir = PROJECTS / project_id / "scenes" / f"{scene_id:03d}"
        scene_dir.mkdir(parents=True, exist_ok=True)
        suffix = source.suffix.lower() if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} else ".png"
        target = scene_dir / f"image-generated-flux2{suffix}"
        shutil.copy2(source, target)

        meta = load_project(project_id)
        scene = _scene(meta, scene_id)
        scene["status"] = "image_ready"
        scene["generated_image"] = str(target)
        scene["generated_image_source"] = "huggingface-flux2-klein"
        scene["image_generation_backend"] = "huggingface-flux2-klein"
        scene.pop("external_image_error", None)
        save_json(PROJECTS / project_id / "project.json", meta)
        with _jobs_lock:
            _jobs.pop(task_id, None)
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": "image_ready",
            "backend": "huggingface-flux2-klein",
            "generated_image": str(target),
            "outputs": [{"filename": target.name, "path": str(target)}],
        }
    except Exception as exc:
        meta = load_project(project_id)
        scene = _scene(meta, scene_id)
        scene["status"] = "generation_failed"
        scene["external_image_error"] = str(exc)
        save_json(PROJECTS / project_id / "project.json", meta)
        with _jobs_lock:
            _jobs.pop(task_id, None)
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": "generation_failed",
            "backend": "huggingface-flux2-klein",
            "task_id": task_id,
            "error": str(exc),
        }
