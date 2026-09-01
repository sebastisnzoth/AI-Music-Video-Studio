from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse

from .audio_analysis import analyze_audio
from .director import direct_storyboard
from .pipeline import ROOT, create_project_files, duration, make_storyboard, safe_suffix, save_json

router = APIRouter(prefix="/api")

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
VISUAL_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def _input_dir() -> Path:
    configured = os.getenv("AI_MUSIC_VIDEO_INPUT_DIR", "").strip()
    path = Path(configured).expanduser() if configured else ROOT / "input"
    path = path.resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_input(name: str, allowed_extensions: set[str]) -> Path:
    clean = str(name or "").strip()
    if not clean or Path(clean).name != clean:
        raise HTTPException(400, "Nombre de archivo inválido")
    base = _input_dir()
    path = (base / clean).resolve()
    if path.parent != base:
        raise HTTPException(400, "Ruta fuera de la carpeta input")
    if path.suffix.lower() not in allowed_extensions:
        raise HTTPException(400, "Tipo de archivo no permitido")
    if not path.is_file():
        raise HTTPException(404, f"Archivo local no encontrado: {clean}")
    return path


def _file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "size": stat.st_size,
        "size_mb": round(stat.st_size / 1024 / 1024, 2),
        "modified": stat.st_mtime,
    }


@router.get("/local-inputs")
def local_inputs():
    base = _input_dir()
    files = [p for p in base.iterdir() if p.is_file() and not p.name.startswith(".")]
    audio = [_file_info(p) for p in files if p.suffix.lower() in AUDIO_EXTENSIONS]
    visuals = [_file_info(p) for p in files if p.suffix.lower() in VISUAL_EXTENSIONS]
    audio.sort(key=lambda item: item["modified"], reverse=True)
    visuals.sort(key=lambda item: item["modified"], reverse=True)
    return {
        "ok": True,
        "input_dir": str(base),
        "audio": audio,
        "visuals": visuals,
        "audio_count": len(audio),
        "visual_count": len(visuals),
    }


@router.post("/projects/from-local")
def create_project_from_local(payload: dict = Body(...)):
    song_name = str(payload.get("song_name", "")).strip()
    visual_name = str(payload.get("visual_name", "")).strip()
    title = str(payload.get("title", "Mi videoclip"))
    style = str(payload.get("style", "cinematic rock"))
    aspect = str(payload.get("aspect", "16:9"))
    quality = str(payload.get("quality", "preview"))
    lyrics = str(payload.get("lyrics", ""))

    if aspect not in {"16:9", "9:16"}:
        raise HTTPException(400, "Formato inválido")
    if quality not in {"preview", "final", "master"}:
        raise HTTPException(400, "Calidad inválida")

    source_song = _safe_input(song_name, AUDIO_EXTENSIONS)
    source_visual = _safe_input(visual_name, VISUAL_EXTENSIONS)
    visual_kind = "image" if source_visual.suffix.lower() in IMAGE_EXTENSIONS else "video"

    project_id, project_dir, meta = create_project_files(title, style, aspect, quality, lyrics)
    song_path = project_dir / f"song{safe_suffix(source_song.name, '.mp3')}"
    visual_fallback = ".jpg" if visual_kind == "image" else ".mp4"
    visual_path = project_dir / f"reference{safe_suffix(source_visual.name, visual_fallback)}"

    # Local disk-to-disk copies only. No media bytes travel through Vercel/Cloudflare.
    shutil.copy2(source_song, song_path)
    shutil.copy2(source_visual, visual_path)

    try:
        d = duration(song_path)
        analysis = analyze_audio(song_path)
        analysis.setdefault("duration", round(d, 3))
        meta.update({
            "status": "analyzed",
            "progress": 30,
            "duration": d,
            "analysis": analysis,
            "song": song_path.name,
            "visual": visual_path.name,
            "visual_kind": visual_kind,
            "source_mode": "local_input_folder",
            "source_song": source_song.name,
            "source_visual": source_visual.name,
        })
        meta["storyboard"] = direct_storyboard(make_storyboard(d, lyrics, style, analysis), style)
        meta.update({"status": "storyboard_ready", "progress": 55})
        save_json(project_dir / "project.json", meta)
    except Exception as exc:
        meta.update({"status": "failed", "error": str(exc)})
        save_json(project_dir / "project.json", meta)
        raise HTTPException(500, f"No se pudo procesar: {exc}") from exc

    return JSONResponse({
        "id": project_id,
        "duration": d,
        "analysis": analysis,
        "storyboard": meta["storyboard"],
        "status": meta["status"],
        "progress": meta["progress"],
        "source_mode": meta["source_mode"],
        "input_dir": str(_input_dir()),
        "video_url": None,
        "download_url": None,
    })
