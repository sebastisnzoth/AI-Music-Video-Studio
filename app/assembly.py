from __future__ import annotations

from pathlib import Path
from typing import Any

from .pipeline import PROJECTS, load_project, run, save_json


def _best_clip(scene: dict[str, Any]) -> Path | None:
    approved = scene.get("approved_asset")
    if approved and Path(str(approved)).exists():
        return Path(str(approved))
    for key in ("upscaled_clip", "lipsync_clip", "generated_clip"):
        value = scene.get(key)
        if value and Path(str(value)).exists():
            return Path(str(value))
    return None


def assemble_generated_video(project_id: str, approved_only: bool = False) -> dict[str, Any]:
    """Assemble generated scene clips while preserving the original song as master audio."""
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    song_name = meta.get("song")
    if not song_name:
        raise FileNotFoundError("song not registered")
    song = project_dir / str(song_name)
    if not song.exists():
        raise FileNotFoundError(song)

    selected: list[tuple[dict[str, Any], Path]] = []
    missing: list[int] = []
    for scene in meta.get("storyboard", []):
        if approved_only and not scene.get("approved"):
            continue
        clip = _best_clip(scene)
        if clip is None:
            missing.append(int(scene.get("id", -1)))
            continue
        selected.append((scene, clip))

    if not selected:
        raise RuntimeError("No generated scene clips are available to assemble")

    concat_file = project_dir / "generated-scenes.txt"
    lines = []
    for _, clip in selected:
        escaped = str(clip.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    silent_video = project_dir / "generated-video-silent.mp4"
    output = project_dir / "final-ai.mp4"

    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        str(silent_video),
    ])
    run([
        "ffmpeg", "-y", "-i", str(silent_video), "-i", str(song),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
        "-shortest", str(output),
    ])

    meta["ai_output"] = output.name
    meta["ai_assembly"] = {
        "scene_count": len(selected),
        "missing_scene_ids": missing,
        "approved_only": approved_only,
        "selection_policy": "approved_asset > upscaled > lipsync > generated",
    }
    save_json(project_dir / "project.json", meta)
    return {
        "project_id": project_id,
        "output": str(output),
        "scene_count": len(selected),
        "missing_scene_ids": missing,
    }
