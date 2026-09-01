from __future__ import annotations

import os
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .comfyui import ComfyUIError, DEFAULT_BASE_URL, get_history, load_workflow, output_files, queue_prompt, render_workflow
from .pipeline import PROJECTS, load_project, save_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIDEO_WORKFLOW = ROOT / "workflows" / "scene-video-api.json"


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    item = next((x for x in meta.get("storyboard", []) if int(x.get("id", -1)) == scene_id), None)
    if item is None:
        raise KeyError(scene_id)
    return item


def _comfy_output_dir() -> Path | None:
    explicit = os.getenv("COMFYUI_OUTPUT_DIR")
    if explicit:
        return Path(explicit).expanduser()
    root = os.getenv("COMFYUI_DIR")
    if root:
        return Path(root).expanduser() / "output"
    conventional = Path.home() / "ComfyUI" / "output"
    return conventional if conventional.exists() else None


def _resolve_comfy_file(item: dict[str, str]) -> Path | None:
    output_dir = _comfy_output_dir()
    if output_dir is None:
        return None
    filename = str(item.get("filename", "")).strip()
    if not filename:
        return None
    subfolder = str(item.get("subfolder", "")).strip()
    candidate = output_dir / subfolder / filename if subfolder else output_dir / filename
    return candidate if candidate.exists() else None


def _import_video_output(project_id: str, scene_id: int, item: dict[str, str]) -> Path | None:
    source = _resolve_comfy_file(item)
    if source is None:
        return None
    scene_dir = PROJECTS / project_id / "scenes" / f"{scene_id:03d}"
    scene_dir.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower() or ".mp4"
    target = scene_dir / f"clip-generated{suffix}"
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target


def _video_dimensions(meta: dict[str, Any]) -> tuple[int, int]:
    aspect = str(meta.get("aspect", "16:9"))
    quality = str(meta.get("quality", "preview"))
    if aspect == "9:16":
        return (432, 768) if quality == "preview" else (576, 1024)
    return (768, 432) if quality == "preview" else (1024, 576)


def _ffmpeg_motion_fallback(project_id: str, scene_id: int, fps: int) -> dict[str, Any]:
    """Create a lightweight cinematic motion clip from the generated image.

    This keeps the full videoclip pipeline usable on CPU-only Macs even when
    an image-to-video ComfyUI workflow/model is not installed.
    """
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    generated_image = Path(str(scene.get("generated_image") or ""))
    if not generated_image.exists():
        raise FileNotFoundError("generated_image is required before video fallback")

    width, height = _video_dimensions(meta)
    duration = max(1.0, float(scene.get("duration", 5.0)))
    actual_fps = max(1, int(fps))
    scene_dir = PROJECTS / project_id / "scenes" / f"{scene_id:03d}"
    scene_dir.mkdir(parents=True, exist_ok=True)
    target = scene_dir / "clip-generated.mp4"

    # Slow Ken Burns-style zoom. It is deterministic, inexpensive and works
    # with the ffmpeg binary already installed by start-worker.sh.
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='min(zoom+0.0008,1.08)':d=1:s={width}x{height}:fps={actual_fps},"
        "format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(generated_image),
        "-vf", vf,
        "-t", f"{duration:.3f}",
        "-r", str(actual_fps),
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(target),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0 or not target.exists():
        raise RuntimeError("FFmpeg video fallback failed: " + proc.stderr[-1400:])

    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    scene["status"] = "clip_ready"
    scene["video_generation_backend"] = "ffmpeg-motion-fallback"
    scene["generated_clip"] = str(target)
    scene["generated_clip_source"] = "ffmpeg-motion-fallback"
    scene["video_generation_settings"] = {
        "fallback": True,
        "fps": actual_fps,
        "duration": duration,
        "width": width,
        "height": height,
    }
    save_json(PROJECTS / project_id / "project.json", meta)
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "backend": "ffmpeg-motion-fallback",
        "status": "clip_ready",
        "generated_clip": str(target),
        "settings": scene["video_generation_settings"],
    }


