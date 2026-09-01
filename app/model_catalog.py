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
    ModelSpec("localai-video", "LocalAI Video", "video", "localai", True, True,
              ("start_frame", "prompt", "audio"),
              ("image-to-video", "ltx", "unified_local_api"),
              "Optional LocalAI video backend. Exact generation route is configurable per LocalAI version/backend."),
    ModelSpec("deep-live-cam", "Deep-Live-Cam", "identity_refine", "local", True, True,
              ("reference_image", "video"), ("face_swap", "identity_refinement", "mouth_mask"),
              "Optional face refinement stage before lip-sync."),
    ModelSpec("duix-avatar", "Duix Avatar", "avatar", "local", True, True,
              ("video", "audio"), ("digital_human", "lip_sync", "avatar"),
              "Optional fully local avatar backend; practical deployment expects NVIDIA hardware and substantial disk/RAM."),
    ModelSpec("wav2lip", "Wav2Lip", "lipsync", "local", True, True,
              ("video", "audio"), ("lip_sync", "performance"),
              "Lightweight local singing close-up fallback."),
    ModelSpec("musetalk", "MuseTalk", "lipsync", "local", True, True,
              ("video", "audio"), ("lip_sync", "portrait"),
              "Optional higher-quality local lip-sync backend when hardware allows."),
    ModelSpec("real-esrgan", "Real-ESRGAN", "upscale", "local", True, True,
              ("image", "video"), ("upscale", "detail_recovery"),
              "Fast local upscale option."),
    ModelSpec("hyperframes", "HyperFrames", "compositor", "local", True, True,
              ("video", "audio", "captions", "html"),
              ("deterministic_render", "motion_graphics", "beat_sync", "captions"),
              "Optional Node.js compositor for deterministic overlays, titles and beat-synced graphics."),
    ModelSpec("srs", "SRS", "streaming", "local", True, True,
              ("video", "audio"), ("webrtc", "rtmp", "hls", "preview_stream"),
              "Optional realtime preview/stream server; not a generation model."),
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
    identity_model = "ipadapter"
    lipsync_model = "wav2lip" if needs_lipsync else "none"
    if strategy == "abstract":
        identity_model = "none"
        lipsync_model = "none"
    return {
        "identity_model": identity_model,
        "image_model": "comfyui-image",
        "video_model": "comfyui-video",
        "video_model_fallback": "localai-video",
        "identity_refine_model": "deep-live-cam" if identity_model != "none" else "none",
        "lipsync_model": lipsync_model,
        "upscale_model": "real-esrgan",
        "compositor": "ffmpeg",
    }
