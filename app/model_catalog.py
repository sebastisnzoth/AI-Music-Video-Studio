from __future__ import annotations

from dataclasses import asdict, dataclass
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
    ModelSpec("reference-render", "Reference Render", "video", "ffmpeg", True, True,
              ("reference_image", "reference_video", "audio"), ("fallback", "preview", "timing"),
              "Always available when FFmpeg is installed."),
    ModelSpec("comfyui-image", "ComfyUI Image", "image", "comfyui", True, True,
              ("reference_image", "prompt"), ("storyboard", "style"),
              "Workflow-driven local image generation."),
    ModelSpec("ipadapter", "IPAdapter / FaceID", "identity", "comfyui", True, True,
              ("reference_image", "prompt"), ("identity", "face_consistency", "style_transfer"),
              "Preferred identity-conditioning path when compatible ComfyUI nodes/models are installed."),
    ModelSpec("instantid", "InstantID", "identity", "comfyui", True, True,
              ("reference_image", "prompt"), ("identity", "portrait", "face_consistency"),
              "Alternative face-identity conditioning path for compatible SDXL workflows."),
    ModelSpec("comfyui-video", "ComfyUI Video", "video", "comfyui", True, True,
              ("start_frame", "reference_image", "audio", "prompt"),
              ("image-to-video", "cinematic", "scene_generation"),
              "Workflow-driven local video generation; availability depends on installed models."),
    ModelSpec("wav2lip", "Wav2Lip", "lipsync", "local", True, True,
              ("video", "audio"), ("lip_sync", "performance"),
              "Lightweight local singing close-up fallback."),
    ModelSpec("musetalk", "MuseTalk", "lipsync", "local", True, True,
              ("video", "audio"), ("lip_sync", "portrait"),
              "Optional higher-quality local lip-sync backend when hardware allows."),
    ModelSpec("real-esrgan", "Real-ESRGAN", "upscale", "local", True, True,
              ("image", "video"), ("upscale", "detail_recovery"),
              "Fast local upscale option."),
)


def catalog() -> list[dict[str, Any]]:
    return [asdict(m) for m in MODELS]


def get_model(model_id: str) -> dict[str, Any] | None:
    for model in MODELS:
        if model.id == model_id:
            return asdict(model)
    return None


def choose_for_scene(scene: dict[str, Any]) -> dict[str, str]:
    needs_lipsync = bool(scene.get("needs_lipsync"))
    strategy = str(scene.get("strategy", "narrative"))
    identity_model = "ipadapter" if strategy.startswith("performance") else "ipadapter"
    lipsync_model = "wav2lip" if needs_lipsync else "none"
    if strategy == "abstract":
        identity_model = "none"
        lipsync_model = "none"
    return {
        "identity_model": identity_model,
        "image_model": "comfyui-image",
        "video_model": "comfyui-video",
        "lipsync_model": lipsync_model,
        "upscale_model": "real-esrgan",
    }
