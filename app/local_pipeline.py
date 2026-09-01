from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .pipeline import PROJECTS, load_project, save_json


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    scene = next((row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id), None)
    if scene is None:
        raise KeyError(scene_id)
    return scene


def _deep_live_cam_install() -> tuple[Path | None, Path | None]:
    raw = os.getenv("DEEP_LIVE_CAM_DIR", "").strip()
    candidates = [
        Path(raw).expanduser() if raw else None,
        Path.home() / "Deep-Live-Cam",
        Path.home() / "deep-live-cam",
    ]
    for root in candidates:
        if root and (root / "run.py").exists():
            return root, root / "run.py"
    return None, None


def detect_local_tools() -> dict[str, Any]:
    """Detect optional local post-processing tools without requiring them."""
    wav2lip = os.getenv("WAV2LIP_CMD") or shutil.which("wav2lip")
    realesrgan = os.getenv("REALESRGAN_CMD") or shutil.which("realesrgan-ncnn-vulkan") or shutil.which("realesrgan")
    ffmpeg = shutil.which("ffmpeg")
    dlc_root, dlc_run = _deep_live_cam_install()
    return {
        "ffmpeg": {"available": bool(ffmpeg), "command": ffmpeg},
        "wav2lip": {"available": bool(wav2lip), "command": wav2lip},
        "real_esrgan": {"available": bool(realesrgan), "command": realesrgan},
        "deep_live_cam": {
            "available": bool(dlc_run),
            "root": str(dlc_root) if dlc_root else None,
            "command": str(dlc_run) if dlc_run else None,
            "execution_provider": os.getenv("DEEP_LIVE_CAM_PROVIDER", "cpu"),
        },
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


def run_deep_live_cam(
    project_id: str,
    scene_id: int,
    execution_provider: str | None = None,
    mouth_mask: bool = True,
    enhance_face: bool = True,
) -> dict[str, Any]:
    """Refine artist identity on a generated clip using a local Deep-Live-Cam install.

    Configure DEEP_LIVE_CAM_DIR to the cloned Deep-Live-Cam directory. The source
    face is the project's uploaded reference image. This stage is optional and
    should only be used with faces the user is authorized to use.
    """
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = _scene(meta, scene_id)

    source_name = meta.get("visual")
    if meta.get("visual_kind") != "image" or not source_name:
        raise RuntimeError("Deep-Live-Cam identity refinement requires an uploaded reference image")
    source = project_dir / str(source_name)
    target_value = scene.get("generated_clip")
    if not source.exists():
        raise FileNotFoundError(source)
    if not target_value or not Path(str(target_value)).exists():
        raise FileNotFoundError("generated clip not available")
    target = Path(str(target_value))

    root, run_py = _deep_live_cam_install()
    if not root or not run_py:
        raise RuntimeError("Deep-Live-Cam not configured. Set DEEP_LIVE_CAM_DIR to its local clone.")

    provider = (execution_provider or os.getenv("DEEP_LIVE_CAM_PROVIDER") or "cpu").strip().lower()
    python_cmd = os.getenv("DEEP_LIVE_CAM_PYTHON", "").strip() or sys.executable
    out = project_dir / "scenes" / f"{scene_id:03d}" / "clip-face-refined.mp4"
    processors = ["face_swapper"]
    if enhance_face:
        processors.append("face_enhancer")

    args = [
        python_cmd,
        str(run_py),
        "-s", str(source),
        "-t", str(target),
        "-o", str(out),
        "--frame-processor", *processors,
        "--keep-fps",
        "--keep-audio",
        "--execution-provider", provider,
    ]
    if mouth_mask:
        args.append("--mouth-mask")

    proc = subprocess.run(args, cwd=str(root), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "Deep-Live-Cam failed")
    if not out.exists():
        raise RuntimeError("Deep-Live-Cam completed but output file was not found")

    scene["face_refined_clip"] = str(out)
    scene["face_refinement"] = {
        "backend": "deep-live-cam",
        "execution_provider": provider,
        "mouth_mask": bool(mouth_mask),
        "face_enhancer": bool(enhance_face),
    }
    scene["status"] = "face_refined"
    save_json(project_dir / "project.json", meta)
    return {"scene_id": scene_id, "status": scene["status"], "output": str(out), "settings": scene["face_refinement"]}


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

    face = scene.get("face_refined_clip") or scene.get("generated_clip")
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
    source = scene.get("lipsync_clip") or scene.get("face_refined_clip") or scene.get("generated_clip")
    if not source or not Path(str(source)).exists():
        raise FileNotFoundError("scene clip not available")

    cmd = command or os.getenv("REALESRGAN_CMD") or shutil.which("realesrgan-ncnn-vulkan") or shutil.which("realesrgan")
    if not cmd:
        raise RuntimeError("Real-ESRGAN command not configured. Set REALESRGAN_CMD.")

    out = project_dir / "scenes" / f"{scene_id:03d}" / "clip-upscaled.mp4"
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
        "face_refined_clip": scene.get("face_refined_clip"),
        "lipsync_clip": scene.get("lipsync_clip"),
        "upscaled_clip": scene.get("upscaled_clip"),
        "toolchain": scene.get("toolchain", {}),
    }
