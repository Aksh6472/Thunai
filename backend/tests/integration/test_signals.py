"""T-012: call signals (FR-06b, AC-11, NFR-08)."""

import httpx
import pytest
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import ConsentType
from tests.db_factories import grant_consent, hero_world, make_customer
from tests.hero_api import HERO_CALL_DAY2, HERO_EVENTS, replay_hero_until_transfer

pytestmark = pytest.mark.anyio


async def test_consent_required(
    client: httpx.AsyncClient, db: Session, service_headers: dict[str, str]
) -> None:
    make_customer(db, "CUST-0007")
    r = await client.post("/api/v1/signals/call", json=HERO_CALL_DAY2, headers=service_headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "CONSENT_REQUIRED"


async def test_revoked_consent_is_refused(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    world = hero_world(db, test_settings)
    grant_consent(db, world.customer, ConsentType.CALL_SIGNAL, granted=False)
    db.flush()
    # Revocation recorded later than the grant wins.
    from datetime import UTC, datetime

    from sqlalchemy import update

    from app.models import Consent

    db.execute(
        update(Consent)
        .where(Consent.customer_id == world.customer.id, Consent.granted.is_(False))
        .values(recorded_at=datetime(2026, 9, 1, tzinfo=UTC))
    )
    r = await client.post("/api/v1/signals/call", json=HERO_CALL_DAY2, headers=service_headers)
    assert r.status_code == 403


@pytest.mark.parametrize("field", ["caller_number", "app_name", "audio", "transcript"])
async def test_unknown_fields_rejected(
    client: httpx.AsyncClient, db: Session, service_headers: dict[str, str], field: str
) -> None:
    r = await client.post(
        "/api/v1/signals/call", json={**HERO_CALL_DAY2, field: "x"}, headers=service_headers
    )
    assert r.status_code == 422


async def test_call_signal_updates_watch_score(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hero_world(db, test_settings)
    for event in HERO_EVENTS:
        await client.post("/api/v1/events", json=event, headers=service_headers)
    r = await client.post("/api/v1/signals/call", json=HERO_CALL_DAY2, headers=service_headers)
    assert r.status_code == 202
    assert r.json()["episode"]["watch_score"] == 40
    assert r.json()["episode"]["watch_tier"] == "MEDIUM"


async def test_hero_watch_score_climbs_over_three_days(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    """AC-01 (watch part): 15 on day 1, 40 on day 2, 63 on day 3."""
    hero_world(db, test_settings)
    scores = await replay_hero_until_transfer(client, service_headers)
    # FD, pool 1, pool 2, call day 2, call day 3 morning (fresh), payee added
    assert scores == [15, 25, 25, 40, 40, 63]
