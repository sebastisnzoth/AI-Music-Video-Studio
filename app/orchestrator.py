from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .generation_service import queue_scene_image, refresh_scene_generation
from .local_pipeline import detect_local_tools, run_deep_live_cam, run_upscale, run_wav2lip
from .pipeline import PROJECTS, load_project, save_json
from .scene_package import prepare_scene_package
from .video_generation import queue_scene_video, refresh_scene_video


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scene(meta: dict[str, Any], scene_id: int) -> dict[str, Any]:
    scene = next((row for row in meta.get("storyboard", []) if int(row.get("id", -1)) == scene_id), None)
    if scene is None:
        raise KeyError(scene_id)
    return scene


def _exists(value: Any) -> bool:
    return bool(value) and Path(str(value)).exists()


def _log(scene: dict[str, Any], stage: str, status: str, detail: str = "") -> None:
    scene.setdefault("auto_pipeline_log", []).append({
        "at": _now(),
        "stage": stage,
        "status": status,
        "detail": detail,
    })
    scene["auto_pipeline_log"] = scene["auto_pipeline_log"][-80:]


def _best_clip(scene: dict[str, Any]) -> str | None:
    for key in ("upscaled_clip", "lipsync_clip", "face_refined_clip", "generated_clip"):
        value = scene.get(key)
        if _exists(value):
            return str(value)
    return None


def _ensure_review_version(scene: dict[str, Any], file_path: str, stage: str) -> int:
    versions = scene.setdefault("versions", [])
    for item in versions:
        if str(item.get("file")) == file_path:
            return int(item.get("id", 0))
    version_id = max([int(v.get("id", 0)) for v in versions] or [0]) + 1
    versions.append({
        "id": version_id,
        "file": file_path,
        "stage": stage,
        "note": "Creada automáticamente por Auto Pipeline",
        "created_at": _now(),
        "approved": False,
    })
    return version_id


def auto_pipeline_status(project_id: str, scene_id: int) -> dict[str, Any]:
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    return {
        "project_id": project_id,
        "scene_id": scene_id,
        "status": scene.get("status", "planned"),
        "auto_state": scene.get("auto_pipeline_state", "idle"),
        "generated_image": scene.get("generated_image"),
        "generated_clip": scene.get("generated_clip"),
        "face_refined_clip": scene.get("face_refined_clip"),
        "lipsync_clip": scene.get("lipsync_clip"),
        "upscaled_clip": scene.get("upscaled_clip"),
        "review_candidate": scene.get("review_candidate"),
        "review_version": scene.get("review_version"),
        "last_error": scene.get("auto_pipeline_error"),
        "log": scene.get("auto_pipeline_log", [])[-12:],
    }