def queue_scene_video(
    project_id: str,
    scene_id: int,
    workflow_path: Path | None = None,
    base_url: str = DEFAULT_BASE_URL,
    seed: int | None = None,
    fps: int = 24,
) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    generated_image = scene.get("generated_image")
    if not generated_image:
        raise FileNotFoundError("generated_image is required before image-to-video")

    selected_workflow = workflow_path or Path(os.getenv("COMFYUI_VIDEO_WORKFLOW", str(DEFAULT_VIDEO_WORKFLOW)))
    allow_fallback = os.getenv("VIDEO_FALLBACK", "1").strip().lower() not in {"0", "false", "no", "off"}
    if not selected_workflow.exists():
        if allow_fallback:
            return _ffmpeg_motion_fallback(project_id, scene_id, fps)
        raise FileNotFoundError(
            f"Video workflow not found: {selected_workflow}. Export a ComfyUI API workflow and set COMFYUI_VIDEO_WORKFLOW."
        )

    actual_seed = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    duration = max(1.0, float(scene.get("duration", 5.0)))
    frame_count = max(8, int(round(duration * fps)))
    variables = {
        "prompt": scene.get("director_prompt") or scene.get("prompt", ""),
        "negative_prompt": scene.get("negative_prompt", ""),
        "reference_path": str(generated_image),
        "audio_path": str(scene.get("scene_audio") or ""),
        "duration": duration,
        "fps": int(fps),
        "frame_count": frame_count,
        "seed": actual_seed,
        "scene_id": f"{scene_id:03d}",
    }

    try:
        workflow = render_workflow(load_workflow(selected_workflow), variables)
        prompt_id = queue_prompt(workflow, base_url=base_url)
    except (ComfyUIError, FileNotFoundError, ValueError, KeyError):
        if allow_fallback:
            return _ffmpeg_motion_fallback(project_id, scene_id, fps)
        raise

    scene["status"] = "generating_video"
    scene["video_generation_backend"] = "comfyui"
    scene["comfyui_video_prompt_id"] = prompt_id
    scene["video_generation_settings"] = {
        "workflow": str(selected_workflow),
        "seed": actual_seed,
        "fps": int(fps),
        "frame_count": frame_count,
        "duration": duration,
    }
    save_json(PROJECTS / project_id / "project.json", meta)
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "backend": "comfyui",
        "prompt_id": prompt_id,
        "settings": scene["video_generation_settings"],
    }


def refresh_scene_video(project_id: str, scene_id: int, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    prompt_id = scene.get("comfyui_video_prompt_id")
    if not prompt_id:
        return {"project_id": project_id, "scene_id": scene_id, "status": scene.get("status", "planned"), "outputs": []}

    try:
        history = get_history(str(prompt_id), base_url=base_url)
    except ComfyUIError as exc:
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": scene.get("status", "generating_video"),
            "outputs": [],
            "transient": True,
            "transient_error": str(exc),
            "prompt_id": prompt_id,
        }

    if history is None:
        return {"project_id": project_id, "scene_id": scene_id, "status": "generating_video", "outputs": []}

    files = output_files(history)
    video_candidates = [f for f in files if f.get("kind") in {"videos", "gifs"}]
    imported: Path | None = None
    if video_candidates:
        for candidate in video_candidates:
            imported = _import_video_output(project_id, scene_id, candidate)
            if imported is not None:
                break
        scene["status"] = "clip_ready" if imported else "video_ready"
        scene["comfyui_video_outputs"] = video_candidates
        if imported:
            scene["generated_clip"] = str(imported)
            scene["generated_clip_source"] = "comfyui"
    else:
        status_info = history.get("status", {}) if isinstance(history, dict) else {}
        completed = bool(status_info.get("completed", True))
        scene["status"] = "generation_failed" if completed else "generating_video"
        scene["comfyui_video_outputs"] = files

    save_json(PROJECTS / project_id / "project.json", meta)
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "status": scene["status"],
        "outputs": scene.get("comfyui_video_outputs", []),
        "generated_clip": scene.get("generated_clip"),
        "output_dir": str(_comfy_output_dir()) if _comfy_output_dir() else None,
        "prompt_id": prompt_id,
    }
