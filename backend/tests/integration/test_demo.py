"""T-021: demo control (FR-17, AC-16, SECURITY T-14)."""

import asyncio
import time

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import Role
from app.main import create_app
from tests.scenario_helpers import bearer, staff_headers

pytestmark = pytest.mark.anyio


async def _admin(app: FastAPI, settings: Settings) -> dict[str, str]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post(
            "/api/v1/auth/login",
            json={"username": "admin.demo", "password": settings.seed_password},
        )
        return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_demo_mode_off_is_403(test_settings: Settings, db: Session) -> None:
    app = create_app(test_settings.model_copy(update={"demo_mode": False}))
    transport = httpx.ASGITransport(app=app)
    headers = bearer(test_settings, "00000000-0000-0000-0000-000000000001", Role.ADMIN)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/api/v1/demo/scenarios", headers=headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "DEMO_MODE_DISABLED"


async def test_only_admin_controls_demo(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    teller = staff_headers(db, test_settings, "teller.x", Role.TELLER)
    assert (await client.post("/api/v1/demo/reset", headers=teller)).status_code == 403


async def test_reset_restores_seed_quickly_and_hero_runs(
    demo_app: FastAPI, test_settings: Settings
) -> None:
    """AC-16: reset ≤ 10 s, then the hero can be re-run immediately."""
    headers = await _admin(demo_app, test_settings)
    transport = httpx.ASGITransport(app=demo_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        started = time.perf_counter()
        r = await c.post("/api/v1/demo/reset", headers=headers)
        assert r.status_code == 200
        assert time.perf_counter() - started < 10
        assert r.json()["customers"] == 50
        scenarios = (await c.get("/api/v1/demo/scenarios", headers=headers)).json()
        assert scenarios[0]["id"] == "P1" and len(scenarios) == 13
        run = await c.post(
            "/api/v1/demo/scenarios/P1/run", json={"speed": 10_000_000}, headers=headers
        )
        assert run.status_code == 202
        run_id = run.json()["run_id"]
        for _ in range(200):
            runs = (await c.get("/api/v1/demo/runs", headers=headers)).json()
            if runs[0]["status"] != "RUNNING":
                break
            await asyncio.sleep(0.05)
        assert runs[0]["run_id"] == run_id
        assert runs[0]["status"] == "DONE", runs[0]
        assert runs[0]["transfers"][0]["tier"] == "VERY_HIGH"
        clock = (await c.get("/api/v1/demo/clock", headers=headers)).json()
        assert clock["sim_now"].startswith("2026-10-03")
        assert clock["running_scenario"] is None
        messages = (await c.get("/api/v1/demo/console-messages", headers=headers)).json()
        assert messages and "/t/" in messages[0]["link"]


async def test_fri_simulator(demo_app: FastAPI, test_settings: Settings) -> None:
    headers = await _admin(demo_app, test_settings)
    transport = httpx.ASGITransport(app=demo_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post(
            "/api/v1/demo/fri",
            json={"linked_msisdn": "+919800000999", "rating": "VERY_HIGH"},
            headers=headers,
        )
        assert r.json() == {
            "linked_msisdn_last4": "0999",
            "rating": "VERY_HIGH",
            "note": "SIMULATED — not real DoT data",
        }
        bad = await c.post(
            "/api/v1/demo/fri", json={"linked_msisdn": "98000", "rating": "HIGH"}, headers=headers
        )
        assert bad.status_code == 422
