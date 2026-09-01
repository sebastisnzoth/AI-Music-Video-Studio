from __future__ import annotations

from .main import app
from .pipeline_api import router as pipeline_router

app.include_router(pipeline_router)
app.version = "0.7.0"
