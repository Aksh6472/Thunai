"""Demo control (FR-17, T-021). Only reachable when THUNAI_DEMO_MODE=true.

Uses the simulator package (sim/) for seeding and scenario runs: demo-only code paths.
"""

import logging
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.clock import SimClock
from app.core.errors import DemoModeDisabled, NotFound
from app.core.security import hmac_msisdn
from app.core.settings import Settings
from app.domain.enums import ActorType, FriRating
from app.models import FriMockRating
from app.schemas.demo import (
    ClockIn,
    ClockOut,
    ConsoleMessageOut,
    FriIn,
    FriOut,
    ResetOut,
    RunOut,
    ScenarioOut,
)
from app.services.audit_service import audit
from sim import runner as sim_runner
from sim import seed as sim_seed
from sim.scenarios.schema import Scenario, load_all

logger = logging.getLogger(__name__)


def ensure_demo(settings: Settings) -> None:
    if not settings.demo_mode:
        raise DemoModeDisabled()


def scenarios(state: Any) -> dict[str, Scenario]:
    if getattr(state, "scenarios", None) is None:
        state.scenarios = load_all()
    loaded: dict[str, Scenario] = state.scenarios
    return loaded


def list_scenarios(state: Any) -> list[ScenarioOut]:
    order = {"P": 0, "N": 1}
    return [
        ScenarioOut(
            id=s.id,
            title=s.title,
            label=s.label,
            customer_ref=s.customer.ref,
            customer_name=s.customer.display_name,
            description=s.description,
            expected_decision=s.expected.decision,
            expected_tier=s.expected.after_teller or s.expected.tier,
            held_out=s.held_out,
        )
        for s in sorted(scenarios(state).values(), key=lambda s: (order[s.id[0]], s.id))
    ]


def reset(session: Session, state: Any) -> ResetOut:
    started = time.perf_counter()
    sim_runner.cancel_all(state.demo_runs)
    state.demo_runs.clear()
    summary = sim_seed.seed(session, state.settings, scenarios=scenarios(state))
    if isinstance(state.clock, SimClock):
        state.clock.reload()
    state.console_notifier.clear()
    state.rate_limiter.enabled = state.settings.rate_limits_enabled
    audit(
        session,
        "DEMO_RESET",
        entity_type="demo",
        entity_id="reset",
        actor_type=ActorType.STAFF,
        details={"seed": summary.seed},
    )
    session.commit()
    return ResetOut(
        seconds=round(time.perf_counter() - started, 2),
        customers=summary.customers,
        seed=summary.seed,
        sim_now=state.clock.now(),
    )


def run(state: Any, asgi_app: Any, scenario_id: str, speed: float) -> RunOut:
    scenario = scenarios(state).get(scenario_id)
    if scenario is None:
        raise NotFound("scenario")
    settings: Settings = state.settings
    run_state = sim_runner.start_run(
        asgi_app,
        scenario,
        speed=speed,
        service_key=settings.service_api_key,
        teller_login=("teller.priya", settings.seed_password or ""),
        registry=state.demo_runs,
    )
    return run_out(run_state)


def run_out(run_state: sim_runner.RunState) -> RunOut:
    return RunOut(
        run_id=run_state.run_id,
        scenario_id=run_state.scenario_id,
        speed=run_state.speed,
        status=run_state.status,
        started_at=run_state.started_at,
        lines=list(run_state.lines),
        transfers=list(run_state.transfers),
        error=run_state.error,
    )


def runs(state: Any, limit: int) -> list[RunOut]:
    ordered = sorted(state.demo_runs.values(), key=lambda r: r.started_at, reverse=True)
    return [run_out(r) for r in ordered[:limit]]


def clock(state: Any) -> ClockOut:
    clock_ = state.clock
    if isinstance(clock_, SimClock):
        s = clock_.state()
        return ClockOut(sim_now=clock_.now(), speed=s.speed, running_scenario=s.running_scenario)
    return ClockOut(sim_now=clock_.now(), speed=1.0, running_scenario=None)


def set_clock(state: Any, body: ClockIn) -> ClockOut:
    clock_ = state.clock
    if not isinstance(clock_, SimClock):
        raise DemoModeDisabled("The simulated clock is not active.")
    clock_.set(body.sim_now, speed=body.speed, running_scenario=body.running_scenario)
    return clock(state)


def set_fri(session: Session, settings: Settings, body: FriIn, actor_id: str) -> FriOut:
    row = FriMockRating(
        msisdn_hmac=hmac_msisdn(body.linked_msisdn, settings),
        rating=FriRating(body.rating),
        updated_at=datetime.now(UTC),
    )
    merged = session.merge(row)
    audit(
        session,
        "FRI_SIMULATED_SET",
        entity_type="fri_mock_rating",
        entity_id=body.linked_msisdn[-4:],
        actor_type=ActorType.STAFF,
        actor_id=actor_id,
        details={"rating": body.rating},
    )
    session.commit()
    return FriOut(
        linked_msisdn_last4=body.linked_msisdn[-4:],
        rating=merged.rating.value,
        note="SIMULATED — not real DoT data",
    )


def console_messages(state: Any, limit: int) -> list[ConsoleMessageOut]:
    return [
        ConsoleMessageOut(at=m.at, to=m.to, text=m.text, link=m.link)
        for m in state.console_notifier.messages(limit)
    ]
