"""T-023/T-024: every family at seed 42 replayed through the API gives its expected decision."""

import math

import httpx
import pytest
from fastapi import FastAPI

from app.core.settings import Settings
from sim.client import SimClient
from sim.plan import plan_scenario
from sim.replay import run_steps
from sim.scenarios.schema import load_all

pytestmark = pytest.mark.anyio


async def test_all_families_match_expectations(demo_app: FastAPI, test_settings: Settings) -> None:
    transport = httpx.ASGITransport(app=demo_app)
    outcomes = {}
    async with httpx.AsyncClient(transport=transport, base_url="http://t/api/v1") as http:
        client = SimClient(http, test_settings.service_api_key)
        for family, scenario in sorted(load_all().items()):
            results = await run_steps(
                client,
                plan_scenario(scenario),
                speed=math.inf,
                teller_login=("teller.priya", test_settings.seed_password or ""),
            )
            first = next(r for r in results if r.step.kind == "transfer")
            teller = [r for r in results if r.step.kind == "teller"]
            outcomes[family] = (
                first.body["decision"],
                first.body["tier"],
                teller[-1].body["tier"] if teller else None,
            )
            assert first.body["decision"] == scenario.expected.decision, (family, first.body)
            if scenario.expected.tier:
                assert first.body["tier"] == scenario.expected.tier, (family, first.body)
            if scenario.expected.after_teller:
                assert teller[-1].body["tier"] == scenario.expected.after_teller, family
    assert len(outcomes) == 13
