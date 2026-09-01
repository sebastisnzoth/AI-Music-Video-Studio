from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import requests

COMFY_URL = "http://127.0.0.1:8188"
ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "workflows"


def is_online(timeout: float = 1.0) -> bool:
    try:
        return requests.get(f"{COMFY_URL}/system_stats", timeout=timeout).ok
    except requests.RequestException:
        return False


def load_workflow(name: str = "scene.json") -> dict[str, Any]:
    path = WORKFLOWS / name
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _replace(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        for key, replacement in variables.items():
            value = value.replace("{{" + key + "}}", str(replacement))
        return value
    if isinstance(value, list):
        return [_replace(x, variables) for x in value]
    if isinstance(value, dict):
        return {k: _replace(v, variables) for k, v in value.items()}
    return value


def prepare_workflow(template: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    """Replace {{variable}} placeholders recursively in an API-format ComfyUI workflow."""
    return _replace(copy.deepcopy(template), variables)


def queue_scene(scene: dict[str, Any], project_dir: Path, reference_path: Path, workflow_name: str = "scene.json") -> str:
    if not is_online():
        raise RuntimeError("ComfyUI no está ejecutándose en http://127.0.0.1:8188")

    template = load_workflow(workflow_name)
    variables = {
        "prompt": scene.get("prompt", "cinematic music video"),
        "scene_id": scene.get("id"),
        "duration": scene.get("duration", 5.0),
        "reference_path": str(reference_path.resolve()),
        "output_prefix": str((project_dir / "generated" / f"scene-{scene.get('id')}").resolve()),
    }
    prompt = prepare_workflow(template, variables)
    response = requests.post(f"{COMFY_URL}/prompt", json={"prompt": prompt}, timeout=15)
    if not response.ok:
        raise RuntimeError(f"ComfyUI rechazó el workflow: {response.text[:500]}")
    payload = response.json()
    prompt_id = payload.get("prompt_id")
    if not prompt_id:
        raise RuntimeError("ComfyUI no devolvió prompt_id")
    return str(prompt_id)


def history(prompt_id: str) -> dict[str, Any]:
    response = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=5)
    response.raise_for_status()
    return response.json()
