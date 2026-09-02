from __future__ import annotations

import os

from fastapi.middleware.cors import CORSMiddleware

from . import main as main_module
from . import orchestrator as orchestrator_module
from .image_engine_adapter import queue_scene_image as routed_queue_scene_image
from .integrations_api import router as integrations_router
from .pipeline_api import router as pipeline_router
from .project_create_api import router as project_create_router
from .scene_control_api import router as scene_control_router
from .ui_extensions import enhance_page
from .video_engine_adapter import (
    queue_scene_video as routed_queue_scene_video,
    refresh_scene_video as routed_refresh_scene_video,
    video_engines_status,
)

# Keep the existing resumable orchestrator, but replace only its generation
# stages. Image queuing is idempotent and uses a fast 8-step path in Preview;
# video tries WAN 2.2 ZeroGPU first and preserves ComfyUI/FFmpeg fallback.
orchestrator_module.queue_scene_image = routed_queue_scene_image
orchestrator_module.queue_scene_video = routed_queue_scene_video
orchestrator_module.refresh_scene_video = routed_refresh_scene_video

app = main_module.app
main_module.PAGE = enhance_page(main_module.PAGE)

DEFAULT_WEB_ORIGINS = ",".join([
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "https://ai-music-video-studio-three.vercel.app",
    "https://ai-music-video-studio-sebastisnzoths-projects.vercel.app",
])
raw_origins = os.getenv("WEB_ORIGINS", DEFAULT_WEB_ORIGINS)
origins = [item.strip() for item in raw_origins.split(",") if item.strip()]
allow_all = "*" in origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/video-engines")
def video_engines():
    return video_engines_status()


app.include_router(project_create_router)
app.include_router(scene_control_router)
app.include_router(pipeline_router)
app.include_router(integrations_router)
app.version = "0.13.6"
