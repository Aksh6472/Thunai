"""Background scenario runs for the demo panel (T-021, ARCHITECTURE §6).

The run is an asyncio task in the API process that still calls the API over HTTP semantics
(httpx ASGITransport), so the integration boundary stays intact. Nothing from app is imported:
the ASGI app is passed in.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from sim.client import SimClient
from sim.plan import plan_scenario
from sim.replay import run_steps
from sim.scenarios.schema import Scenario


@dataclass
class RunState:
    run_id: str
    scenario_id: str
    speed: float
    started_at: datetime
    status: str = "RUNNING"  # RUNNING | DONE | FAILED | CANCELLED
    lines: list[str] = field(default_factory=list)
    transfers: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    task: asyncio.Task[None] | None = None


def start_run(
    asgi_app: Any,
    scenario: Scenario,
    *,
    speed: float,
    service_key: str,
    teller_login: tuple[str, str],
    registry: dict[str, RunState],
) -> RunState:
    state = RunState(
        run_id=uuid.uuid4().hex[:12],
        scenario_id=scenario.id,
        speed=speed,
        started_at=datetime.now(UTC),
    )

    async def body() -> None:
        transport = httpx.ASGITransport(app=asgi_app)
        try:
            async with httpx.AsyncClient(
                transport=transport, base_url="http://thunai/api/v1", timeout=60
            ) as http:
                results = await run_steps(
                    SimClient(http, service_key),
                    plan_scenario(scenario),
                    speed=speed,
                    teller_login=teller_login,
                    on_line=state.lines.append,
                )
            state.transfers = [r.body for r in results if r.step.kind == "transfer"]
            state.status = "DONE"
        except asyncio.CancelledError:
            state.status = "CANCELLED"
            raise
        except Exception as exc:  # noqa: BLE001 (record any failure for the presenter)
            state.status = "FAILED"
            state.error = str(exc)[:300]

    state.task = asyncio.get_running_loop().create_task(body())
    registry[state.run_id] = state
    return state


def cancel_all(registry: dict[str, RunState]) -> None:
    for state in registry.values():
        if state.task is not None and not state.task.done():
            state.task.cancel()
