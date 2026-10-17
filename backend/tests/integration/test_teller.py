"""T-017: teller queue, checklist re-score (escalate only), script (AC-08, AC-09 script part)."""

import httpx
import pytest
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import Role
from tests.scenario_helpers import (
    IQBAL_EVENTS,
    IQBAL_TRANSFER,
    WEDDING_EVENTS,
    WEDDING_TRANSFER,
    hero_hold,
    iqbal_world,
    staff_headers,
    wedding_world,
)

pytestmark = pytest.mark.anyio
CHECK = "/api/v1/teller/transfers/{ref}/checklist"


async def test_queue_shows_branch_hold(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await hero_hold(client, db, test_settings, service_headers)
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    items = (await client.get("/api/v1/teller/queue", headers=teller)).json()["items"]
    assert [(i["transfer_ref"], i["tier"], i["channel"]) for i in items] == [
        ("TRF-P1-0001", "VERY_HIGH", "BRANCH")
    ]


async def test_checklist_rescore(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    """AC-08: on a call + mentions police/CBI → re-scored, new reasons present."""
    await hero_hold(client, db, test_settings, service_headers)
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    r = await client.post(
        CHECK.format(ref="TRF-P1-0001"),
        json={"items": ["ON_CALL", "MENTIONS_AUTHORITY"]},
        headers=teller,
    )
    assert r.status_code == 200
    body = r.json()
    points = {x["code"]: x["points"] for x in body["reasons"]}
    assert (points["TELLER_ON_CALL"], points["TELLER_MENTIONS_AUTHORITY"]) == (8, 15)
    assert body["raw_score"] == 138
    assert (body["trigger"], body["decision"], body["tier"]) == (
        "TELLER_CHECKLIST",
        "HOLD",
        "VERY_HIGH",
    )


async def test_customer_said_never_changes_the_score(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await hero_hold(client, db, test_settings, service_headers)
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    a = (
        await client.post(
            CHECK.format(ref="TRF-P1-0001"), json={"items": ["DISTRESSED"]}, headers=teller
        )
    ).json()
    b = (
        await client.post(
            CHECK.format(ref="TRF-P1-0001"),
            json={"items": ["DISTRESSED"], "customer_said": "Says it is for a property purchase."},
            headers=teller,
        )
    ).json()
    assert a["raw_score"] == b["raw_score"]
    assert [r["code"] for r in a["reasons"]] == [r["code"] for r in b["reasons"]]


async def test_high_escalates_to_very_high(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    wedding_world(db, test_settings)
    for event in WEDDING_EVENTS:
        await client.post("/api/v1/events", json=event, headers=service_headers)
    initial = (
        await client.post(
            "/api/v1/transfers/assess",
            json={**WEDDING_TRANSFER, "channel": "BRANCH"},
            headers=service_headers,
        )
    ).json()
    assert initial["tier"] == "HIGH"
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    r = await client.post(
        CHECK.format(ref="TRF-N4-0001"),
        json={"items": ["ON_CALL", "MENTIONS_AUTHORITY"]},
        headers=teller,
    )
    assert r.json()["tier"] == "VERY_HIGH"
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    detail = (await client.get(f"/api/v1/holds/{initial['hold_id']}", headers=officer)).json()
    assert (detail["tier"], detail["status"]) == ("VERY_HIGH", "AWAITING_OFFICER")


async def test_no_de_escalation(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await hero_hold(client, db, test_settings, service_headers)
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    body = (
        await client.post(CHECK.format(ref="TRF-P1-0001"), json={"items": []}, headers=teller)
    ).json()
    assert (body["decision"], body["tier"]) == ("HOLD", "VERY_HIGH")


async def test_checklist_after_execution_is_409(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    iqbal_world(db)
    for event in IQBAL_EVENTS:
        await client.post("/api/v1/events", json=event, headers=service_headers)
    await client.post("/api/v1/transfers/assess", json=IQBAL_TRANSFER, headers=service_headers)
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    r = await client.post(
        CHECK.format(ref="TRF-N1-0001"), json={"items": ["ON_CALL"]}, headers=teller
    )
    assert r.status_code == 409


async def test_script_langs(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    """AC-09 (script part)."""
    hold = await hero_hold(client, db, test_settings, service_headers)
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    ta = (
        await client.get(f"/api/v1/teller/holds/{hold['hold_id']}/script?lang=ta", headers=teller)
    ).json()
    en = (
        await client.get(f"/api/v1/teller/holds/{hold['hold_id']}/script?lang=en", headers=teller)
    ).json()
    assert [s["id"] for s in ta["steps"]] == [
        "greet",
        "no_digital_arrest",
        "ask_family",
        "offer_1930",
        "do_not",
    ]
    assert any("஀" <= ch <= "௿" for ch in ta["steps"][1]["text"])
    assert "digital arrest" in en["steps"][1]["text"]
    assert ta["reviewed_by_native_speaker"] is False  # pending T-038
    assert ta["tier"] == "VERY_HIGH"


async def test_unknown_checklist_item_rejected(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await hero_hold(client, db, test_settings, service_headers)
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    r = await client.post(
        CHECK.format(ref="TRF-P1-0001"), json={"items": ["AGE_OVER_70"]}, headers=teller
    )
    assert r.status_code == 422
