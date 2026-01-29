import logging
import os

from fastapi import FastAPI

from src.common.exceptions import register_handlers
from src.identity import routes as identity

logger = logging.getLogger(__name__)

environment = (
    os.environ.get("ENVIRONMENT")
    if os.environ.get("ENVIRONMENT") is not None
    else "Production"
)


app = FastAPI(
    title="Template API",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "persistAuthorization": True,
    },
    docs_url=None if environment == "Production" else "/docs",
    redoc_url=None if environment == "Production" else "/redoc",
)


register_handlers(app)

app.include_router(identity.api, prefix="/api")
