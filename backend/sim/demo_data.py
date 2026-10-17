"""Fill a running demo with sample activity (make demo-data): reset, then replay every family.

    uv run python -m sim.demo_data

All synthetic. Every scenario family is replayed instantly over HTTP so the Ops queue, the
watchlist, the teller console and the customer app all have something to show. P1 (the hero)
runs last, so the clock ends on its day-3 hold. Use `make demo-reset` for a clean stage demo.
"""

import asyncio
import math

import httpx

from app.core.settings import get_settings
from sim.client import SimClient
from sim.plan import plan_scenario
from sim.replay import run_steps
from sim.scenarios.schema import GOLDEN_SEED, load_all

HERO = "P1"


async def populate(base_url: str, service_key: str, password: str) -> list[str]:
    scenarios = load_all()
    order = sorted(s for s in scenarios if s != HERO) + [HERO]
    lines: list[str] = []
    async with httpx.AsyncClient(base_url=base_url, timeout=60) as http:
        login = await http.post(
            "/auth/login", json={"username": "admin.demo", "password": password}
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        reset = await http.post("/demo/reset", headers={"Authorization": f"Bearer {token}"})
        reset.raise_for_status()
        client = SimClient(http, service_key)
        for scenario_id in order:
            results = await run_steps(
                client,
                plan_scenario(scenarios[scenario_id], GOLDEN_SEED),
                speed=math.inf,
                teller_login=("teller.priya", password),
            )
            decisions = [
                f"{r.body.get('decision')} {r.body.get('tier')}"
                for r in results
                if r.step.kind == "transfer"
            ]
            lines.append(f"{scenario_id}: {', '.join(decisions) or 'no transfer'}")
    return lines


def main() -> None:
    settings = get_settings()
    lines = asyncio.run(
        populate(settings.api_base_url, settings.service_api_key, settings.seed_password or "")
    )
    for line in lines:
        print(line)  # noqa: T201 (CLI output)
    print(f"Sample data loaded: {len(lines)} synthetic scenario families.")  # noqa: T201


if __name__ == "__main__":
    main()
