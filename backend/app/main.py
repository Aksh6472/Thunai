from fastapi import APIRouter, FastAPI

from app.api.v1 import health
from app.core.branding import PRODUCT_NAME

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(title=f"{PRODUCT_NAME} API", version="0.1.0")

    v1 = APIRouter(prefix=API_PREFIX)
    v1.include_router(health.router)
    app.include_router(v1)

    return app


app = create_app()
