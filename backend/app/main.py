from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import health
from app.core.branding import PRODUCT_NAME
from app.core.clock import Clock, RealClock, SimClock
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.scoring_config import load_scoring_config
from app.core.settings import Settings, get_settings
from app.db import make_engine, make_session_factory

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    # Fail closed at startup: an invalid scoring config stops the process (AI_DESIGN §11).
    scoring_config = load_scoring_config(settings.scoring_config_file)

    app = FastAPI(title=f"{PRODUCT_NAME} API", version="0.1.0")
    engine = make_engine(settings.database_url)
    app.state.settings = settings
    app.state.scoring_config = scoring_config
    app.state.engine = engine
    session_factory = make_session_factory(engine)
    app.state.session_factory = session_factory
    # Demo mode runs on simulated time so multi-day scenarios replay in seconds (ADR-008).
    clock: Clock = SimClock(session_factory) if settings.demo_mode else RealClock()
    app.state.clock = clock

    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=[
            "X-Request-ID",
            "Retry-After",
            "Idempotent-Replay",
            "X-Thunai-LLM-Fallback",
        ],
    )
    app.add_middleware(RequestContextMiddleware)

    v1 = APIRouter(prefix=API_PREFIX)
    v1.include_router(health.router)
    app.include_router(v1)

    return app


app = create_app()
