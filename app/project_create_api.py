from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .audio_analysis import analyze_audio
from .director import direct_storyboard
from .pipeline import (
    copy_upload,
    create_project_files,
    duration,
    make_storyboard,
    safe_suffix,
    save_json,
)

router = APIRouter(prefix="/api")


@router.post("/projects/storyboard")
async def create_storyboard_project(
    song: UploadFile = File(...),
    visual: UploadFile = File(...),
    title: str = Form("Mi videoclip"),
    style: str = Form("cinematic rock"),
    aspect: str = Form("16:9"),
    quality: str = Form("preview"),
    lyrics: str = Form(""),
):
    """Upload inputs, analyze audio and create storyboard without blocking on base-video rendering."""
    if aspect not in {"16:9", "9:16"}:
        raise HTTPException(400, "Formato inválido")
    if quality not in {"preview", "final", "master"}:
        raise HTTPException(400, "Calidad inválida")
    if not song.content_type or not song.content_type.startswith("audio/"):
        raise HTTPException(400, "La canción debe ser audio")

    visual_type = visual.content_type or ""
    if visual_type.startswith("image/"):
        visual_kind, visual_fallback = "image", ".jpg"
    elif visual_type.startswith("video/"):
        visual_kind, visual_fallback = "video", ".mp4"
    else:
        raise HTTPException(400, "La referencia debe ser foto o video")

    project_id, project_dir, meta = create_project_files(title, style, aspect, quality, lyrics)
    song_path = project_dir / f"song{safe_suffix(song.filename, '.mp3')}"
    visual_path = project_dir / f"reference{safe_suffix(visual.filename, visual_fallback)}"

    copy_upload(song.file, song_path)
    copy_upload(visual.file, visual_path)

    try:
        d = duration(song_path)
        analysis = analyze_audio(song_path)
        analysis.setdefault("duration", round(d, 3))
        storyboard = direct_storyboard(make_storyboard(d, lyrics, style, analysis), style)
        meta.update(
            {
                "status": "storyboard_ready",
                "progress": 55,
                "duration": d,
                "analysis": analysis,
                "song": song_path.name,
                "visual": visual_path.name,
                "visual_kind": visual_kind,
                "storyboard": storyboard,
            }
        )
        save_json(project_dir / "project.json", meta)
    except Exception as exc:
        meta.update({"status": "failed", "error": str(exc)})
        save_json(project_dir / "project.json", meta)
        raise HTTPException(500, f"No se pudo crear el storyboard: {exc}") from exc

    return JSONResponse(
        {
            "id": project_id,
            "duration": d,
            "analysis": analysis,
            "storyboard": storyboard,
            "status": meta["status"],
            "progress": meta["progress"],
            "upload_mode": "direct",
        }
    )
