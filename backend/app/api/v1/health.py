import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import error_response

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/readyz", response_model=None)
def readyz(request: Request) -> dict[str, str] | JSONResponse:
    """Readiness: DB reachable, scoring config loaded, notifier selected."""
    state = request.app.state
    db_status = "ok"
    try:
        with state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("readyz.db_unavailable")
        db_status = "error"

    body = {
        "db": db_status,
        "scoring_config": state.scoring_config.config_version,
        "notifier": state.settings.notifier,
    }
    if db_status != "ok":
        return error_response(503, "DEPENDENCY_UNAVAILABLE", "Not ready.", body)
    return {"status": "ready", **body}
