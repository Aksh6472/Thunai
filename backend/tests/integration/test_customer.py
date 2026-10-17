"""Customer app (API_SPEC §5): customer-safe responses, warnings, ownership (ADR-013, T-07)."""

from datetime import timedelta

import httpx
import pytest
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.models import Customer
from tests.conftest import TEST_NOW
from tests.db_factories import make_account, make_baseline, make_customer, make_payee
from tests.scenario_helpers import customer_headers

pytestmark = pytest.mark.anyio


def _app_customer(db: Session, ref: str = "CUST-0031") -> Customer:
    customer = make_customer(db, ref, login=f"cust.{ref[-2:]}")
    make_account(db, customer, "XXXXXX3101", 10_00_000)
    make_baseline(db, customer, 40_000)
    make_payee(db, customer, "PAY-NEW", TEST_NOW - timedelta(minutes=45))
    return customer


TRANSFER = {
    "transfer_ref": "APP-0001",
    "from_account": "XXXXXX3101",
    "payee_ref": "PAY-NEW",
    "amount_paise": 40000000,
    "rail": "IMPS",
}


async def test_medium_transfer_warns_with_customer_safe_body(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    headers = customer_headers(test_settings, _app_customer(db))
    r = await client.post("/api/v1/customer/transfers", json=TRANSFER, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["decision"], body["transfer_status"], body["message_key"]) == (
        "WARN",
        "WARNED",
        "transfer.warned",
    )
    for hidden in ("score", "tier", "reasons", "raw_score"):
        assert hidden not in body


async def test_warning_continue_executes(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    headers = customer_headers(test_settings, _app_customer(db))
    await client.post("/api/v1/customer/transfers", json=TRANSFER, headers=headers)
    r = await client.post(
        "/api/v1/customer/transfers/APP-0001/warning-response",
        json={"action": "CONTINUE"},
        headers=headers,
    )
    assert r.json()["transfer_status"] == "EXECUTED"
    again = await client.post(
        "/api/v1/customer/transfers/APP-0001/warning-response",
        json={"action": "CANCEL"},
        headers=headers,
    )
    assert again.status_code == 409


async def test_warning_cancel(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    headers = customer_headers(test_settings, _app_customer(db))
    await client.post("/api/v1/customer/transfers", json=TRANSFER, headers=headers)
    r = await client.post(
        "/api/v1/customer/transfers/APP-0001/warning-response",
        json={"action": "CANCEL"},
        headers=headers,
    )
    assert r.json()["transfer_status"] == "CANCELLED"


async def test_insufficient_balance(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    headers = customer_headers(test_settings, _app_customer(db))
    r = await client.post(
        "/api/v1/customer/transfers", json={**TRANSFER, "amount_paise": 10**11}, headers=headers
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INSUFFICIENT_BALANCE"


async def test_other_customers_transfer_is_404(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    owner = customer_headers(test_settings, _app_customer(db))
    await client.post("/api/v1/customer/transfers", json=TRANSFER, headers=owner)
    intruder = customer_headers(test_settings, _app_customer(db, "CUST-0032"))
    assert (
        await client.get("/api/v1/customer/transfers/APP-0001", headers=intruder)
    ).status_code == 404
    assert (
        await client.post("/api/v1/customer/transfers/APP-0001/cancel", headers=intruder)
    ).status_code == 404


async def test_mass_assignment_rejected(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    headers = customer_headers(test_settings, _app_customer(db))
    r = await client.post(
        "/api/v1/customer/transfers", json={**TRANSFER, "status": "EXECUTED"}, headers=headers
    )
    assert r.status_code == 422


async def test_overview_consent_and_contact(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    headers = customer_headers(test_settings, _app_customer(db))
    overview = (await client.get("/api/v1/customer/overview", headers=headers)).json()
    assert overview["accounts"][0]["masked_number"] == "XXXXXX3101"
    assert overview["consents"] == {"CALL_SIGNAL": False, "TRUSTED_CONTACT_SHARING": False}
    r = await client.post(
        "/api/v1/customer/consents",
        json={"consent_type": "CALL_SIGNAL", "granted": True, "text_version": "call_signal_v1"},
        headers=headers,
    )
    assert r.status_code == 201
    r = await client.post(
        "/api/v1/customer/trusted-contact",
        json={
            "display_name": "Arun",
            "relationship": "son",
            "phone_e164": "+919800000101",
            "preferred_language": "ta",
        },
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "PENDING_ACTIVATION"
    overview = (await client.get("/api/v1/customer/overview", headers=headers)).json()
    assert overview["consents"]["CALL_SIGNAL"] is True
    assert overview["trusted_contact"]["phone_last4"] == "0101"
    assert overview["trusted_contact"]["status"] == "PENDING_ACTIVATION"


async def test_staff_token_cannot_use_customer_app(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    from app.domain.enums import Role
    from tests.scenario_helpers import staff_headers

    teller = staff_headers(db, test_settings, "teller.c", Role.TELLER)
    assert (await client.get("/api/v1/customer/overview", headers=teller)).status_code == 403
