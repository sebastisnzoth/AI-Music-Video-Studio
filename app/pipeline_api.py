from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from .assembly import assemble_generated_video
from .identity import build_identity_profile
from .local_pipeline import detect_local_tools, run_upscale, run_wav2lip, scene_pipeline_status
from .pipeline import PROJECTS

router = APIRouter(prefix="/api")


@router.get("/local-tools")
def local_tools():
    return detect_local_tools()


@router.post("/projects/{project_id}/identity")
def create_identity(project_id: str, payload: dict = Body(default={})):
    try:
        return build_identity_profile(project_id, description=str(payload.get("description", "")))
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/projects/{project_id}/scenes/{scene_id}/pipeline-status")
def pipeline_status(project_id: str, scene_id: int):
    try:
        return scene_pipeline_status(project_id, scene_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/scenes/{scene_id}/lipsync")
def lipsync(project_id: str, scene_id: int):
    try:
        return run_wav2lip(project_id, scene_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/projects/{project_id}/scenes/{scene_id}/upscale")
def upscale(project_id: str, scene_id: int, payload: dict = Body(default={})):
    try:
        return run_upscale(project_id, scene_id, scale=int(payload.get("scale", 2)))
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/projects/{project_id}/assemble-ai")
def assemble_ai(project_id: str, payload: dict = Body(default={})):
    try:
        result = assemble_generated_video(project_id, approved_only=bool(payload.get("approved_only", False)))
        result["download_url"] = f"/api/projects/{project_id}/download-ai"
        return result
    except (FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/projects/{project_id}/download-ai")
def download_ai(project_id: str):
    path = PROJECTS / project_id / "final-ai.mp4"
    if not path.exists():
        raise HTTPException(404, "AI master not available")
    return FileResponse(path, media_type="video/mp4", filename=f"{project_id}-ai-music-video.mp4")
