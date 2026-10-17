"""T-018: report drafts (FR-15, AC-09 report part)."""

import re

import httpx
import pytest
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import Role
from tests.scenario_helpers import hero_hold, staff_headers

pytestmark = pytest.mark.anyio


async def _draft(
    client: httpx.AsyncClient, db: Session, settings: Settings, headers: dict[str, str]
) -> tuple[dict, dict[str, str]]:  # type: ignore[type-arg]
    hold = await hero_hold(client, db, settings, headers)
    teller = staff_headers(db, settings, "teller.priya", Role.TELLER)
    r = await client.post(
        f"/api/v1/holds/{hold['hold_id']}/report", json={"use_llm": False}, headers=teller
    )
    assert r.status_code == 201, r.text
    return r.json(), teller


async def test_structured_fields_equal_db_values(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    report, _ = await _draft(client, db, test_settings, service_headers)
    tx = report["structured_fields"]["transaction"]
    assert (tx["amount_paise"], tx["rail"], tx["status"]) == (
        460000000,
        "RTGS",
        "HELD — not executed",
    )
    assert (
        tx["from_account_masked"],
        tx["beneficiary_ifsc"],
        tx["beneficiary_account_masked"],
    ) == ("XXXXXX2201", "EXMP0001234", "XXXXXX4821")
    assert report["structured_fields"]["helpline"] == "1930"
    assert report["structured_fields"]["portal"] == "https://cybercrime.gov.in"
    whats = [t["what"] for t in report["structured_fields"]["timeline"]]
    assert whats[0].startswith("Fixed deposit closed before maturity")
    assert report["narrative_source"] == "TEMPLATE"
    assert report["disclaimer"].startswith("Draft for officer review")


async def test_no_full_account_or_phone_number(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    report, _ = await _draft(client, db, test_settings, service_headers)
    text = str(report["structured_fields"]) + report["narrative_text"]
    assert not re.search(r"\d{9,}", text.replace("460000000", ""))
    for word in ("fraudster", "criminal", "victim"):
        assert word not in text.lower()


async def test_repeat_returns_existing(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    report, teller = await _draft(client, db, test_settings, service_headers)
    again = await client.post(f"/api/v1/holds/{report['hold_id']}/report", headers=teller)
    assert again.status_code == 200
    assert again.json()["id"] == report["id"]


async def test_patch_and_edit(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    report, teller = await _draft(client, db, test_settings, service_headers)
    url = f"/api/v1/reports/{report['id']}"
    r = await client.patch(
        url,
        json={"customer_reported": {"claimed_agency": "CBI", "platform": "WhatsApp video"}},
        headers=teller,
    )
    assert r.json()["narrative_source"] == "TEMPLATE"
    assert "CBI" in r.json()["narrative_text"]
    r = await client.patch(
        url, json={"narrative_text": "Officer-edited text.", "status": "READY"}, headers=teller
    )
    assert (r.json()["narrative_source"], r.json()["status"]) == ("EDITED", "READY")
    assert (
        await client.patch(url, json={"status": "FILED_EXTERNALLY"}, headers=teller)
    ).status_code == 422


async def test_mark_filed(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    report, teller = await _draft(client, db, test_settings, service_headers)
    url = f"/api/v1/reports/{report['id']}/mark-filed"
    assert (
        await client.post(url, json={"acknowledgement_number": "ACK-1"}, headers=teller)
    ).status_code == 403
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    assert (
        await client.post(url, json={"acknowledgement_number": "bad ack!"}, headers=officer)
    ).status_code == 422
    r = await client.post(url, json={"acknowledgement_number": "NCRP/2026/0001"}, headers=officer)
    assert (r.json()["status"], r.json()["acknowledgement_number"]) == (
        "FILED_EXTERNALLY",
        "NCRP/2026/0001",
    )
    late = await client.patch(
        f"/api/v1/reports/{report['id']}", json={"status": "READY"}, headers=officer
    )
    assert late.status_code == 409


async def test_llm_request_falls_back_when_disabled(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hold = await hero_hold(client, db, test_settings, service_headers)
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    r = await client.post(
        f"/api/v1/holds/{hold['hold_id']}/report", json={"use_llm": True}, headers=teller
    )
    assert r.status_code == 201
    assert r.headers["x-thunai-llm-fallback"] == "LLM_DISABLED"
    assert r.json()["narrative_source"] == "TEMPLATE"
