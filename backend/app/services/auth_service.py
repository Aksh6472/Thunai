"""Login and identity lookups (FR-19, SECURITY T-12)."""

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.clock import wall_now
from app.core.errors import InvalidCredentials, Unauthenticated
from app.core.rate_limit import RateLimiter
from app.core.security import Principal, create_access_token, verify_password
from app.core.settings import Settings
from app.domain.enums import ActorType, Role
from app.models import Customer, StaffUser
from app.repositories import users
from app.schemas.auth import LoginResponse, UserOut
from app.services.audit_service import audit

logger = logging.getLogger(__name__)

LOGIN_IP_LIMIT = (10, 60)  # 10 / min / IP
LOGIN_FAILURE_LIMIT = (5, 15 * 60)  # 5 failures / 15 min / username


def _user_out(user: StaffUser | Customer) -> UserOut:
    if isinstance(user, StaffUser):
        return UserOut(
            id=str(user.id),
            role=user.role,
            display_name=user.display_name,
            branch_code=user.branch_code,
        )
    return UserOut(
        id=str(user.id),
        role=Role.CUSTOMER,
        display_name=user.display_name,
        branch_code=user.branch_code,
        customer_ref=user.external_ref,
    )


def login(
    session: Session,
    *,
    username: str,
    password: str,
    client_ip: str,
    limiter: RateLimiter,
    settings: Settings,
) -> LoginResponse:
    limiter.hit(f"login-ip:{client_ip}", *LOGIN_IP_LIMIT)
    failure_key = f"login-fail:{username.lower()}"
    limiter.check(failure_key, *LOGIN_FAILURE_LIMIT)

    staff = users.staff_by_username(session, username)
    customer = None if staff else users.customer_by_login(session, username)
    user: StaffUser | Customer | None = staff or customer
    password_hash = (
        staff.password_hash
        if staff and staff.is_active
        else customer.login_password_hash
        if customer
        else None
    )
    # verify_password always runs (against a dummy hash for unknown users): uniform timing.
    if user is None or not verify_password(password, password_hash):
        limiter.hit(failure_key, *LOGIN_FAILURE_LIMIT)
        audit(
            session,
            "LOGIN_FAILED",
            entity_type="login",
            entity_id=username.lower()[:64],
            actor_type=ActorType.SYSTEM,
        )
        session.commit()
        logger.info("auth.login_failed")
        raise InvalidCredentials()

    limiter.reset(failure_key)
    out = _user_out(user)
    token, expires_in = create_access_token(
        user_id=out.id,
        role=out.role,
        branch_code=out.branch_code,
        settings=settings,
        now=wall_now(),
    )
    audit(
        session,
        "LOGIN_SUCCEEDED",
        entity_type="staff_user" if staff else "customer",
        entity_id=out.id,
        actor_type=ActorType.STAFF if staff else ActorType.CUSTOMER,
        actor_id=out.id,
    )
    session.commit()
    return LoginResponse(access_token=token, expires_in=expires_in, user=out)


def me(session: Session, principal: Principal) -> UserOut:
    try:
        user_id = uuid.UUID(principal.id)
    except ValueError:
        raise Unauthenticated() from None
    user: StaffUser | Customer | None = (
        users.customer_by_id(session, user_id)
        if principal.role is Role.CUSTOMER
        else users.staff_by_id(session, user_id)
    )
    if user is None:
        raise Unauthenticated()
    return _user_out(user)
