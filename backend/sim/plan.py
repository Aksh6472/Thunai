"""Turn a scenario into timed API requests (FR-02). Seed 42 is exact; other seeds randomise."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sim.generator import DAY1, IST, scenario_params
from sim.scenarios.schema import (
    GOLDEN_SEED,
    CallStep,
    EventStep,
    Scenario,
    TellerStep,
    TransferStep,
)


@dataclass
class PlannedStep:
    at: datetime
    scenario_id: str
    kind: str  # event | call | transfer | teller
    path: str
    body: dict[str, Any]
    target: bool = False
    on_warn: str = "NONE"
    expected: dict[str, Any] = field(default_factory=dict)

    @property
    def transfer_ref(self) -> str | None:
        return self.body.get("transfer_ref")


def _nominal(day: int, hhmm: str) -> datetime:
    hh, mm = (int(x) for x in hhmm.split(":"))
    return datetime(DAY1.year, DAY1.month, DAY1.day, hh, mm, tzinfo=IST) + timedelta(days=day - 1)


def suffix(seed: int) -> str:
    return "" if seed == GOLDEN_SEED else f"-S{seed}"


def plan_scenario(scenario: Scenario, seed: int = GOLDEN_SEED) -> list[PlannedStep]:
    params = scenario_params(scenario, seed)
    tag = suffix(seed)
    first = _nominal(scenario.steps[0].day, scenario.steps[0].time)
    ref = scenario.customer.ref
    planned: list[PlannedStep] = []
    for index, step in enumerate(scenario.steps):
        nominal = _nominal(step.day, step.time)
        at = first + (nominal - first) * params.gap_scale
        iso = at.isoformat()
        if isinstance(step, EventStep):
            body: dict[str, Any] = {
                "event_id": f"EVT-{scenario.id}-{index:02d}{tag}",
                "customer_ref": ref,
                "event_type": step.type,
                "occurred_at": iso,
                "payload": dict(step.payload),
            }
            if step.account:
                body["account_ref"] = step.account
            if step.amount_rupees is not None:
                scale = params.amount_scale if step.scale_amount else 1.0
                body["amount_paise"] = round(step.amount_rupees * scale) * 100
            if step.type == "PAYEE_ADDED" and tag:
                body["payload"]["payee_ref"] = f"{step.payload['payee_ref']}{tag}"
            planned.append(PlannedStep(at, scenario.id, "event", "/events", body))
        elif isinstance(step, CallStep):
            body = {
                "customer_ref": ref,
                "call_type": step.call_type,
                "caller_known": step.caller_known,
                "duration_min": step.duration_min,
                "ended_at": iso if step.ended else None,
                "observed_at": iso,
            }
            planned.append(PlannedStep(at, scenario.id, "call", "/signals/call", body))
        elif isinstance(step, TransferStep):
            payee = step.payee
            if tag and not any(p.ref == payee for p in scenario.customer.payees):
                payee = f"{payee}{tag}"  # a payee added during this run
            body = {
                "transfer_ref": f"{step.ref}{tag}",
                "customer_ref": ref,
                "from_account": step.from_account,
                "payee_ref": payee,
                "amount_paise": round(step.amount_rupees * params.amount_scale) * 100,
                "rail": step.rail,
                "channel": step.channel,
                "initiated_at": iso,
                "scenario_label": scenario.id,
            }
            planned.append(
                PlannedStep(
                    at,
                    scenario.id,
                    "transfer",
                    "/transfers/assess",
                    body,
                    target=step.target,
                    on_warn=step.on_warn,
                    expected=scenario.expected.model_dump(),
                )
            )
        elif isinstance(step, TellerStep):
            body = {"items": list(step.items)}
            if step.customer_said:
                body["customer_said"] = step.customer_said
            planned.append(
                PlannedStep(
                    at,
                    scenario.id,
                    "teller",
                    f"/teller/transfers/{step.transfer_ref}{tag}/checklist",
                    body,
                )
            )
    return planned
