from __future__ import annotations

import os

from fastapi.middleware.cors import CORSMiddleware

from . import main as main_module
from .integrations_api import router as integrations_router
from .pipeline_api import router as pipeline_router
from .project_create_api import router as project_create_router
from .ui_extensions import enhance_page

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

app.include_router(project_create_router)
app.include_router(pipeline_router)
app.include_router(integrations_router)
app.version = "0.13.3"
