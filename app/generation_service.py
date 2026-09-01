from __future__ import annotations

import os
import random
import shutil
from pathlib import Path
from typing import Any

from .comfyui import ComfyUIError, DEFAULT_BASE_URL, get_history, load_workflow, output_files, queue_prompt, render_workflow
from .pipeline import PROJECTS, load_project, save_json
from .scene_package import prepare_scene_package

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE_WORKFLOW = ROOT / "workflows" / "scene-image-api.json"


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    item = next((row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id), None)
    if item is None:
        raise KeyError(scene_id)
    return item


def _dimensions(aspect: str, quality: str) -> tuple[int, int]:
    if aspect == "9:16":
        return (576, 1024) if quality != "preview" else (432, 768)
    return (1024, 576) if quality != "preview" else (768, 432)


def _comfy_output_dir() -> Path | None:
    explicit = os.getenv("COMFYUI_OUTPUT_DIR")
    if explicit:
        return Path(explicit).expanduser()
    root = os.getenv("COMFYUI_DIR")
    if root:
        return Path(root).expanduser() / "output"
    conventional = Path.home() / "ComfyUI" / "output"
    return conventional if conventional.exists() else None


def _import_image_output(project_id: str, scene_id: int, item: dict[str, str]) -> Path | None:
    output_dir = _comfy_output_dir()
    if output_dir is None:
        return None
    filename = str(item.get("filename", "")).strip()
    if not filename:
        return None
    subfolder = str(item.get("subfolder", "")).strip()
    source = output_dir / subfolder / filename if subfolder else output_dir / filename
    if not source.exists():
        return None
    scene_dir = PROJECTS / project_id / "scenes" / f"{scene_id:03d}"
    scene_dir.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower() or ".png"
    target = scene_dir / f"image-generated{suffix}"
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target


def queue_scene_image(
    project_id: str,
    scene_id: int,
    checkpoint: str,
    base_url: str = DEFAULT_BASE_URL,
    workflow_path: Path = DEFAULT_IMAGE_WORKFLOW,
    seed: int | None = None,
    steps: int = 24,
    cfg: float = 6.0,
) -> dict[str, Any]:
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    package = prepare_scene_package(project_id, scene_id)
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)

    width, height = _dimensions(str(meta.get("aspect", "16:9")), str(meta.get("quality", "final")))
    actual_seed = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    variables = {
        "checkpoint": checkpoint,
        "prompt": package.get("prompt", ""),
        "negative_prompt": package.get("negative_prompt", ""),
        "width": width,
        "height": height,
        "seed": actual_seed,
        "steps": int(steps),
        "cfg": float(cfg),
        "scene_id": f"{scene_id:03d}",
    }
    workflow = render_workflow(load_workflow(workflow_path), variables)
    prompt_id = queue_prompt(workflow, base_url=base_url)

    scene["status"] = "generating_image"
    scene["generation_engine"] = "comfyui-image"
    scene["comfyui_prompt_id"] = prompt_id
    scene["generation_settings"] = {
        "checkpoint": checkpoint,
        "seed": actual_seed,
        "steps": int(steps),
        "cfg": float(cfg),
        "width": width,
        "height": height,
    }
    save_json(project_dir / "project.json", meta)
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "prompt_id": prompt_id,
        "status": scene["status"],
        "settings": scene["generation_settings"],
    }


def refresh_scene_generation(project_id: str, scene_id: int, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = _scene(meta, scene_id)
    prompt_id = scene.get("comfyui_prompt_id")
    if not prompt_id:
        return {"project_id": project_id, "scene_id": scene_id, "status": scene.get("status", "planned"), "outputs": []}

    try:
        history = get_history(str(prompt_id), base_url=base_url)
    except ComfyUIError as exc:
        # En CPU ComfyUI puede tardar en responder mientras genera. Eso no debe
        # detener el pipeline: se considera un fallo transitorio y se reintenta.
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": scene.get("status", "generating_image"),
            "outputs": [],
            "transient": True,
            "transient_error": str(exc),
            "prompt_id": prompt_id,
        }

    if history is None:
        return {"project_id": project_id, "scene_id": scene_id, "status": scene.get("status", "generating_image"), "outputs": []}

    files = output_files(history)
    image_candidates = [item for item in files if item.get("kind") == "images"]
    imported: Path | None = None
    for candidate in image_candidates:
        imported = _import_image_output(project_id, scene_id, candidate)
        if imported is not None:
            break

    status_info = history.get("status", {}) if isinstance(history, dict) else {}
    completed = bool(status_info.get("completed", True))
    if imported is not None:
        scene["status"] = "image_ready"
        scene["generated_image"] = str(imported)
        scene["generated_image_source"] = "comfyui"
    elif completed and image_candidates:
        scene["status"] = "image_ready_external"
    else:
        scene["status"] = "generation_failed" if completed else "generating_image"
    scene["comfyui_outputs"] = files
    save_json(project_dir / "project.json", meta)
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "status": scene["status"],
        "outputs": files,
        "generated_image": scene.get("generated_image"),
        "output_dir": str(_comfy_output_dir()) if _comfy_output_dir() else None,
        "prompt_id": prompt_id,
    }
