from __future__ import annotations

from . import main as main_module
from .integrations_api import router as integrations_router
from .pipeline_api import router as pipeline_router
from .ui_extensions import enhance_page

app = main_module.app
main_module.PAGE = enhance_page(main_module.PAGE)

app.include_router(pipeline_router)
app.include_router(integrations_router)
app.version = "0.11.1"
