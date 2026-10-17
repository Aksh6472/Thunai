"""T-012: event ingestion (FR-03, AC-15, NFR-05)."""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import AccountStatus
from app.models import AccountEvent, Payee, TrustedContact
from tests.db_factories import hero_world
from tests.hero_api import HERO_EVENTS, HERO_PAYEE

pytestmark = pytest.mark.anyio


async def test_fd_closure_detects_s1_and_opens_episode(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    world = hero_world(db, test_settings)
    r = await client.post("/api/v1/events", json=HERO_EVENTS[0], headers=service_headers)
    assert r.status_code == 202
    body = r.json()
    assert body["stage_detected"] == "S1_LIQUIDATION"
    assert body["episode"]["watch_score"] == 15
    assert body["episode"]["watch_tier"] == "LOW"
    db.expire_all()
    assert world.fd.status is AccountStatus.CLOSED
    assert world.savings.balance_paise == 36_00_000 * 100


async def test_idempotent_replay_returns_original(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hero_world(db, test_settings)
    first = await client.post("/api/v1/events", json=HERO_EVENTS[0], headers=service_headers)
    await client.post("/api/v1/events", json=HERO_EVENTS[1], headers=service_headers)
    again = await client.post("/api/v1/events", json=HERO_EVENTS[0], headers=service_headers)
    assert again.status_code == 200
    assert again.headers["idempotent-replay"] == "true"
    assert again.json() == first.json()
    count = db.scalar(
        select(AccountEvent).where(AccountEvent.event_id == "EVT-P1-FD").exists().select()
    )
    assert count
    assert (
        len(db.scalars(select(AccountEvent).where(AccountEvent.event_id == "EVT-P1-FD")).all()) == 1
    )


async def test_conflicting_replay_is_409(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hero_world(db, test_settings)
    await client.post("/api/v1/events", json=HERO_EVENTS[0], headers=service_headers)
    changed = {**HERO_EVENTS[0], "amount_paise": 1}
    r = await client.post("/api/v1/events", json=changed, headers=service_headers)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


async def test_unknown_customer_is_404(
    client: httpx.AsyncClient, db: Session, service_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/events",
        json={**HERO_EVENTS[0], "customer_ref": "CUST-9999"},
        headers=service_headers,
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "CUSTOMER_NOT_FOUND"


async def test_payload_is_validated_by_event_type(
    client: httpx.AsyncClient, db: Session, service_headers: dict[str, str]
) -> None:
    bad = {**HERO_EVENTS[0], "payload": {"from_account": "XXXXXX3302", "to_account": "XXXXXX2201"}}
    r = await client.post("/api/v1/events", json=bad, headers=service_headers)
    assert r.status_code == 422


async def test_extra_fields_are_rejected(
    client: httpx.AsyncClient, db: Session, service_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/events", json={**HERO_EVENTS[0], "status": "EXECUTED"}, headers=service_headers
    )
    assert r.status_code == 422


async def test_payee_phone_is_hmaced_never_stored_raw(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hero_world(db, test_settings)
    r = await client.post("/api/v1/events", json=HERO_PAYEE, headers=service_headers)
    assert r.json()["stage_detected"] == "S3_NEW_PAYEE"
    payee = db.scalars(select(Payee).where(Payee.payee_ref == "PAY-0007-03")).one()
    assert payee.linked_msisdn_hmac and "9800000193" not in payee.linked_msisdn_hmac
    assert payee.linked_msisdn_last4 == "0193"
    stored = db.scalars(select(AccountEvent).where(AccountEvent.event_id == "EVT-P1-PAYEE")).one()
    assert "9800000193" not in str(stored.payload)


async def test_trusted_contact_change_is_encrypted_and_pending(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    world = hero_world(db, test_settings)
    event = {
        "event_id": "EVT-TC-1",
        "customer_ref": "CUST-0007",
        "event_type": "TRUSTED_CONTACT_CHANGED",
        "occurred_at": "2026-10-02T10:00:00+05:30",
        "payload": {
            "display_name": "New Person",
            "relationship": "friend",
            "phone_e164": "+919800000555",
            "preferred_language": "en",
        },
    }
    r = await client.post("/api/v1/events", json=event, headers=service_headers)
    assert r.status_code == 202
    db.expire_all()
    contacts = db.scalars(
        select(TrustedContact).where(TrustedContact.customer_id == world.customer.id)
    ).all()
    statuses = sorted(c.status.value for c in contacts)
    assert statuses == ["PENDING_ACTIVATION", "REVOKED"]
    new = next(c for c in contacts if c.status.value == "PENDING_ACTIVATION")
    assert "9800000555" not in new.phone_ciphertext
    assert (new.effective_from - new.registered_at).total_seconds() == 72 * 3600


async def test_service_key_required(client: httpx.AsyncClient) -> None:
    assert (await client.post("/api/v1/events", json=HERO_EVENTS[0])).status_code == 401
