"""T-010: login, JWT, RBAC basics, rate limiting, audit (AC-13, TESTING.md §3)."""

from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rate_limit import RateLimiter
from app.core.security import create_access_token
from app.core.settings import Settings
from app.domain.enums import Role
from app.models import AuditLog
from tests.db_factories import PASSWORD, make_customer, make_staff

pytestmark = pytest.mark.anyio


async def _login(
    client: httpx.AsyncClient, username: str, password: str = PASSWORD
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


async def test_staff_login_returns_token_and_user(client: httpx.AsyncClient, db: Session) -> None:
    make_staff(db, "teller.priya", Role.TELLER)
    response = await _login(client, "teller.priya")
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["user"]["role"] == "TELLER"
    assert body["user"]["display_name"] == "Priya (fictional)"

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["role"] == "TELLER"
    actions = db.scalars(select(AuditLog.action)).all()
    assert "LOGIN_SUCCEEDED" in actions


async def test_customer_login(client: httpx.AsyncClient, db: Session) -> None:
    make_customer(db, "CUST-0007", login="cust.kamala")
    body = (await _login(client, "cust.kamala")).json()
    assert body["user"]["role"] == "CUSTOMER"
    assert body["user"]["customer_ref"] == "CUST-0007"


async def test_wrong_password_and_unknown_user_look_identical(
    client: httpx.AsyncClient, db: Session
) -> None:
    make_staff(db, "officer.rao", Role.OFFICER)
    wrong = await _login(client, "officer.rao", "nope")
    unknown = await _login(client, "nobody.here", "nope")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["code"] == unknown.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]
    failed = db.scalars(select(AuditLog).where(AuditLog.action == "LOGIN_FAILED")).all()
    assert len(failed) == 2


async def test_inactive_staff_cannot_log_in(client: httpx.AsyncClient, db: Session) -> None:
    make_staff(db, "teller.gone", active=False)
    assert (await _login(client, "teller.gone")).status_code == 401


async def test_me_without_token_is_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_expired_token_is_401_token_expired(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    user = make_staff(db, "teller.old")
    token, _ = create_access_token(
        user_id=str(user.id),
        role=Role.TELLER,
        branch_code="CHN001",
        settings=test_settings,
        now=datetime.now(UTC) - timedelta(hours=2),
    )
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


async def test_alg_none_token_is_rejected(client: httpx.AsyncClient, db: Session) -> None:
    user = make_staff(db, "teller.none")
    claims = {"sub": str(user.id), "role": "OFFICER", "jti": "x", "exp": 9999999999}
    forged = jwt.encode(claims, key=None, algorithm="none")  # type: ignore[arg-type]
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


async def test_token_signed_with_other_key_is_rejected(
    client: httpx.AsyncClient, db: Session
) -> None:
    user = make_staff(db, "teller.forge")
    claims = {"sub": str(user.id), "role": "OFFICER", "jti": "x", "exp": 9999999999}
    forged = jwt.encode(claims, "x" * 64, algorithm="HS256")
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


async def test_service_key_on_user_route_is_403(
    client: httpx.AsyncClient, test_settings: Settings
) -> None:
    response = await client.get(
        "/api/v1/auth/me", headers={"X-Thunai-Service-Key": test_settings.service_api_key}
    )
    assert response.status_code == 403


async def test_wrong_service_key_is_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me", headers={"X-Thunai-Service-Key": "wrong"})
    assert response.status_code == 401


@pytest.fixture
def limits_on(app: FastAPI) -> None:
    app.state.rate_limiter = RateLimiter(enabled=True)


async def test_sixth_failed_login_is_429(
    client: httpx.AsyncClient, db: Session, limits_on: None
) -> None:
    make_staff(db, "teller.rate")
    for _ in range(5):
        assert (await _login(client, "teller.rate", "bad")).status_code == 401
    sixth = await _login(client, "teller.rate")  # even the right password is refused now
    assert sixth.status_code == 429
    assert sixth.json()["error"]["code"] == "RATE_LIMITED"
    assert int(sixth.headers["retry-after"]) > 0


async def test_login_ip_limit(client: httpx.AsyncClient, db: Session, limits_on: None) -> None:
    make_staff(db, "teller.burst")
    codes = [(await _login(client, "teller.burst")).status_code for _ in range(11)]
    assert codes[:10] == [200] * 10
    assert codes[10] == 429
