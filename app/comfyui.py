from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8188"


class ComfyUIError(RuntimeError):
    pass


def is_online(base_url: str = DEFAULT_BASE_URL, timeout: float = 1.0) -> bool:
    try:
        return requests.get(f"{base_url.rstrip('/')}/system_stats", timeout=timeout).ok
    except requests.RequestException:
        return False


def load_workflow(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ComfyUIError("El workflow debe ser un objeto JSON exportado en formato API de ComfyUI")
    return payload


def _replace(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {k: _replace(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace(v, variables) for v in value]
    if isinstance(value, str):
        result = value
        for key, replacement in variables.items():
            token = "{{" + key + "}}"
            if result == token:
                return replacement
            result = result.replace(token, str(replacement))
        return result
    return value


def render_workflow(template: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    return _replace(copy.deepcopy(template), variables)


def queue_prompt(workflow: dict[str, Any], base_url: str = DEFAULT_BASE_URL, timeout: float = 20.0) -> str:
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/prompt",
            json={"prompt": workflow},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise ComfyUIError(f"No se pudo conectar con ComfyUI: {exc}") from exc
    if not response.ok:
        raise ComfyUIError(f"ComfyUI rechazó el workflow ({response.status_code}): {response.text[:1000]}")
    data = response.json()
    prompt_id = data.get("prompt_id")
    if not prompt_id:
        raise ComfyUIError(f"Respuesta sin prompt_id: {data}")
    return str(prompt_id)


def get_history(prompt_id: str, base_url: str = DEFAULT_BASE_URL, timeout: float = 10.0) -> dict[str, Any] | None:
    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/history/{prompt_id}",
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise ComfyUIError(f"No se pudo consultar ComfyUI: {exc}") from exc
    if not response.ok:
        raise ComfyUIError(f"Error consultando historial ({response.status_code})")
    data = response.json()
    item = data.get(prompt_id)
    return item if isinstance(item, dict) else None


def wait_for_prompt(
    prompt_id: str,
    base_url: str = DEFAULT_BASE_URL,
    poll_seconds: float = 1.5,
    timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    started = time.monotonic()
    while time.monotonic() - started < timeout_seconds:
        item = get_history(prompt_id, base_url=base_url)
        if item is not None:
            return item
        time.sleep(poll_seconds)
    raise TimeoutError(f"ComfyUI no terminó el prompt {prompt_id} dentro del tiempo límite")


def output_files(history_item: dict[str, Any]) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    outputs = history_item.get("outputs", {})
    if not isinstance(outputs, dict):
        return files
    for node_id, node_output in outputs.items():
        if not isinstance(node_output, dict):
            continue
        for key in ("images", "gifs", "videos"):
            media = node_output.get(key, [])
            if not isinstance(media, list):
                continue
            for item in media:
                if isinstance(item, dict) and item.get("filename"):
                    files.append({
                        "node_id": str(node_id),
                        "kind": key,
                        "filename": str(item.get("filename")),
                        "subfolder": str(item.get("subfolder", "")),
                        "type": str(item.get("type", "output")),
                    })
    return files
