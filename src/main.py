import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.exceptions import register_handlers
from src.identity import routes as identity
from src.legal.routes import legal_router


logger = logging.getLogger(__name__)

environment = (
    os.environ.get("ENVIRONMENT")
    if os.environ.get("ENVIRONMENT") is not None
    else "Production"
)

logger.info("API Starting up")

app = FastAPI(
    title="Voney Machine Learning API",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    docs_url=None if environment == "Production" else "/docs",
    redoc_url=None if environment == "Production" else "/redoc",
)


register_handlers(app)

app.include_router(identity.api, prefix="/api")
app.include_router(legal_router)