def advance_scene_pipeline(
    project_id: str,
    scene_id: int,
    *,
    checkpoint: str | None = None,
    image_steps: int = 24,
    image_cfg: float = 6.0,
    fps: int = 24,
    use_face_refine: bool = True,
    mouth_mask: bool = True,
    enhance_face: bool = True,
    execution_provider: str | None = None,
    use_lipsync: bool = True,
    use_upscale: bool = True,
    upscale_scale: int = 2,
    strict_optional: bool = False,
) -> dict[str, Any]:
    """Advance one scene through a resumable local image-to-review pipeline."""
    meta = load_project(project_id)
    project_dir = PROJECTS / project_id
    scene = _scene(meta, scene_id)

    if not scene.get("scene_audio") or not _exists(scene.get("scene_audio")):
        prepare_scene_package(project_id, scene_id)
        meta = load_project(project_id)
        scene = _scene(meta, scene_id)
        _log(scene, "prepare", "done", "Audio y package preparados")
        save_json(project_dir / "project.json", meta)

    # 0) Generate/import the scene image when needed.
    if not _exists(scene.get("generated_image")):
        image_prompt_id = scene.get("comfyui_prompt_id")
        if image_prompt_id:
            refreshed_image = refresh_scene_generation(project_id, scene_id)
            meta = load_project(project_id)
            scene = _scene(meta, scene_id)
            if not _exists(scene.get("generated_image")):
                if refreshed_image.get("status") == "generation_failed":
                    scene["auto_pipeline_state"] = "failed"
                    scene["auto_pipeline_error"] = "ComfyUI terminó sin producir una imagen utilizable."
                    _log(scene, "image", "failed", scene["auto_pipeline_error"])
                else:
                    scene["auto_pipeline_state"] = "waiting_image"
                    _log(scene, "image", "waiting", "ComfyUI sigue generando/importando la imagen")
                save_json(project_dir / "project.json", meta)
                return auto_pipeline_status(project_id, scene_id)
            _log(scene, "image", "done", str(scene.get("generated_image")))
            save_json(project_dir / "project.json", meta)
        elif checkpoint:
            queued_image = queue_scene_image(
                project_id,
                scene_id,
                checkpoint=checkpoint,
                steps=max(1, int(image_steps)),
                cfg=float(image_cfg),
            )
            meta = load_project(project_id)
            scene = _scene(meta, scene_id)
            scene["auto_pipeline_state"] = "waiting_image"
            scene.pop("auto_pipeline_error", None)
            _log(scene, "image", "queued", f"ComfyUI prompt {queued_image.get('prompt_id')}")
            save_json(project_dir / "project.json", meta)
            return auto_pipeline_status(project_id, scene_id)
        else:
            scene["auto_pipeline_state"] = "blocked"
            scene["auto_pipeline_error"] = "Falta generated_image y no se indicó checkpoint para generarla."
            _log(scene, "image", "blocked", scene["auto_pipeline_error"])
            save_json(project_dir / "project.json", meta)
            return auto_pipeline_status(project_id, scene_id)

    # 1) Image-to-video via ComfyUI. Queue once, then poll on later calls.
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    if not _exists(scene.get("generated_clip")):
        prompt_id = scene.get("comfyui_video_prompt_id")
        if not prompt_id:
            queued = queue_scene_video(project_id, scene_id, fps=max(1, int(fps)))
            meta = load_project(project_id)
            scene = _scene(meta, scene_id)
            scene["auto_pipeline_state"] = "waiting_video"
            scene.pop("auto_pipeline_error", None)
            _log(scene, "video", "queued", f"ComfyUI prompt {queued.get('prompt_id')}")
            save_json(project_dir / "project.json", meta)
            return auto_pipeline_status(project_id, scene_id)

        refreshed = refresh_scene_video(project_id, scene_id)
        meta = load_project(project_id)
        scene = _scene(meta, scene_id)
        if not _exists(scene.get("generated_clip")):
            if refreshed.get("status") == "generation_failed":
                scene["auto_pipeline_state"] = "failed"
                scene["auto_pipeline_error"] = "ComfyUI terminó sin producir un clip de video utilizable."
                _log(scene, "video", "failed", scene["auto_pipeline_error"])
            else:
                scene["auto_pipeline_state"] = "waiting_video"
                _log(scene, "video", "waiting", "ComfyUI sigue generando/importando el video")
            save_json(project_dir / "project.json", meta)
            return auto_pipeline_status(project_id, scene_id)
        _log(scene, "video", "done", str(scene.get("generated_clip")))
        save_json(project_dir / "project.json", meta)

    tools = detect_local_tools()

    # 2) Optional identity refinement.
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    if use_face_refine and not _exists(scene.get("face_refined_clip")):
        available = bool(tools.get("deep_live_cam", {}).get("available"))
        if available:
            try:
                run_deep_live_cam(
                    project_id,
                    scene_id,
                    execution_provider=execution_provider,
                    mouth_mask=mouth_mask,
                    enhance_face=enhance_face,
                )
                meta = load_project(project_id)
                scene = _scene(meta, scene_id)
                _log(scene, "face_refine", "done", str(scene.get("face_refined_clip")))
                save_json(project_dir / "project.json", meta)
            except Exception as exc:
                meta = load_project(project_id)
                scene = _scene(meta, scene_id)
                _log(scene, "face_refine", "failed", str(exc))
                if strict_optional:
                    scene["auto_pipeline_state"] = "failed"
                    scene["auto_pipeline_error"] = str(exc)
                    save_json(project_dir / "project.json", meta)
                    return auto_pipeline_status(project_id, scene_id)
                save_json(project_dir / "project.json", meta)
        else:
            _log(scene, "face_refine", "skipped", "Deep-Live-Cam no disponible")
            save_json(project_dir / "project.json", meta)

    # 3) Optional lip-sync only for scenes marked by the Director.
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    needs_lipsync = bool(scene.get("needs_lipsync"))
    if use_lipsync and needs_lipsync and not _exists(scene.get("lipsync_clip")):
        available = bool(tools.get("wav2lip", {}).get("available"))
        if available:
            try:
                run_wav2lip(project_id, scene_id)
                meta = load_project(project_id)
                scene = _scene(meta, scene_id)
                _log(scene, "lipsync", "done", str(scene.get("lipsync_clip")))
                save_json(project_dir / "project.json", meta)
            except Exception as exc:
                meta = load_project(project_id)
                scene = _scene(meta, scene_id)
                _log(scene, "lipsync", "failed", str(exc))
                if strict_optional:
                    scene["auto_pipeline_state"] = "failed"
                    scene["auto_pipeline_error"] = str(exc)
                    save_json(project_dir / "project.json", meta)
                    return auto_pipeline_status(project_id, scene_id)
                save_json(project_dir / "project.json", meta)
        else:
            _log(scene, "lipsync", "skipped", "Wav2Lip no disponible")
            save_json(project_dir / "project.json", meta)
    elif not needs_lipsync:
        _log(scene, "lipsync", "skipped", "La escena no requiere lip-sync")
        save_json(project_dir / "project.json", meta)

    # 4) Optional upscale using the best clip available so far.
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    if use_upscale and not _exists(scene.get("upscaled_clip")):
        available = bool(tools.get("real_esrgan", {}).get("available"))
        if available:
            try:
                run_upscale(project_id, scene_id, scale=max(1, int(upscale_scale)))
                meta = load_project(project_id)
                scene = _scene(meta, scene_id)
                _log(scene, "upscale", "done", str(scene.get("upscaled_clip")))
                save_json(project_dir / "project.json", meta)
            except Exception as exc:
                meta = load_project(project_id)
                scene = _scene(meta, scene_id)
                _log(scene, "upscale", "failed", str(exc))
                if strict_optional:
                    scene["auto_pipeline_state"] = "failed"
                    scene["auto_pipeline_error"] = str(exc)
                    save_json(project_dir / "project.json", meta)
                    return auto_pipeline_status(project_id, scene_id)
                save_json(project_dir / "project.json", meta)
        else:
            _log(scene, "upscale", "skipped", "Real-ESRGAN no disponible")
            save_json(project_dir / "project.json", meta)

    # 5) Register final candidate for manual review; do not auto-approve it.
    meta = load_project(project_id)
    scene = _scene(meta, scene_id)
    candidate = _best_clip(scene)
    if not candidate:
        scene["auto_pipeline_state"] = "failed"
        scene["auto_pipeline_error"] = "No quedó ningún clip utilizable al finalizar el pipeline."
        _log(scene, "review", "failed", scene["auto_pipeline_error"])
    else:
        stage = (
            "upscaled" if str(scene.get("upscaled_clip")) == candidate else
            "lipsync" if str(scene.get("lipsync_clip")) == candidate else
            "face_refined" if str(scene.get("face_refined_clip")) == candidate else
            "generated"
        )
        version_id = _ensure_review_version(scene, candidate, stage)
        scene["review_candidate"] = candidate
        scene["review_version"] = version_id
        scene["status"] = "ready_for_review"
        scene["auto_pipeline_state"] = "ready_for_review"
        scene.pop("auto_pipeline_error", None)
        _log(scene, "review", "ready", f"Versión {version_id}: {candidate}")
    save_json(project_dir / "project.json", meta)
    return auto_pipeline_status(project_id, scene_id)
