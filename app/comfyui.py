from __future__ import annotations

import copy
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")


class ComfyUIError(RuntimeError):
    pass


def is_online(base_url: str = DEFAULT_BASE_URL, timeout: float = 1.0) -> bool:
    try:
        return requests.get(f"{base_url.rstrip('/')}/system_stats", timeout=timeout).ok
    except requests.RequestException:
        return False


def get_queue(base_url: str = DEFAULT_BASE_URL, timeout: float = 4.0) -> dict[str, Any]:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/queue", timeout=timeout)
    except requests.RequestException as exc:
        raise ComfyUIError(f"No se pudo consultar la cola de ComfyUI: {exc}") from exc
    if not response.ok:
        raise ComfyUIError(f"Error consultando cola de ComfyUI ({response.status_code})")
    data = response.json()
    return data if isinstance(data, dict) else {}


def prompt_is_active(prompt_id: str, base_url: str = DEFAULT_BASE_URL, timeout: float = 4.0) -> bool:
    """Return True when a prompt is currently running or pending in ComfyUI."""
    target = str(prompt_id)
    queue = get_queue(base_url=base_url, timeout=timeout)
    for key in ("queue_running", "queue_pending"):
        rows = queue.get(key, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, list) and len(row) > 1 and str(row[1]) == target:
                return True
    return False


def _checkpoint_names_from_object_info(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    node = payload.get("CheckpointLoaderSimple", payload)
    if not isinstance(node, dict):
        return []
    required = node.get("input", {}).get("required", {})
    if not isinstance(required, dict):
        return []
    spec = required.get("ckpt_name")
    if not isinstance(spec, list) or not spec:
        return []
    values = spec[0] if isinstance(spec[0], list) else spec
    return sorted({str(value) for value in values if isinstance(value, str) and value.strip()})


def list_checkpoints(base_url: str = DEFAULT_BASE_URL, timeout: float = 4.0) -> list[str]:
    """Return checkpoint names exactly as ComfyUI exposes them."""
    base = base_url.rstrip("/")
    errors: list[str] = []

    try:
        response = requests.get(f"{base}/object_info/CheckpointLoaderSimple", timeout=timeout)
        if response.ok:
            names = _checkpoint_names_from_object_info(response.json())
            if names:
                return names
        else:
            errors.append(f"object_info HTTP {response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        errors.append(f"object_info: {exc}")

    try:
        response = requests.get(f"{base}/models/checkpoints", timeout=timeout)
        if response.ok:
            data = response.json()
            if isinstance(data, list):
                return sorted({str(value) for value in data if isinstance(value, str) and value.strip()})
            if isinstance(data, dict):
                values = data.get("models") or data.get("checkpoints") or data.get("items") or []
                if isinstance(values, list):
                    return sorted({str(value) for value in values if isinstance(value, str) and value.strip()})
        else:
            errors.append(f"models HTTP {response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        errors.append(f"models: {exc}")

    if not is_online(base_url=base, timeout=min(timeout, 1.5)):
        raise ComfyUIError("ComfyUI no está accesible")
    if errors:
        raise ComfyUIError("No se pudo leer la lista de checkpoints: " + " | ".join(errors))
    return []


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
