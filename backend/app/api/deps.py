"""Shared FastAPI dependencies: DB session, clock, settings, authentication and RBAC.

Every route declares one of: require_roles(...), require_service_key, require_staff_or_service,
or is explicitly public (CLAUDE.md §10).
"""

from collections.abc import Callable, Iterator

from fastapi import BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.errors import Forbidden, Unauthenticated
from app.core.rate_limit import RateLimiter
from app.core.security import Principal, decode_access_token, service_key_matches
from app.core.settings import Settings
from app.domain.enums import Role
from app.services.context import Ctx

SERVICE_KEY_HEADER = "X-Thunai-Service-Key"
USER_LIMIT = (300, 60)
SERVICE_LIMIT = (1200, 60)


def get_db(request: Request) -> Iterator[Session]:
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter = request.app.state.rate_limiter
    return limiter


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    return token.strip() if scheme.lower() == "bearer" and token.strip() else None


def _service_principal(request: Request) -> Principal | None:
    """None if no key header; raises 401 if a key is present but wrong."""
    key = request.headers.get(SERVICE_KEY_HEADER)
    if key is None:
        return None
    settings: Settings = request.app.state.settings
    if not service_key_matches(key, settings):
        raise Unauthenticated()
    return Principal(kind="service", id="simulator")


def _user_principal(request: Request) -> Principal | None:
    token = _bearer(request)
    if token is None:
        return None
    return decode_access_token(token, request.app.state.settings)


def current_user(request: Request) -> Principal:
    principal = _user_principal(request)
    if principal is None:
        if _service_principal(request) is not None:
            raise Forbidden()  # valid service key on a user route
        raise Unauthenticated()
    request.app.state.rate_limiter.hit(f"user:{principal.id}", *USER_LIMIT)
    return principal


def require_roles(*roles: Role) -> Callable[..., Principal]:
    allowed = frozenset(roles)

    def dependency(principal: Principal = Depends(current_user)) -> Principal:
        if principal.role not in allowed:
            raise Forbidden()
        return principal

    dependency.__name__ = f"require_{'_'.join(r.value.lower() for r in roles)}"
    return dependency


def require_service_key(request: Request) -> Principal:
    principal = _service_principal(request)
    if principal is None:
        if _user_principal(request) is not None:
            raise Forbidden()  # valid JWT on a service route
        raise Unauthenticated()
    request.app.state.rate_limiter.hit("service", *SERVICE_LIMIT)
    return principal


def require_staff_or_service(*roles: Role) -> Callable[..., Principal]:
    allowed = frozenset(roles)

    def dependency(request: Request) -> Principal:
        service = _service_principal(request)
        if service is not None:
            request.app.state.rate_limiter.hit("service", *SERVICE_LIMIT)
            return service
        principal = current_user(request)
        if principal.role not in allowed:
            raise Forbidden()
        return principal

    return dependency


def get_ctx(request: Request, background: BackgroundTasks) -> Ctx:
    state = request.app.state
    return Ctx(
        settings=state.settings,
        cfg=state.scoring_config,
        clock=state.clock,
        fri=state.fri_client,
        console=state.console_notifier,
        real_notifier=state.real_notifier,
        session_factory=state.session_factory,
        limiter=state.rate_limiter,
        drafter=state.narrative_drafter,
        schedule=background.add_task,
    )
