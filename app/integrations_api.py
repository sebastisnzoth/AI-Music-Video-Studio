from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from .integrations import integration_status, queue_localai_video

router = APIRouter(prefix="/api")


@router.get("/integrations")
def integrations():
    return integration_status()


@router.post("/projects/{project_id}/scenes/{scene_id}/generate-video-localai")
def generate_video_localai(project_id: str, scene_id: int, payload: dict = Body(...)):
    model = str(payload.get("model", "")).strip()
    if not model:
        raise HTTPException(400, "model requerido")
    endpoint = str(payload.get("endpoint", "")).strip() or None
    try:
        return queue_localai_video(project_id, scene_id, model=model, endpoint=endpoint)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
