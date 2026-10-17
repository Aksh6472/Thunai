"""T-014: hold lifecycle and officer decision (FR-11, FR-13, AC-10)."""

from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import FixedClock
from app.core.settings import Settings
from app.domain.enums import EpisodeStatus, Role
from app.models import AuditLog, RiskEpisode
from tests.scenario_helpers import hero_hold, staff_headers, wedding_hold

pytestmark = pytest.mark.anyio
NOTE = "Spoke with the customer and son in person; confirmed."


async def _decide(
    client: httpx.AsyncClient,
    hold_id: str,
    headers: dict[str, str],
    decision: str,
    note: str | None = NOTE,
) -> httpx.Response:
    body = {"decision": decision} | ({"note": note} if note is not None else {})
    return await client.post(
        f"/api/v1/holds/{hold_id}/officer-decision", json=body, headers=headers
    )


async def test_note_is_required(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    """AC-10."""
    hold = await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    for note in (None, "too short"):
        r = await _decide(client, hold["hold_id"], officer, "RELEASE", note)
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "NOTE_REQUIRED"


async def test_officer_cancel_closes_as_confirmed_risk(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hold = await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    r = await _decide(client, hold["hold_id"], officer, "CANCEL_TRANSFER")
    assert r.status_code == 200
    detail = r.json()
    assert detail["status"] == "CANCELLED"
    assert detail["transfer"]["status"] == "CANCELLED"
    assert detail["transfer"]["cancelled_reason"] == "OFFICER_CANCELLED"
    assert detail["resolution_note"] == NOTE
    assert detail["episode"]["status"] == "CLOSED_CONFIRMED_RISK"
    assert "HOLD_CANCELLED" in [a["action"] for a in detail["audit"]]


async def test_officer_release_executes_and_closes_benign(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hold = await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    detail = (await _decide(client, hold["hold_id"], officer, "RELEASE")).json()
    assert (detail["status"], detail["transfer"]["status"]) == ("RELEASED", "EXECUTED")
    assert detail["episode"]["status"] == "CLOSED_BENIGN"


async def test_second_decision_is_409(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hold = await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    await _decide(client, hold["hold_id"], officer, "CANCEL_TRANSFER")
    r = await _decide(client, hold["hold_id"], officer, "RELEASE")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


async def test_keep_holding_changes_nothing_but_is_audited(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hold = await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    detail = (await _decide(client, hold["hold_id"], officer, "KEEP_HOLDING")).json()
    assert detail["status"] == "AWAITING_OFFICER"
    assert detail["transfer"]["status"] == "HELD"
    actions = db.scalars(select(AuditLog.action)).all()
    assert "OFFICER_KEEP_HOLDING" in actions


@pytest.mark.parametrize("role", [Role.ADMIN, Role.TELLER])
async def test_only_officers_decide(
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
    role: Role,
) -> None:
    hold = await hero_hold(client, db, test_settings, service_headers)
    headers = staff_headers(db, test_settings, f"{role.value.lower()}.x", role)
    assert (await _decide(client, hold["hold_id"], headers, "RELEASE")).status_code == 403


async def test_other_branch_officer_gets_404(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hold = await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.blr", Role.OFFICER, branch="BLR001")
    assert (
        await client.get(f"/api/v1/holds/{hold['hold_id']}", headers=officer)
    ).status_code == 404
    assert (await _decide(client, hold["hold_id"], officer, "RELEASE")).status_code == 404


async def test_hold_detail_has_reasons_episode_and_contact(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hold = await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    detail = (await client.get(f"/api/v1/holds/{hold['hold_id']}", headers=officer)).json()
    assert detail["tier"] == "VERY_HIGH"
    assert detail["payee"]["masked_account"] == "XXXXXX4821"
    assert [p["score"] for p in detail["episode"]["watch_history"]][:4] == [15, 25, 25, 40]
    assert detail["trusted_contact"]["display_name"] == "Arun"
    assert detail["contact_requests"][0]["delivery_status"] == "SENT"
    assert "token" not in str(detail["contact_requests"]).lower()


async def test_cooling_off_expiry_moves_to_officer(
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
    clock: FixedClock,
) -> None:
    hold = await wedding_hold(client, db, test_settings, service_headers)
    assert hold["tier"] == "HIGH"
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    detail = (await client.get(f"/api/v1/holds/{hold['hold_id']}", headers=officer)).json()
    assert detail["status"] == "AWAITING_CONTACT"
    clock.advance(timedelta(minutes=241))
    detail = (await client.get(f"/api/v1/holds/{hold['hold_id']}", headers=officer)).json()
    assert detail["status"] == "AWAITING_OFFICER"


async def test_list_puts_very_high_first(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await wedding_hold(client, db, test_settings, service_headers)
    await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    page = (await client.get("/api/v1/holds?limit=1", headers=officer)).json()
    assert page["items"][0]["tier"] == "VERY_HIGH"
    assert page["next_cursor"]
    second = (
        await client.get(f"/api/v1/holds?limit=1&cursor={page['next_cursor']}", headers=officer)
    ).json()
    assert second["items"][0]["tier"] == "HIGH"
    assert second["next_cursor"] is None
    assert len(page["items"][0]["top_reasons"]) == 3


async def test_episode_closed_benign_on_release(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hold = await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    await _decide(client, hold["hold_id"], officer, "RELEASE")
    db.expire_all()
    statuses = {e.status for e in db.scalars(select(RiskEpisode)).all()}
    assert EpisodeStatus.CLOSED_BENIGN in statuses
