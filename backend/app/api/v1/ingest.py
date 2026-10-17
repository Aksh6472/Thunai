"""Ingestion endpoints (API_SPEC §4). Service key only."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings_dep, require_service_key
from app.core.security import Principal
from app.core.settings import Settings
from app.schemas.events import CallSignalAccepted, CallSignalIn, EventAccepted, EventIn
from app.services import ingest_service

router = APIRouter(tags=["ingestion"])


@router.post("/events", response_model=EventAccepted, status_code=202)
def post_event(
    body: EventIn,
    request: Request,
    response: Response,
    _: Principal = Depends(require_service_key),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> EventAccepted:
    result, replayed = ingest_service.ingest_event(
        session, body, settings, request.app.state.scoring_config
    )
    if replayed:
        response.status_code = 200
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.post("/signals/call", response_model=CallSignalAccepted, status_code=202)
def post_call_signal(
    body: CallSignalIn,
    request: Request,
    _: Principal = Depends(require_service_key),
    session: Session = Depends(get_db),
) -> CallSignalAccepted:
    return ingest_service.ingest_call_signal(session, body, request.app.state.scoring_config)
