"""Replay scenario families against the API in simulated time (FR-02, T-024).

    uv run python -m sim.replay --scenario P1 --speed 4320

Speed is simulated seconds per real second (4320: three days in about a minute).
"""

import argparse
import asyncio
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.settings import get_settings
from sim.client import SimClient
from sim.plan import PlannedStep, plan_scenario
from sim.scenarios.schema import GOLDEN_SEED, load_all

MAX_SLEEP_SECONDS = 30.0  # keep long quiet gaps (e.g. 4 simulated days) watchable on stage


@dataclass
class StepResult:
    step: PlannedStep
    status: int
    body: dict[str, Any]


@dataclass
class ReplayResult:
    scenario_id: str
    results: list[StepResult] = field(default_factory=list)

    def transfers(self) -> list[StepResult]:
        return [r for r in self.results if r.step.kind == "transfer"]


def describe(result: StepResult) -> str:
    s, b = result.step, result.body
    when = s.at.strftime("%d %b %H:%M")
    if s.kind == "transfer":
        return (
            f"{when} {s.scenario_id} transfer {b.get('transfer_ref')}: {b.get('decision')} "
            f"{b.get('tier')} score {b.get('score')} (raw {b.get('raw_score')})"
        )
    if s.kind == "teller":
        return f"{when} {s.scenario_id} teller checklist → {b.get('decision')} {b.get('tier')}"
    episode = b.get("episode") or {}
    label = s.body.get("event_type", "CALL_SIGNAL")
    stage = b.get("stage_detected")
    watch = f" watch {episode.get('watch_score')} {episode.get('watch_tier')}" if episode else ""
    return f"{when} {s.scenario_id} {label}{' → ' + stage if stage else ''}{watch}"


async def run_steps(
    client: SimClient,
    steps: list[PlannedStep],
    *,
    speed: float,
    teller_login: tuple[str, str] | None = None,
    on_line: Callable[[str], None] = lambda _: None,
) -> list[StepResult]:
    """speed = math.inf replays instantly (tests, evaluation).

    The clock is frozen at the step's exact time while the step is posted, so every decision
    sees the scenario's time regardless of speed; it runs at `speed` only while waiting for the
    next step (so the demo clock visibly moves).
    """
    results: list[StepResult] = []
    previous = None
    for step in steps:
        if previous is not None and not math.isinf(speed):
            await client.set_clock(previous, speed, step.scenario_id)
            gap = (step.at - previous).total_seconds() / speed
            await asyncio.sleep(min(max(gap, 0.0), MAX_SLEEP_SECONDS))
        previous = step.at
        await client.set_clock(step.at, 0.0, step.scenario_id)
        if step.kind == "teller":
            if teller_login is None:
                raise RuntimeError("teller steps need a teller login")
            response = await client.teller_post(step.path, step.body, *teller_login)
        else:
            response = await client.post(step.path, step.body)
        body = response.json() if response.content else {}
        if response.status_code >= 400:
            raise RuntimeError(f"{step.path} → {response.status_code}: {body}")
        result = StepResult(step, response.status_code, body)
        results.append(result)
        on_line(describe(result))
        if step.kind == "transfer" and body.get("decision") == "WARN" and step.on_warn != "NONE":
            ref = step.body["transfer_ref"]
            await client.post(f"/transfers/{ref}/warning-response", {"action": step.on_warn})
            on_line(f"    customer chose {step.on_warn} on the warning")
    if steps:
        await client.set_clock(steps[-1].at, 0.0, None)
    return results


async def replay(
    scenario_id: str,
    *,
    speed: float,
    seed: int,
    base_url: str,
    service_key: str,
    teller: tuple[str, str],
) -> ReplayResult:
    scenario = load_all()[scenario_id]
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as http:
        client = SimClient(http, service_key)
        results = await run_steps(
            client, plan_scenario(scenario, seed), speed=speed, teller_login=teller, on_line=print
        )
    return ReplayResult(scenario_id, results)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a scenario family over HTTP.")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--speed", type=float, default=None, help="sim seconds per real second")
    parser.add_argument("--seed", type=int, default=GOLDEN_SEED)
    args = parser.parse_args()
    settings = get_settings()
    asyncio.run(
        replay(
            args.scenario,
            speed=args.speed or settings.sim_default_speed,
            seed=args.seed,
            base_url=settings.api_base_url,
            service_key=settings.service_api_key,
            teller=("teller.priya", settings.seed_password or ""),
        )
    )


if __name__ == "__main__":
    main()
