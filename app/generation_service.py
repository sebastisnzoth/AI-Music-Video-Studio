from __future__ import annotations

import os
import random
import shutil
from pathlib import Path
from typing import Any

import requests

from .comfyui import (
    ComfyUIError,
    DEFAULT_BASE_URL,
    get_history,
    load_workflow,
    output_files,
    prompt_is_active,
    queue_prompt,
    render_workflow,
)
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
    """Find ComfyUI output locally when possible.

    The app repo and ComfyUI commonly live next to each other on the user's
    external drive, so detect that layout automatically. HTTP import is still
    used as a fallback when no filesystem path is available.
    """
    candidates: list[Path] = []
    explicit = os.getenv("COMFYUI_OUTPUT_DIR")
    if explicit:
        candidates.append(Path(explicit).expanduser())
    root = os.getenv("COMFYUI_DIR")
    if root:
        candidates.append(Path(root).expanduser() / "output")
    candidates.extend([
        ROOT.parent / "ComfyUI" / "output",
        Path("/Volumes/Armazenamento/ComfyUI/output"),
        Path.home() / "ComfyUI" / "output",
    ])
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _scene_image_target(project_id: str, scene_id: int, suffix: str) -> Path:
    scene_dir = PROJECTS / project_id / "scenes" / f"{scene_id:03d}"
    scene_dir.mkdir(parents=True, exist_ok=True)
    return scene_dir / f"image-generated{suffix or '.png'}"


def _import_image_output(
    project_id: str,
    scene_id: int,
    item: dict[str, str],
    base_url: str = DEFAULT_BASE_URL,
) -> Path | None:
    filename = str(item.get("filename", "")).strip()
    if not filename:
        return None
    subfolder = str(item.get("subfolder", "")).strip()
    suffix = Path(filename).suffix.lower() or ".png"
    target = _scene_image_target(project_id, scene_id, suffix)

    # Fast path: copy directly from ComfyUI's output directory when local.
    output_dir = _comfy_output_dir()
    if output_dir is not None:
        source = output_dir / subfolder / filename if subfolder else output_dir / filename
        if source.exists():
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            return target

    # Robust path: fetch the generated media from ComfyUI's own /view endpoint.
    # This removes any dependency on where ComfyUI is installed on disk.
    params = {
        "filename": filename,
        "subfolder": subfolder,
        "type": str(item.get("type", "output") or "output"),
    }
    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/view",
            params=params,
            timeout=30,
        )
    except requests.RequestException:
        return None
    if not response.ok or not response.content:
        return None
    target.write_bytes(response.content)
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
    scene.pop("comfyui_missing_polls", None)
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
        # A manually cleared queue or restarted ComfyUI used to leave the scene
        # stuck forever at waiting_image. Detect a genuinely lost prompt and
        # release the scene so the next pipeline tick can queue it again.
        try:
            active = prompt_is_active(str(prompt_id), base_url=base_url)
        except ComfyUIError:
            active = True
        if active:
            scene.pop("comfyui_missing_polls", None)
            save_json(project_dir / "project.json", meta)
            return {
                "project_id": project_id,
                "scene_id": scene_id,
                "status": scene.get("status", "generating_image"),
                "outputs": [],
                "prompt_id": prompt_id,
            }

        missing = int(scene.get("comfyui_missing_polls", 0)) + 1
        scene["comfyui_missing_polls"] = missing
        if missing >= 3:
            scene.pop("comfyui_prompt_id", None)
            scene.pop("comfyui_missing_polls", None)
            scene["status"] = "planned"
            save_json(project_dir / "project.json", meta)
            return {
                "project_id": project_id,
                "scene_id": scene_id,
                "status": "generation_lost",
                "outputs": [],
                "requeue": True,
            }
        save_json(project_dir / "project.json", meta)
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": scene.get("status", "generating_image"),
            "outputs": [],
            "prompt_id": prompt_id,
            "missing_polls": missing,
        }

    scene.pop("comfyui_missing_polls", None)
    files = output_files(history)
    image_candidates = [item for item in files if item.get("kind") == "images"]
    imported: Path | None = None
    for candidate in image_candidates:
        imported = _import_image_output(project_id, scene_id, candidate, base_url=base_url)
        if imported is not None:
            break

    status_info = history.get("status", {}) if isinstance(history, dict) else {}
    completed = bool(status_info.get("completed", True))
    if imported is not None:
        scene["status"] = "image_ready"
        scene["generated_image"] = str(imported)
        scene["generated_image_source"] = "comfyui"
    elif completed and image_candidates:
        scene["status"] = "generation_failed"
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
