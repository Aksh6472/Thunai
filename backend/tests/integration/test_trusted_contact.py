"""T-015: trusted-contact links (FR-12, AC-04..07, AC-12, SECURITY T-04/T-05)."""

import asyncio
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import wall_now
from app.core.settings import Settings
from app.domain.enums import Role
from app.models import ContactRequest
from tests.conftest import TEST_NOW
from tests.scenario_helpers import (
    WEDDING_EVENTS,
    WEDDING_TRANSFER,
    customer_headers,
    hero_hold,
    latest_link_token,
    staff_headers,
    wedding_hold,
    wedding_world,
)

pytestmark = pytest.mark.anyio


async def test_view_shows_only_minimal_data(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    await hero_hold(client, db, test_settings, service_headers)
    r = await client.get(f"/api/v1/trusted/{latest_link_token(app)}")
    assert r.status_code == 200
    body = r.json()
    assert body["customer_first_name"] == "Kamala"
    assert body["amount_display"] == "₹46,00,000"
    assert body["language"] == "ta"
    text_ = r.text
    for secret in ("4821", "PAY-0007", "reasons", "score", "0193", "0101", "Verification"):
        assert secret not in text_


async def test_high_hold_released_by_contact(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    """AC-06."""
    hold = await wedding_hold(client, db, test_settings, service_headers)
    assert hold["tier"] == "HIGH"
    token = latest_link_token(app)
    r = await client.post(f"/api/v1/trusted/{token}/response", json={"response": "CONFIRM_GENUINE"})
    assert r.status_code == 200
    assert r.json()["result_key"] == "RELEASED"
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    detail = (await client.get(f"/api/v1/holds/{hold['hold_id']}", headers=officer)).json()
    assert (detail["status"], detail["transfer"]["status"]) == ("RELEASED", "EXECUTED")
    assert detail["resolved_by_type"] == "TRUSTED_CONTACT"
    assert "HOLD_RELEASED" in [a["action"] for a in detail["audit"]]


async def test_used_link_is_410_and_changes_nothing(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    """AC-05."""
    await wedding_hold(client, db, test_settings, service_headers)
    token = latest_link_token(app)
    await client.post(f"/api/v1/trusted/{token}/response", json={"response": "CANNOT_REACH"})
    again = await client.post(
        f"/api/v1/trusted/{token}/response", json={"response": "CONFIRM_GENUINE"}
    )
    assert again.status_code == 410
    assert again.json()["error"]["code"] == "CONTACT_LINK_EXPIRED"
    assert (await client.get(f"/api/v1/trusted/{token}")).status_code == 410


async def test_expired_link_is_410(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    await wedding_hold(client, db, test_settings, service_headers)
    token = latest_link_token(app)
    db.execute(update(ContactRequest).values(expires_at=wall_now() - timedelta(seconds=1)))
    r = await client.post(f"/api/v1/trusted/{token}/response", json={"response": "CONFIRM_GENUINE"})
    assert r.status_code == 410


async def test_unknown_token_is_404(client: httpx.AsyncClient, db: Session) -> None:
    r = await client.get("/api/v1/trusted/" + "A" * 43)
    assert r.status_code == 404


async def test_very_high_not_released_by_contact(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    """AC-07."""
    hold = await hero_hold(client, db, test_settings, service_headers)
    token = latest_link_token(app)
    r = await client.post(f"/api/v1/trusted/{token}/response", json={"response": "CONFIRM_GENUINE"})
    assert r.json()["result_key"] == "SENT_TO_OFFICER"
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    detail = (await client.get(f"/api/v1/holds/{hold['hold_id']}", headers=officer)).json()
    assert detail["status"] == "AWAITING_OFFICER"
    assert detail["contact_response"] == "CONFIRM_GENUINE"
    assert detail["transfer"]["status"] == "HELD"


async def test_report_suspicious_sends_high_hold_to_officer(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    hold = await wedding_hold(client, db, test_settings, service_headers)
    r = await client.post(
        f"/api/v1/trusted/{latest_link_token(app)}/response", json={"response": "REPORT_SUSPICIOUS"}
    )
    assert r.json()["result_key"] == "SENT_TO_OFFICER"
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    detail = (await client.get(f"/api/v1/holds/{hold['hold_id']}", headers=officer)).json()
    assert (detail["status"], detail["contact_response"]) == (
        "AWAITING_OFFICER",
        "REPORT_SUSPICIOUS",
    )


async def test_activation_delay(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    """AC-12: a contact registered < 72 h ago is not notified; the officer gets the hold."""
    hold = await wedding_hold(
        client,
        db,
        test_settings,
        service_headers,
        contact_registered_at=TEST_NOW - timedelta(hours=20),
    )
    assert hold["decision"] == "HOLD"
    assert "NO_ACTIVE_TRUSTED_CONTACT" in hold["overrides_applied"]
    assert "TRUSTED_CONTACT_RECENTLY_CHANGED" in {r["code"] for r in hold["reasons"]}
    assert app.state.console_notifier.messages(5) == []
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    detail = (await client.get(f"/api/v1/holds/{hold['hold_id']}", headers=officer)).json()
    assert detail["status"] == "AWAITING_OFFICER"
    assert detail["contact_requests"] == []


async def test_response_after_customer_cancel_is_409(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    from app.repositories import customers

    await wedding_hold(client, db, test_settings, service_headers)
    customer = customers.by_ref(db, "CUST-0021")
    assert customer is not None
    r = await client.post(
        "/api/v1/customer/transfers/TRF-N4-0001/cancel",
        headers=customer_headers(test_settings, customer),
    )
    assert r.json()["transfer_status"] == "CANCELLED"
    late = await client.post(
        f"/api/v1/trusted/{latest_link_token(app)}/response", json={"response": "CONFIRM_GENUINE"}
    )
    assert late.status_code == 409


async def test_resend_expires_old_link(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    hold = await wedding_hold(client, db, test_settings, service_headers)
    old = latest_link_token(app)
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    r = await client.post(f"/api/v1/holds/{hold['hold_id']}/resend-contact", headers=teller)
    assert r.status_code == 202
    new = latest_link_token(app)
    assert new != old
    assert (await client.get(f"/api/v1/trusted/{old}")).status_code == 410
    assert (await client.get(f"/api/v1/trusted/{new}")).status_code == 200


# ---------- Concurrency: real separate connections, committed data ----------


async def test_concurrent_double_submit_gives_one_200_and_one_410(
    committed_app: FastAPI, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    factory: sessionmaker[Session] = committed_app.state.session_factory
    transport = httpx.ASGITransport(app=committed_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with factory() as session:
            wedding_world(session, test_settings)
            session.commit()
        for event in WEDDING_EVENTS:
            assert (
                await client.post("/api/v1/events", json=event, headers=service_headers)
            ).status_code == 202
        r = await client.post(
            "/api/v1/transfers/assess", json=WEDDING_TRANSFER, headers=service_headers
        )
        assert r.json()["tier"] == "HIGH"
        token = latest_link_token(committed_app)
        url = f"/api/v1/trusted/{token}/response"
        a, b = await asyncio.gather(
            client.post(url, json={"response": "CONFIRM_GENUINE"}),
            client.post(url, json={"response": "CONFIRM_GENUINE"}),
        )
    assert sorted([a.status_code, b.status_code]) == [200, 410]
