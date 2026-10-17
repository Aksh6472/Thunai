"""T-043: every route × every principal gets the SECURITY §3 outcome (AC-13).

Allowed principals must get past authentication and role checks (any status except 401/403;
dummy ids then give 404/422). Others get 401 (no credentials) or 403 (wrong credential type
or role). Every route in the app must appear here: no route without an explicit decision.
"""

import uuid

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import Role
from tests.db_factories import make_customer
from tests.scenario_helpers import bearer, customer_headers, staff_headers

pytestmark = pytest.mark.anyio

PUBLIC = "PUBLIC"
SERVICE = "SERVICE"
ANY_USER = "ANY_USER"
C, T, OFF, A = Role.CUSTOMER, Role.TELLER, Role.OFFICER, Role.ADMIN

# (method, path template) -> who may call it
MATRIX: dict[tuple[str, str], set[object]] = {
    ("GET", "/api/v1/healthz"): {PUBLIC},
    ("GET", "/api/v1/readyz"): {PUBLIC},
    ("POST", "/api/v1/auth/login"): {PUBLIC},
    ("GET", "/api/v1/auth/me"): {ANY_USER},
    ("POST", "/api/v1/events"): {SERVICE},
    ("POST", "/api/v1/signals/call"): {SERVICE},
    ("POST", "/api/v1/transfers/assess"): {SERVICE},
    ("GET", "/api/v1/transfers/{transfer_ref}"): {SERVICE, T, OFF},
    ("POST", "/api/v1/transfers/{transfer_ref}/warning-response"): {SERVICE},
    ("GET", "/api/v1/customer/overview"): {C},
    ("POST", "/api/v1/customer/transfers"): {C},
    ("GET", "/api/v1/customer/transfers/{transfer_ref}"): {C},
    ("POST", "/api/v1/customer/transfers/{transfer_ref}/warning-response"): {C},
    ("POST", "/api/v1/customer/transfers/{transfer_ref}/cancel"): {C},
    ("POST", "/api/v1/customer/consents"): {C},
    ("POST", "/api/v1/customer/trusted-contact"): {C},
    ("GET", "/api/v1/holds"): {T, OFF, A},
    ("GET", "/api/v1/holds/{hold_id}"): {T, OFF, A},
    ("POST", "/api/v1/holds/{hold_id}/officer-decision"): {OFF},
    ("POST", "/api/v1/holds/{hold_id}/resend-contact"): {T, OFF},
    ("GET", "/api/v1/trusted/{token}"): {PUBLIC},
    ("POST", "/api/v1/trusted/{token}/response"): {PUBLIC},
    ("GET", "/api/v1/teller/queue"): {T, OFF},
    ("POST", "/api/v1/teller/transfers/{transfer_ref}/checklist"): {T, OFF},
    ("GET", "/api/v1/teller/holds/{hold_id}/script"): {T, OFF},
    ("POST", "/api/v1/holds/{hold_id}/report"): {T, OFF},
    ("GET", "/api/v1/reports/{report_id}"): {T, OFF, A},
    ("PATCH", "/api/v1/reports/{report_id}"): {T, OFF},
    ("POST", "/api/v1/reports/{report_id}/mark-filed"): {OFF},
    ("GET", "/api/v1/dashboard/summary"): {OFF, A},
    ("GET", "/api/v1/alerts"): {T, OFF, A},
    ("GET", "/api/v1/customers"): {OFF, A},
    ("GET", "/api/v1/customers/{customer_id}/risk"): {T, OFF, A},
    ("GET", "/api/v1/customers/{customer_id}/timeline"): {OFF, A},
    ("GET", "/api/v1/demo/scenarios"): {A},
    ("POST", "/api/v1/demo/reset"): {A},
    ("POST", "/api/v1/demo/scenarios/{scenario_id}/run"): {A},
    ("GET", "/api/v1/demo/runs"): {A},
    ("GET", "/api/v1/demo/clock"): {A, OFF, T},
    ("POST", "/api/v1/demo/clock"): {A, SERVICE},
    ("POST", "/api/v1/demo/fri"): {A},
    ("GET", "/api/v1/demo/console-messages"): {A},
}

PRINCIPALS = ["anonymous", "service", C, T, OFF, A]
DUMMY = {
    "transfer_ref": "TRF-NOPE",
    "hold_id": str(uuid.UUID(int=0)),
    "report_id": str(uuid.UUID(int=0)),
    "customer_id": str(uuid.UUID(int=0)),
    "token": "A" * 43,
    "scenario_id": "ZZ",
}
# Routes whose allowed call would do real work with an empty body: send nothing harmful.
SKIP_ALLOWED_CALL = {("POST", "/api/v1/demo/reset"), ("POST", "/api/v1/demo/clock")}


def test_every_route_has_an_explicit_decision(app: FastAPI) -> None:
    # The OpenAPI schema lists every included route (FastAPI nests included routers).
    routes = {
        (method.upper(), path) for path, item in app.openapi()["paths"].items() for method in item
    }
    assert routes == set(MATRIX), {
        "missing": sorted(routes - set(MATRIX)),
        "stale": sorted(set(MATRIX) - routes),
    }


def _headers(principal: object, db: Session, settings: Settings) -> dict[str, str]:
    if principal == "anonymous":
        return {}
    if principal == "service":
        return {"X-Thunai-Service-Key": settings.service_api_key}
    if principal is C:
        return customer_headers(settings, make_customer(db, login="cust.matrix"))
    assert isinstance(principal, Role)
    return staff_headers(db, settings, f"{principal.value.lower()}.matrix", principal)


def _allowed(principal: object, allowed: set[object]) -> bool:
    if PUBLIC in allowed:
        return True
    if principal == "anonymous":
        return False
    if principal == "service":
        return SERVICE in allowed
    return ANY_USER in allowed or principal in allowed


@pytest.mark.parametrize("principal", PRINCIPALS, ids=lambda p: str(p))
@pytest.mark.parametrize(("method", "path"), sorted(MATRIX), ids=lambda x: str(x))
async def test_authorisation_matrix(
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    method: str,
    path: str,
    principal: object,
) -> None:
    allowed = _allowed(principal, MATRIX[(method, path)])
    if allowed and (method, path) in SKIP_ALLOWED_CALL:
        pytest.skip("allowed call has side effects; covered in test_demo.py")
    url = path.format(**DUMMY)
    headers = _headers(principal, db, test_settings)
    response = await client.request(
        method, url, headers=headers, json={} if method != "GET" else None
    )
    if allowed:
        assert response.status_code not in (401, 403), (response.status_code, response.text)
    elif principal == "anonymous":
        assert response.status_code == 401, response.text
    else:
        assert response.status_code == 403, response.text


async def test_admin_cannot_resolve_holds(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    """Separation of duties (SECURITY §3): ADMIN reads everything but never decides."""
    headers = bearer(test_settings, str(uuid.uuid4()), Role.ADMIN)
    r = await client.post(
        f"/api/v1/holds/{uuid.UUID(int=0)}/officer-decision",
        json={"decision": "RELEASE", "note": "admin trying to release"},
        headers=headers,
    )
    assert r.status_code == 403
