"""Ops dashboard DTOs (API_SPEC §10)."""

from datetime import date, datetime
from typing import Any, Literal

from app.domain.enums import Channel, Tier
from app.schemas.common import ResponseModel
from app.schemas.transfers import CustomerBrief, EpisodeOut, ReasonOut, TrustedContactBrief


class Summary(ResponseModel):
    active_holds: int
    awaiting_contact: int
    awaiting_officer: int
    warnings_today: int
    watchlist_count: int
    amount_on_hold_paise: int
    data_label: Literal["SYNTHETIC"] = "SYNTHETIC"


class AlertItem(ResponseModel):
    kind: Literal["HOLD", "WARN", "WATCH"]
    id: str
    customer: CustomerBrief
    tier: Tier
    status: str
    amount_paise: int | None = None
    channel: Channel | None = None
    transfer_ref: str | None = None
    hold_id: str | None = None
    contact_response: str | None = None
    top_reason: ReasonOut | None = None
    watch_score: int | None = None
    created_at: datetime
    cooling_off_until: datetime | None = None


class CustomerListItem(ResponseModel):
    id: str
    external_ref: str
    display_name: str
    preferred_language: str
    branch_code: str


class BaselineOut(ResponseModel):
    history_days: int
    median_outbound_paise: int
    p95_outbound_paise: int
    qualifying_transfer_count: int
    premature_fd_closures_365d: int
    confidence: str
    computed_at: datetime


class AccountBrief(ResponseModel):
    masked_number: str
    account_type: str
    balance_paise: int
    status: str
    maturity_date: date | None


class RecentAssessment(ResponseModel):
    transfer_ref: str
    amount_paise: int
    decision: str
    tier: Tier
    score: int
    trigger: str
    assessed_at: datetime
    transfer_status: str
    hold_id: str | None


class CustomerRisk(ResponseModel):
    customer: CustomerBrief
    preferred_language: str
    accounts: list[AccountBrief]
    baseline: BaselineOut | None
    episode: EpisodeOut | None
    trusted_contact: TrustedContactBrief | None
    recent_assessments: list[RecentAssessment]


class TimelineItem(ResponseModel):
    at: datetime
    kind: Literal["EVENT", "SIGNAL", "TRANSFER", "ASSESSMENT", "HOLD"]
    title: str
    stage: str | None = None
    amount_paise: int | None = None
    detail: dict[str, Any] = {}
