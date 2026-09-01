from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from .assembly import assemble_generated_video
from .batch import generation_queue, prepare_batch
from .captions import build_lyrics_srt, burn_subtitles
from .identity import build_identity_profile
from .local_pipeline import detect_local_tools, run_deep_live_cam, run_upscale, run_wav2lip, scene_pipeline_status
from .orchestrator import advance_scene_pipeline, auto_pipeline_status
from .pipeline import PROJECTS
from .review import add_review_comment, add_scene_version, approve_version, review_summary

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


@router.post("/projects/{project_id}/scenes/{scene_id}/auto-pipeline")
def auto_pipeline(project_id: str, scene_id: int, payload: dict = Body(default={})):
    try:
        return advance_scene_pipeline(
            project_id,
            scene_id,
            checkpoint=str(payload.get("checkpoint", "") or "").strip() or None,
            image_steps=int(payload.get("image_steps", 24)),
            image_cfg=float(payload.get("image_cfg", 6.0)),
            fps=int(payload.get("fps", 24)),
            use_face_refine=bool(payload.get("use_face_refine", True)),
            mouth_mask=bool(payload.get("mouth_mask", True)),
            enhance_face=bool(payload.get("enhance_face", True)),
            execution_provider=str(payload.get("execution_provider", "") or "") or None,
            use_lipsync=bool(payload.get("use_lipsync", True)),
            use_upscale=bool(payload.get("use_upscale", True)),
            upscale_scale=int(payload.get("upscale_scale", 2)),
            strict_optional=bool(payload.get("strict_optional", False)),
        )
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/projects/{project_id}/scenes/{scene_id}/auto-pipeline/status")
def auto_pipeline_get_status(project_id: str, scene_id: int):
    try:
        return auto_pipeline_status(project_id, scene_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/scenes/{scene_id}/face-refine")
def face_refine(project_id: str, scene_id: int, payload: dict = Body(default={})):
    try:
        return run_deep_live_cam(
            project_id,
            scene_id,
            execution_provider=str(payload.get("execution_provider", "") or "") or None,
            mouth_mask=bool(payload.get("mouth_mask", True)),
            enhance_face=bool(payload.get("enhance_face", True)),
        )
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


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


@router.post("/projects/{project_id}/scenes/{scene_id}/versions")
def register_scene_version(project_id: str, scene_id: int, payload: dict = Body(...)):
    file_path = str(payload.get("file", "")).strip()
    stage = str(payload.get("stage", "generated")).strip() or "generated"
    if not file_path:
        raise HTTPException(400, "file requerido")
    try:
        return add_scene_version(project_id, scene_id, file_path=file_path, stage=stage, note=str(payload.get("note", "")))
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/scenes/{scene_id}/comments")
def review_comment(project_id: str, scene_id: int, payload: dict = Body(...)):
    text = str(payload.get("text", "")).strip()
    if not text:
        raise HTTPException(400, "text requerido")
    try:
        return add_review_comment(project_id, scene_id, text=text, timestamp=payload.get("timestamp"))
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/scenes/{scene_id}/versions/{version_id}/approve")
def approve_scene_version(project_id: str, scene_id: int, version_id: int):
    try:
        return approve_version(project_id, scene_id, version_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/projects/{project_id}/review")
def project_review(project_id: str):
    try:
        return review_summary(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/batch/prepare")
def batch_prepare(project_id: str, payload: dict = Body(default={})):
    try:
        return prepare_batch(project_id, only_unprepared=bool(payload.get("only_unprepared", True)))
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/projects/{project_id}/batch/queue")
def batch_queue(project_id: str):
    try:
        return generation_queue(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/captions/srt")
def captions_srt(project_id: str):
    try:
        return build_lyrics_srt(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/projects/{project_id}/captions/burn")
def captions_burn(project_id: str, payload: dict = Body(default={})):
    try:
        return burn_subtitles(project_id, source_name=str(payload.get("source_name", "final-ai.mp4")))
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc


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


@router.get("/projects/{project_id}/download-subtitled")
def download_subtitled(project_id: str):
    path = PROJECTS / project_id / "final-subtitled.mp4"
    if not path.exists():
        raise HTTPException(404, "Subtitled master not available")
    return FileResponse(path, media_type="video/mp4", filename=f"{project_id}-subtitled.mp4")
