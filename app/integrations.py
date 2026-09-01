from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import requests

from .pipeline import PROJECTS, load_project, save_json


def _url_online(url: str, timeout: float = 0.8) -> bool:
    try:
        return requests.get(url, timeout=timeout).ok
    except requests.RequestException:
        return False


def integration_status() -> dict[str, Any]:
    localai_base = os.getenv("LOCALAI_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    srs_base = os.getenv("SRS_BASE_URL", "http://127.0.0.1:1985").rstrip("/")
    duix_base = os.getenv("DUIX_VIDEO_URL", "http://127.0.0.1:8383").rstrip("/")
    return {
        "localai": {
            "available": _url_online(f"{localai_base}/v1/models"),
            "base_url": localai_base,
            "video_endpoint": os.getenv("LOCALAI_VIDEO_ENDPOINT"),
            "role": "optional local multimodal/video backend",
        },
        "hyperframes": {
            "available": bool(shutil.which("hyperframes") or shutil.which("npx")),
            "command": shutil.which("hyperframes") or shutil.which("npx"),
            "role": "deterministic motion graphics/captions/compositor",
        },
        "srs": {
            "available": _url_online(f"{srs_base}/api/v1/versions"),
            "base_url": srs_base,
            "role": "optional preview/live streaming server",
        },
        "duix_avatar": {
            "available": _url_online(f"{duix_base}/easy/query?code=healthcheck"),
            "base_url": duix_base,
            "role": "optional NVIDIA digital-human/lipsync backend",
        },
        "pixelle_video": {
            "available": bool(os.getenv("PIXELLE_VIDEO_CMD")),
            "command": os.getenv("PIXELLE_VIDEO_CMD"),
            "role": "optional external modular image-to-video/motion-transfer adapter",
        },
    }


def queue_localai_video(project_id: str, scene_id: int, model: str, endpoint: str | None = None) -> dict[str, Any]:
    """Submit image-to-video to a configured LocalAI-compatible endpoint.

    LocalAI's video backends evolve independently, so the exact endpoint is kept
    configurable via LOCALAI_VIDEO_ENDPOINT. The payload is intentionally small
    and uses the scene package as source of truth.
    """
    meta = load_project(project_id)
    scene = next((x for x in meta.get("storyboard", []) if int(x.get("id", -1)) == scene_id), None)
    if scene is None:
        raise KeyError(scene_id)
    image = scene.get("generated_image")
    if not image:
        raise FileNotFoundError("generated_image is required before image-to-video")

    base = os.getenv("LOCALAI_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    path = endpoint or os.getenv("LOCALAI_VIDEO_ENDPOINT")
    if not path:
        raise RuntimeError("Set LOCALAI_VIDEO_ENDPOINT to your LocalAI video-generation route.")
    url = path if path.startswith("http") else f"{base}/{path.lstrip('/')}"

    request_id = uuid.uuid4().hex[:12]
    payload = {
        "model": model,
        "prompt": scene.get("director_prompt") or scene.get("prompt", ""),
        "image": str(image),
        "duration": float(scene.get("duration", 5.0)),
        "request_id": request_id,
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"LocalAI video request failed: {exc}") from exc

    scene["video_generation_backend"] = "localai"
    scene["video_generation_request"] = data
    scene["status"] = "generating_video"
    save_json(PROJECTS / project_id / "project.json", meta)
    return {"project_id": project_id, "scene_id": scene_id, "backend": "localai", "request": data}
