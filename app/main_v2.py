from __future__ import annotations

from .integrations_api import router as integrations_router
from .main import app
from .pipeline_api import router as pipeline_router

app.include_router(pipeline_router)
app.include_router(integrations_router)
app.version = "0.9.0"
