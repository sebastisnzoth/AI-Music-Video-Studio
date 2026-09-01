from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .pipeline import PROJECTS, load_project, run, save_json


def _find_song(project_dir: Path, meta: dict[str, Any]) -> Path:
    name = meta.get("song")
    if not name:
        raise FileNotFoundError("song not registered")
    path = project_dir / str(name)
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def prepare_scene_package(project_id: str, scene_id: int) -> dict[str, Any]:
    """Create the deterministic local inputs needed by an AI video backend.

    Each package contains the exact song slice, prompt data, identity reference,
    timing and lip-sync flag. No cloud API is required.
    """
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = next((row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id), None)
    if scene is None:
        raise KeyError(scene_id)

    song = _find_song(project_dir, meta)
    visual_name = meta.get("visual")
    visual = project_dir / str(visual_name) if visual_name else None
    scene_dir = project_dir / "scenes" / f"{scene_id:03d}"
    scene_dir.mkdir(parents=True, exist_ok=True)

    start = float(scene.get("start", 0.0))
    length = max(0.1, float(scene.get("duration", float(scene.get("end", 0.0)) - start)))
    audio_out = scene_dir / "audio.wav"
    run([
        "ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", str(song),
        "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(audio_out),
    ])

    package = {
        "project_id": project_id,
        "scene_id": scene_id,
        "start": round(start, 3),
        "end": round(float(scene.get("end", start + length)), 3),
        "duration": round(length, 3),
        "section": scene.get("section", "scene"),
        "strategy": scene.get("strategy", "narrative"),
        "needs_lipsync": bool(scene.get("needs_lipsync", False)),
        "energy_band": scene.get("energy_band", scene.get("energy", "medium")),
        "lyrics": scene.get("lyrics", ""),
        "prompt": scene.get("director_prompt") or scene.get("prompt", ""),
        "negative_prompt": scene.get("negative_prompt", ""),
        "camera": scene.get("camera", ""),
        "palette": scene.get("palette", ""),
        "lighting": scene.get("lighting", ""),
        "audio_path": str(audio_out),
        "reference_path": str(visual) if visual and visual.exists() else None,
        "output_path": str(scene_dir / "clip.mp4"),
        "status": "prepared",
    }
    (scene_dir / "package.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")

    scene["scene_package"] = str(scene_dir / "package.json")
    scene["scene_audio"] = str(audio_out)
    scene["status"] = "prepared"
    save_json(project_dir / "project.json", meta)
    return package


def prepare_all_scenes(project_id: str) -> list[dict[str, Any]]:
    meta = load_project(project_id)
    return [prepare_scene_package(project_id, int(scene["id"])) for scene in meta.get("storyboard", [])]
