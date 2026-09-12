from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .comfyui import ComfyUIError, is_online, list_checkpoints

router = APIRouter(prefix="/api/v1", tags=["worker-contract"])
CONTRACT_VERSION = "1.0"


def _request_id(request: Request) -> str:
    incoming = request.headers.get("x-request-id", "").strip()
    return incoming[:128] if incoming else uuid.uuid4().hex


def _base_payload(request: Request, *, ok: bool = True) -> dict:
    return {
        "ok": ok,
        "version": CONTRACT_VERSION,
        "request_id": _request_id(request),
    }


@router.get("/health")
def health_v1(request: Request):
    comfy_online = is_online()
    return {
        **_base_payload(request),
        "service": "ai-music-video-studio-worker",
        "status": "ready" if comfy_online else "degraded",
        "comfyui": {
            "online": comfy_online,
            "url_configured": bool(os.getenv("COMFYUI_URL", "").strip()),
        },
    }


@router.get("/capabilities")
def capabilities_v1(request: Request):
    return {
        **_base_payload(request),
        "capabilities": {
            "project_persistence": True,
            "storyboard": True,
            "image_generation": True,
            "video_generation": True,
            "scene_review": True,
            "assembly": True,
            "comfyui": True,
            "localai_optional": True,
            "lipsync_optional": True,
            "upscale_optional": True,
        },
        "contract": {
            "project_create": "POST /api/projects",
            "project_get": "GET /api/projects/{id}",
            "scene_generate": "POST /api/projects/{id}/scenes/{scene}/auto-pipeline",
            "scene_status": "GET /api/projects/{id}/scenes/{scene}/auto-pipeline/status",
            "scene_approve": "POST /api/projects/{id}/scenes/{scene}/approve",
            "assemble": "POST /api/projects/{id}/assemble",
        },
    }


@router.get("/comfyui/checkpoints")
def checkpoints_v1(request: Request):
    request_id = _request_id(request)
    try:
        checkpoints = list_checkpoints()
        return {
            "ok": True,
            "version": CONTRACT_VERSION,
            "request_id": request_id,
            "online": True,
            "count": len(checkpoints),
            "checkpoints": checkpoints,
        }
    except ComfyUIError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "version": CONTRACT_VERSION,
                "request_id": request_id,
                "online": False,
                "count": 0,
                "checkpoints": [],
                "error": {
                    "code": "COMFYUI_UNAVAILABLE",
                    "message": str(exc),
                    "retryable": True,
                },
            },
        )
