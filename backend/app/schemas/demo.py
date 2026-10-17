"""Demo control DTOs (API_SPEC §11). Demo mode only."""

from datetime import datetime
from typing import Any, Literal

from pydantic import AwareDatetime, Field

from app.schemas.common import RequestModel, ResponseModel
from app.schemas.events import E164


class ScenarioOut(ResponseModel):
    id: str
    title: str
    label: Literal["coercion", "genuine"]
    customer_ref: str
    customer_name: str
    description: str
    expected_decision: str
    expected_tier: str | None
    held_out: bool


class ResetOut(ResponseModel):
    seconds: float
    customers: int
    seed: int
    sim_now: datetime


class RunIn(RequestModel):
    speed: float = Field(default=4320, gt=0, le=10_000_000)


class RunOut(ResponseModel):
    run_id: str
    scenario_id: str
    speed: float
    status: str
    started_at: datetime
    lines: list[str]
    transfers: list[dict[str, Any]]
    error: str | None


class ClockIn(RequestModel):
    sim_now: AwareDatetime
    speed: float = Field(default=0, ge=0, le=10_000_000)
    running_scenario: str | None = Field(default=None, max_length=8)


class ClockOut(ResponseModel):
    sim_now: datetime
    speed: float
    running_scenario: str | None


class FriIn(RequestModel):
    linked_msisdn: E164
    rating: Literal["MEDIUM", "HIGH", "VERY_HIGH"]


class FriOut(ResponseModel):
    linked_msisdn_last4: str
    rating: str
    note: str


class ConsoleMessageOut(ResponseModel):
    at: datetime
    to: str
    text: str
    link: str | None
