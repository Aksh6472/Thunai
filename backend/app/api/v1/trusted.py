"""Trusted-contact page API (API_SPEC §9). Public: the single-use token is the credential."""

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_ctx, get_db
from app.schemas.trusted import TrustedResponseIn, TrustedResponseOut, TrustedView
from app.services import contact_service
from app.services.context import Ctx

router = APIRouter(prefix="/trusted", tags=["trusted-contact"])
Token = Path(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_\-]+$")


@router.get("/{token}", response_model=TrustedView)
def view(
    request: Request,
    token: str = Token,
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> TrustedView:
    return contact_service.view(session, ctx, token, client_ip(request))


@router.post("/{token}/response", response_model=TrustedResponseOut)
def respond(
    body: TrustedResponseIn,
    request: Request,
    token: str = Token,
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> TrustedResponseOut:
    return contact_service.respond(session, ctx, token, body.response, client_ip(request))
