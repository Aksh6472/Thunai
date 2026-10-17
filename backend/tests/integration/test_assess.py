"""T-013: transfer assessment (FR-09, AC-01/02/03/15, NFR-09, ADR-014)."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import Role
from app.domain.models import AssessmentInput
from app.domain.scoring import assess
from app.integrations.fri.mock import MockFriClient
from app.models import RiskAssessment, Transfer
from app.services import assessment_service
from tests.db_factories import hero_world
from tests.factories import cfg
from tests.hero_api import HERO_TRANSFER, replay_hero_until_transfer
from tests.scenario_helpers import (
    IQBAL_EVENTS,
    IQBAL_TRANSFER,
    hero_hold,
    iqbal_world,
    staff_headers,
)

pytestmark = pytest.mark.anyio


async def test_hero_is_held_very_high(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    body = await hero_hold(client, db, test_settings, service_headers)
    assert (body["decision"], body["tier"], body["score"], body["raw_score"]) == (
        "HOLD",
        "VERY_HIGH",
        100,
        115,
    )
    assert body["transfer_status"] == "HELD"
    assert body["hold_id"]
    assert len(body["reasons"]) == 8
    assert body["config_version"] == "scoring_v1@2026-10-17"


async def test_reasons_sum_to_raw_score_with_both_languages(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    """AC-02."""
    body = await hero_hold(client, db, test_settings, service_headers)
    assert sum(r["points"] for r in body["reasons"]) == body["raw_score"]
    assert all(r["text_en"] and r["text_ta"] for r in body["reasons"])


async def test_hero_hold_notifies_active_contact(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    """AC-04: the console message carries a working link."""
    await hero_hold(client, db, test_settings, service_headers)
    [message] = app.state.console_notifier.messages(5)
    assert "/t/" in (message.link or "")
    assert "₹46,00,000" in message.text and "Kamala" in message.text


async def test_n1_is_allowed_and_executed(
    client: httpx.AsyncClient, db: Session, service_headers: dict[str, str]
) -> None:
    """AC-03."""
    iqbal_world(db)
    for event in IQBAL_EVENTS:
        assert (
            await client.post("/api/v1/events", json=event, headers=service_headers)
        ).status_code == 202
    r = await client.post("/api/v1/transfers/assess", json=IQBAL_TRANSFER, headers=service_headers)
    body = r.json()
    assert (body["decision"], body["tier"], body["raw_score"]) == ("ALLOW", "LOW", 5), body
    assert body["transfer_status"] == "EXECUTED"
    assert body["hold_id"] is None


async def test_idempotent_replay_and_conflict(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    """AC-15."""
    first = await hero_hold(client, db, test_settings, service_headers)
    again = await client.post(
        "/api/v1/transfers/assess", json=HERO_TRANSFER, headers=service_headers
    )
    assert again.status_code == 200
    assert again.headers["idempotent-replay"] == "true"
    assert again.json()["assessment_id"] == first["assessment_id"]
    assert (
        len(db.scalars(select(Transfer).where(Transfer.transfer_ref == "TRF-P1-0001")).all()) == 1
    )
    changed = await client.post(
        "/api/v1/transfers/assess",
        json={**HERO_TRANSFER, "amount_paise": 1000},
        headers=service_headers,
    )
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


async def test_fri_timeout_gives_info_reason_and_still_holds(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    app.state.fri_client = MockFriClient(timeout_ms=50, latency_ms=100)
    body = await hero_hold(client, db, test_settings, service_headers)
    codes = {r["code"]: r["points"] for r in body["reasons"]}
    assert codes.get("FRI_UNAVAILABLE") == 0
    assert "FRI_RISK" not in codes
    assert (body["raw_score"], body["decision"]) == (95, "HOLD")


async def test_engine_failure_is_503_never_allow(
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hero_world(db, test_settings)
    await replay_hero_until_transfer(client, service_headers)

    def boom(*_: object, **__: object) -> None:
        raise RuntimeError("engine exploded")

    monkeypatch.setattr(assessment_service, "assess", boom)
    r = await client.post("/api/v1/transfers/assess", json=HERO_TRANSFER, headers=service_headers)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "ASSESSMENT_UNAVAILABLE"
    assert (
        db.scalars(select(Transfer).where(Transfer.transfer_ref == "TRF-P1-0001")).first() is None
    )


async def test_input_snapshot_replays_to_identical_result(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    """NFR-09: stored input + config version reproduce the decision."""
    body = await hero_hold(client, db, test_settings, service_headers)
    row = db.get(RiskAssessment, __import__("uuid").UUID(body["assessment_id"]))
    assert row is not None
    replayed = assess(AssessmentInput.model_validate(row.input_snapshot), cfg())
    assert replayed.raw_score == row.raw_score
    assert [r.model_dump(mode="json") for r in replayed.reasons] == row.reasons
    assert "scenario_label" not in str(row.input_snapshot)


async def test_unknown_payee_is_404(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hero_world(db, test_settings)
    r = await client.post("/api/v1/transfers/assess", json=HERO_TRANSFER, headers=service_headers)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "PAYEE_NOT_FOUND"


async def test_jwt_on_service_route_is_403(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    headers = staff_headers(db, test_settings, "teller.x", Role.TELLER)
    r = await client.post("/api/v1/transfers/assess", json=HERO_TRANSFER, headers=headers)
    assert r.status_code == 403


async def test_staff_can_read_transfer(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await hero_hold(client, db, test_settings, service_headers)
    headers = staff_headers(db, test_settings, "teller.y", Role.TELLER)
    r = await client.get("/api/v1/transfers/TRF-P1-0001", headers=headers)
    assert r.status_code == 200
    assert r.json()["tier"] == "VERY_HIGH"
    other = staff_headers(db, test_settings, "teller.z", Role.TELLER, branch="BLR001")
    assert (await client.get("/api/v1/transfers/TRF-P1-0001", headers=other)).status_code == 404
