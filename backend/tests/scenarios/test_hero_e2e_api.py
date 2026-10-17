"""T-040a headless hero gate (M2): AC-01..AC-09 through the API on the seeded demo (seed 42).

Follows DEMO_SCRIPT.md: P1 replayed in simulated time → VERY_HIGH hold → teller checklist and
Tamil script → report draft → trusted contact reports a scam → officer cancels. Then N1 is allowed.
"""

import math
import re
from datetime import date, datetime

import httpx
import pytest
from fastapi import FastAPI

from app.core.settings import Settings
from sim.client import SimClient
from sim.plan import plan_scenario
from sim.replay import run_steps
from sim.scenarios.schema import load_all

pytestmark = pytest.mark.anyio


async def _login(c: httpx.AsyncClient, username: str, settings: Settings) -> dict[str, str]:
    r = await c.post("/auth/login", json={"username": username, "password": settings.seed_password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _replay(c: httpx.AsyncClient, settings: Settings, family: str) -> list[dict]:  # type: ignore[type-arg]
    results = await run_steps(
        SimClient(c, settings.service_api_key),
        plan_scenario(load_all()[family]),
        speed=math.inf,
        teller_login=("teller.priya", settings.seed_password or ""),
    )
    return [r.body for r in results if r.step.kind == "transfer"]


async def test_p1_watch_and_hold_then_full_response(
    demo_app: FastAPI, test_settings: Settings
) -> None:
    transport = httpx.ASGITransport(app=demo_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t/api/v1") as c:
        [hold] = await _replay(c, test_settings, "P1")
        officer = await _login(c, "officer.rao", test_settings)
        teller = await _login(c, "teller.priya", test_settings)

        # AC-01: the watch score rises on each of days 1–3, then the RTGS is held VERY_HIGH.
        assert (hold["decision"], hold["tier"], hold["score"], hold["raw_score"]) == (
            "HOLD",
            "VERY_HIGH",
            100,
            115,
        )
        customer = (await c.get("/customers?search=CUST-0007", headers=officer)).json()["items"][0]
        risk = (await c.get(f"/customers/{customer['id']}/risk", headers=officer)).json()
        best_per_day: dict[date, int] = {}
        for point in risk["episode"]["watch_history"]:
            day = datetime.fromisoformat(point["at"]).date()
            best_per_day[day] = max(best_per_day.get(day, 0), point["score"])
        assert list(best_per_day.values()) == [15, 40, 63]

        # AC-02: reasons sum to the raw score, each in English and Tamil.
        assert sum(r["points"] for r in hold["reasons"]) == hold["raw_score"]
        assert all(r["text_en"] and r["text_ta"] for r in hold["reasons"])

        # The teller sees the VERY_HIGH alert at the counter.
        queue = (await c.get("/teller/queue", headers=teller)).json()["items"]
        assert queue[0]["transfer_ref"] == "TRF-P1-0001" and queue[0]["tier"] == "VERY_HIGH"

        # AC-08: checklist (on a call + mentions police/CBI) re-scores with the new reasons.
        rescored = (
            await c.post(
                "/teller/transfers/TRF-P1-0001/checklist",
                json={"items": ["ON_CALL", "MENTIONS_AUTHORITY"]},
                headers=teller,
            )
        ).json()
        codes = {r["code"] for r in rescored["reasons"]}
        assert {"TELLER_ON_CALL", "TELLER_MENTIONS_AUTHORITY"} <= codes
        assert rescored["tier"] == "VERY_HIGH"

        # AC-09: script in Tamil and English, and a pre-filled report draft.
        hold_id = hold["hold_id"]
        for lang in ("ta", "en"):
            script = (
                await c.get(f"/teller/holds/{hold_id}/script?lang={lang}", headers=teller)
            ).json()
            assert len(script["steps"]) == 5
        report = (await c.post(f"/holds/{hold_id}/report", json={}, headers=teller)).json()
        tx = report["structured_fields"]["transaction"]
        assert (tx["amount_paise"], tx["beneficiary_ifsc"], tx["beneficiary_account_masked"]) == (
            460000000,
            "EXMP0001234",
            "XXXXXX4821",
        )
        assert report["structured_fields"]["helpline"] == "1930"
        assert len(report["structured_fields"]["timeline"]) >= 3

        # AC-04: the active trusted contact got a working link (console fallback).
        admin = await _login(c, "admin.demo", test_settings)
        [message] = (await c.get("/demo/console-messages", headers=admin)).json()
        token = re.search(r"/t/([A-Za-z0-9_\-]+)", message["link"]).group(1)  # type: ignore[union-attr]
        page = (await c.get(f"/trusted/{token}")).json()
        assert (page["customer_first_name"], page["amount_display"], page["language"]) == (
            "Kamala",
            "₹46,00,000",
            "ta",
        )

        # AC-07: a contact response alone never releases a VERY_HIGH hold.
        r = await c.post(f"/trusted/{token}/response", json={"response": "REPORT_SUSPICIOUS"})
        assert r.json()["result_key"] == "SENT_TO_OFFICER"
        # AC-05: the link is single use.
        assert (
            await c.post(f"/trusted/{token}/response", json={"response": "CONFIRM_GENUINE"})
        ).status_code == 410

        detail = (await c.get(f"/holds/{hold_id}", headers=officer)).json()
        assert (detail["status"], detail["contact_response"]) == (
            "AWAITING_OFFICER",
            "REPORT_SUSPICIOUS",
        )

        # AC-10 and the officer decision.
        no_note = await c.post(
            f"/holds/{hold_id}/officer-decision",
            json={"decision": "CANCEL_TRANSFER"},
            headers=officer,
        )
        assert no_note.status_code == 422
        done = (
            await c.post(
                f"/holds/{hold_id}/officer-decision",
                json={
                    "decision": "CANCEL_TRANSFER",
                    "note": "Customer confirmed a CBI 'digital arrest' call.",
                },
                headers=officer,
            )
        ).json()
        assert (done["status"], done["transfer"]["status"]) == ("CANCELLED", "CANCELLED")
        assert done["transfer"]["cancelled_reason"] == "CONTACT_REPORTED_SCAM_OFFICER_CONFIRMED"
        assert done["episode"]["status"] == "CLOSED_CONFIRMED_RISK"


async def test_n1_allowed(demo_app: FastAPI, test_settings: Settings) -> None:
    """AC-03: a genuine property instalment goes through with no friction."""
    transport = httpx.ASGITransport(app=demo_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t/api/v1") as c:
        [transfer] = await _replay(c, test_settings, "N1")
        assert (transfer["decision"], transfer["tier"], transfer["transfer_status"]) == (
            "ALLOW",
            "LOW",
            "EXECUTED",
        )
        officer = await _login(c, "officer.rao", test_settings)
        alerts = (await c.get("/alerts?kind=HOLD", headers=officer)).json()["items"]
        assert alerts == []
