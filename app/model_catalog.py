from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ModelSpec:
    id: str
    label: str
    kind: str
    backend: str
    local: bool
    free_core: bool
    roles: tuple[str, ...]
    strengths: tuple[str, ...]
    notes: str = ""


MODELS = (
    ModelSpec(
        id="reference-render",
        label="Reference Render",
        kind="video",
        backend="ffmpeg",
        local=True,
        free_core=True,
        roles=("reference_image", "reference_video", "audio"),
        strengths=("fallback", "preview", "timing"),
        notes="Always available when FFmpeg is installed.",
    ),
    ModelSpec(
        id="comfyui-image",
        label="ComfyUI Image",
        kind="image",
        backend="comfyui",
        local=True,
        free_core=True,
        roles=("reference_image", "prompt"),
        strengths=("storyboard", "identity", "style"),
        notes="Workflow-driven local image generation.",
    ),
    ModelSpec(
        id="comfyui-video",
        label="ComfyUI Video",
        kind="video",
        backend="comfyui",
        local=True,
        free_core=True,
        roles=("start_frame", "reference_image", "audio", "prompt"),
        strengths=("image-to-video", "cinematic", "scene_generation"),
        notes="Workflow-driven local video generation. Model availability depends on installed ComfyUI workflows and weights.",
    ),
    ModelSpec(
        id="wav2lip",
        label="Wav2Lip",
        kind="lipsync",
        backend="local",
        local=True,
        free_core=True,
        roles=("video", "audio"),
        strengths=("lip_sync", "performance"),
        notes="Lightweight fallback for singing close-ups.",
    ),
    ModelSpec(
        id="musetalk",
        label="MuseTalk",
        kind="lipsync",
        backend="local",
        local=True,
        free_core=True,
        roles=("video", "audio"),
        strengths=("lip_sync", "portrait"),
        notes="Optional local lip-sync backend.",
    ),
    ModelSpec(
        id="real-esrgan",
        label="Real-ESRGAN",
        kind="upscale",
        backend="local",
        local=True,
        free_core=True,
        roles=("image", "video"),
        strengths=("upscale", "detail_recovery"),
        notes="Fast local upscale option.",
    ),
)


def catalog() -> list[dict[str, Any]]:
    return [asdict(m) for m in MODELS]


def get_model(model_id: str) -> dict[str, Any] | None:
    for model in MODELS:
        if model.id == model_id:
            return asdict(model)
    return None


def choose_for_scene(scene: dict[str, Any]) -> dict[str, str]:
    """Pick a free/local default toolchain for a directed scene."""
    needs_lipsync = bool(scene.get("needs_lipsync"))
    strategy = str(scene.get("strategy", "narrative"))
    image_model = "comfyui-image"
    video_model = "comfyui-video"
    lipsync_model = "wav2lip" if needs_lipsync else "none"
    if strategy == "abstract":
        lipsync_model = "none"
    return {
        "image_model": image_model,
        "video_model": video_model,
        "lipsync_model": lipsync_model,
        "upscale_model": "real-esrgan",
    }
