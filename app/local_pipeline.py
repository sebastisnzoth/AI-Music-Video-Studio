from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .pipeline import PROJECTS, load_project, save_json


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    scene = next((row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id), None)
    if scene is None:
        raise KeyError(scene_id)
    return scene


def detect_local_tools() -> dict[str, Any]:
    """Detect optional local post-processing tools without requiring them."""
    wav2lip = os.getenv("WAV2LIP_CMD") or shutil.which("wav2lip")
    realesrgan = os.getenv("REALESRGAN_CMD") or shutil.which("realesrgan-ncnn-vulkan") or shutil.which("realesrgan")
    ffmpeg = shutil.which("ffmpeg")
    return {
        "ffmpeg": {"available": bool(ffmpeg), "command": ffmpeg},
        "wav2lip": {"available": bool(wav2lip), "command": wav2lip},
        "real_esrgan": {"available": bool(realesrgan), "command": realesrgan},
    }


def register_generated_image(project_id: str, scene_id: int, image_path: str) -> dict[str, Any]:
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = _scene(meta, scene_id)
    path = Path(image_path)
    scene["generated_image"] = str(path)
    scene["status"] = "image_ready"
    save_json(project_dir / "project.json", meta)
    return scene


def register_generated_clip(project_id: str, scene_id: int, clip_path: str) -> dict[str, Any]:
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = _scene(meta, scene_id)
    path = Path(clip_path)
    scene["generated_clip"] = str(path)
    scene["status"] = "clip_ready"
    save_json(project_dir / "project.json", meta)
    return scene


def run_wav2lip(project_id: str, scene_id: int, command: str | None = None) -> dict[str, Any]:
    """Run a configurable local Wav2Lip wrapper.

    The command must accept: --face <video> --audio <wav> --outfile <mp4>.
    This keeps the app compatible with different local Wav2Lip installs/forks.
    """
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = _scene(meta, scene_id)
    if not scene.get("needs_lipsync"):
        return {"skipped": True, "reason": "scene does not require lip-sync", "scene_id": scene_id}

    face = scene.get("generated_clip")
    audio = scene.get("scene_audio")
    if not face or not Path(str(face)).exists():
        raise FileNotFoundError("generated clip not available")
    if not audio or not Path(str(audio)).exists():
        raise FileNotFoundError("scene audio not available")

    cmd = command or os.getenv("WAV2LIP_CMD") or shutil.which("wav2lip")
    if not cmd:
        raise RuntimeError("Wav2Lip command not configured. Set WAV2LIP_CMD.")

    out = project_dir / "scenes" / f"{scene_id:03d}" / "clip-lipsync.mp4"
    proc = subprocess.run([cmd, "--face", str(face), "--audio", str(audio), "--outfile", str(out)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Wav2Lip failed")

    scene["lipsync_clip"] = str(out)
    scene["status"] = "lipsync_ready"
    save_json(project_dir / "project.json", meta)
    return {"scene_id": scene_id, "status": scene["status"], "output": str(out)}


def run_upscale(project_id: str, scene_id: int, command: str | None = None, scale: int = 2) -> dict[str, Any]:
    """Upscale the best available scene clip with a configurable Real-ESRGAN CLI."""
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = _scene(meta, scene_id)
    source = scene.get("lipsync_clip") or scene.get("generated_clip")
    if not source or not Path(str(source)).exists():
        raise FileNotFoundError("scene clip not available")

    cmd = command or os.getenv("REALESRGAN_CMD") or shutil.which("realesrgan-ncnn-vulkan") or shutil.which("realesrgan")
    if not cmd:
        raise RuntimeError("Real-ESRGAN command not configured. Set REALESRGAN_CMD.")

    out = project_dir / "scenes" / f"{scene_id:03d}" / "clip-upscaled.mp4"
    # CLI wrappers vary; this convention is intentionally simple and configurable.
    proc = subprocess.run([cmd, "-i", str(source), "-o", str(out), "-s", str(scale)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Real-ESRGAN failed")

    scene["upscaled_clip"] = str(out)
    scene["status"] = "upscale_ready"
    save_json(project_dir / "project.json", meta)
    return {"scene_id": scene_id, "status": scene["status"], "output": str(out)}


def scene_pipeline_status(project_id: str, scene_id: int) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    return {
        "scene_id": scene_id,
        "status": scene.get("status", "planned"),
        "needs_lipsync": bool(scene.get("needs_lipsync")),
        "generated_image": scene.get("generated_image"),
        "generated_clip": scene.get("generated_clip"),
        "lipsync_clip": scene.get("lipsync_clip"),
        "upscaled_clip": scene.get("upscaled_clip"),
        "toolchain": scene.get("toolchain", {}),
    }
