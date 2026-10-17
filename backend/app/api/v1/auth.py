from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import client_ip, current_user, get_db, get_limiter, get_settings_dep
from app.core.rate_limit import RateLimiter
from app.core.security import Principal
from app.core.settings import Settings
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    request: Request,
    session: Session = Depends(get_db),
    limiter: RateLimiter = Depends(get_limiter),
    settings: Settings = Depends(get_settings_dep),
) -> LoginResponse:
    """Public, rate-limited. Same 401 for an unknown user or a wrong password."""
    return auth_service.login(
        session,
        username=body.username,
        password=body.password,
        client_ip=client_ip(request),
        limiter=limiter,
        settings=settings,
    )


@router.get("/me", response_model=UserOut)
def me(principal: Principal = Depends(current_user), session: Session = Depends(get_db)) -> UserOut:
    return auth_service.me(session, principal)
