from __future__ import annotations

import os
import random
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

from .pipeline import PROJECTS, load_project, save_json

DEFAULT_SPACE = os.getenv(
    "HF_VIDEO_SPACE",
    "Saravutw/WAN2.2_I2V_LIGHTNING_4-8step_custom",
).strip()
DEFAULT_API_NAME = os.getenv("HF_VIDEO_API_NAME", "/generate_video").strip() or "/generate_video"
DEFAULT_NEGATIVE = (
    "blurry, low quality, chaotic, deformed, watermark, bad anatomy, "
    "shaky camera, text, subtitles, duplicate person, distorted face"
)

# Gradio jobs are intentionally kept in memory. A worker restart only loses the
# handle for jobs that were still running; completed scene files remain on disk.
_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    scene = next(
        (row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id),
        None,
    )
    if scene is None:
        raise KeyError(scene_id)
    return scene


def external_video_status() -> dict[str, Any]:
    enabled = os.getenv("HF_VIDEO_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
    try:
        import gradio_client  # noqa: F401

        client_installed = True
        error = None
    except Exception as exc:  # pragma: no cover - depends on local environment
        client_installed = False
        error = str(exc)
    return {
        "id": "wan22-hf",
        "name": "WAN 2.2 externo · Hugging Face ZeroGPU",
        "enabled": enabled,
        "client_installed": client_installed,
        "available": bool(enabled and client_installed and DEFAULT_SPACE),
        "space": DEFAULT_SPACE,
        "api_name": DEFAULT_API_NAME,
        "authenticated": bool(os.getenv("HF_TOKEN", "").strip()),
        "error": error,
    }


def _extract_path(value: Any) -> Path | None:
    """Find a downloaded file path inside Gradio's possible return shapes."""
    if value is None:
        return None
    if isinstance(value, Path):
        return value if value.exists() else None
    if isinstance(value, str):
        path = Path(value)
        return path if path.exists() else None
    if isinstance(value, dict):
        # FileData is commonly materialized as a dict-like object.
        for key in ("path", "name"):
            candidate = value.get(key)
            if isinstance(candidate, str) and Path(candidate).exists():
                return Path(candidate)
        # Prefer the downloadable file output over video metadata when both exist.
        for key in ("file", "video", "value", "data"):
            if key in value:
                found = _extract_path(value[key])
                if found:
                    return found
        for candidate in value.values():
            found = _extract_path(candidate)
            if found:
                return found
        return None
    if isinstance(value, (list, tuple)):
        # The selected WAN Space returns (video_component, file_output, seed).
        preferred = list(value[1:2]) + list(value[:1]) + list(value[2:])
        for candidate in preferred:
            found = _extract_path(candidate)
            if found:
                return found
    return None


def _probe_duration(path: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        return 0.0
    try:
        return max(0.0, float(proc.stdout.strip()))
    except ValueError:
        return 0.0


def _fit_clip_duration(source: Path, target: Path, duration: float, fps: int) -> None:
    """Fit the short WAN result to the exact storyboard scene duration."""
    source_duration = _probe_duration(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source_duration <= 0.05 or abs(source_duration - duration) < 0.08:
        shutil.copy2(source, target)
        return

    ratio = duration / source_duration
    vf = f"setpts={ratio:.8f}*PTS,fps={max(1, int(fps))},format=yuv420p"
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-an",
            "-vf",
            vf,
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            str(target),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0 or not target.exists():
        raise RuntimeError("No se pudo ajustar la duración del video externo: " + proc.stderr[-1200:])


def queue_wan22_scene_video(
    project_id: str,
    scene_id: int,
    *,
    fps: int = 24,
    duration_limit: float = 4.0,
    steps: int = 4,
) -> dict[str, Any]:
    status = external_video_status()
    if not status["available"]:
        raise RuntimeError(status.get("error") or "Motor WAN 2.2 externo no disponible")

    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    generated_image = Path(str(scene.get("generated_image") or ""))
    if not generated_image.exists():
        raise FileNotFoundError("generated_image is required before external image-to-video")

    try:
        from gradio_client import Client, handle_file
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"gradio_client no disponible: {exc}") from exc

    scene_duration = max(1.0, float(scene.get("duration", 5.0)))
    request_duration = min(scene_duration, max(1.0, float(duration_limit)))
    actual_seed = random.randint(1, 2**31 - 1)
    prompt = str(scene.get("director_prompt") or scene.get("prompt") or "").strip()
    if not prompt:
        prompt = "cinematic music video, natural motion, smooth camera movement, consistent face"

    token = os.getenv("HF_TOKEN", "").strip() or None
    client_kwargs: dict[str, Any] = {"verbose": False}
    if token:
        client_kwargs["hf_token"] = token

    # Client construction reads the Space schema; submit returns immediately with
    # a queue-aware Job object rather than holding our FastAPI request open.
    client = Client(DEFAULT_SPACE, **client_kwargs)
    job = client.submit(
        input_image=handle_file(str(generated_image)),
        last_image=None,
        prompt=prompt,
        steps=max(1, min(8, int(steps))),
        negative_prompt=str(scene.get("negative_prompt") or DEFAULT_NEGATIVE),
        duration_seconds=request_duration,
        guidance_scale=1.0,
        guidance_scale_2=1.0,
        seed=actual_seed,
        randomize_seed=False,
        quality=5,
        scheduler="UniPCMultistep",
        flow_shift=3.0,
        frame_multiplier=16,
        safe_mode=True,
        video_component=False,
        api_name=DEFAULT_API_NAME,
    )

    task_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[task_id] = {
            "client": client,
            "job": job,
            "project_id": project_id,
            "scene_id": scene_id,
            "duration": scene_duration,
            "fps": max(1, int(fps)),
        }

    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    scene["status"] = "generating_external_video"
    scene["video_generation_backend"] = "huggingface-wan22"
    scene["external_video_task_id"] = task_id
    scene["video_generation_settings"] = {
        "provider": "huggingface",
        "space": DEFAULT_SPACE,
        "api_name": DEFAULT_API_NAME,
        "seed": actual_seed,
        "steps": max(1, min(8, int(steps))),
        "requested_duration": request_duration,
        "scene_duration": scene_duration,
        "fps": max(1, int(fps)),
        "safe_mode": True,
    }
    save_json(PROJECTS / project_id / "project.json", meta)
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "backend": "huggingface-wan22",
        "task_id": task_id,
        "status": "generating_external_video",
        "settings": scene["video_generation_settings"],
    }


def refresh_wan22_scene_video(project_id: str, scene_id: int) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    task_id = str(scene.get("external_video_task_id") or "")
    if not task_id:
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": "generation_failed",
            "error": "No hay tarea externa asociada a esta escena",
        }

    with _jobs_lock:
        record = _jobs.get(task_id)
    if record is None:
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": "generation_failed",
            "error": "La tarea externa se perdió al reiniciar el worker",
            "task_id": task_id,
        }

    job = record["job"]
    if not job.done():
        queue_rank = None
        queue_size = None
        status_code = "queued"
        try:
            info = job.status()
            queue_rank = getattr(info, "rank", None)
            queue_size = getattr(info, "queue_size", None)
            code = getattr(info, "code", None)
            status_code = str(getattr(code, "name", code) or "queued").lower()
        except Exception:
            pass
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": "generating_external_video",
            "backend": "huggingface-wan22",
            "task_id": task_id,
            "queue_rank": queue_rank,
            "queue_size": queue_size,
            "provider_status": status_code,
        }

    try:
        result = job.result()
        source = _extract_path(result)
        if source is None or not source.exists():
            raise RuntimeError(f"WAN 2.2 terminó sin devolver un MP4 utilizable: {result!r}")

        scene_dir = PROJECTS / project_id / "scenes" / f"{scene_id:03d}"
        target = scene_dir / "clip-generated-wan22.mp4"
        _fit_clip_duration(
            source,
            target,
            float(record["duration"]),
            int(record["fps"]),
        )

        meta = load_project(project_id)
        scene = _scene(meta, scene_id)
        scene["status"] = "clip_ready"
        scene["video_generation_backend"] = "huggingface-wan22"
        scene["generated_clip"] = str(target)
        scene["generated_clip_source"] = "huggingface-wan22"
        scene.pop("external_video_error", None)
        save_json(PROJECTS / project_id / "project.json", meta)

        with _jobs_lock:
            _jobs.pop(task_id, None)
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": "clip_ready",
            "backend": "huggingface-wan22",
            "generated_clip": str(target),
            "task_id": task_id,
        }
    except Exception as exc:
        meta = load_project(project_id)
        scene = _scene(meta, scene_id)
        scene["status"] = "generation_failed"
        scene["external_video_error"] = str(exc)
        save_json(PROJECTS / project_id / "project.json", meta)
        with _jobs_lock:
            _jobs.pop(task_id, None)
        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": "generation_failed",
            "backend": "huggingface-wan22",
            "task_id": task_id,
            "error": str(exc),
        }
