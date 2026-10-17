"""Engine input and output types (AI_DESIGN §3). Pure data, JSON-serialisable for input_snapshot."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    BaselineConfidence,
    CallType,
    Channel,
    Decision,
    EpisodeStatus,
    EventType,
    FriRating,
    HoldStatus,
    Rail,
    Stage,
    TellerItem,
    Tier,
)


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------- Baseline (§4) ----------


class OutboundDebit(_Model):
    amount_paise: int = Field(ge=0)
    occurred_at: datetime
    to_own_account: bool = False


class FdClosure(_Model):
    closed_at: datetime
    maturity_date: date


class Baseline(_Model):
    history_days: int = Field(ge=0)
    median_outbound_paise: int = Field(gt=0)
    p95_outbound_paise: int = Field(ge=0)
    qualifying_transfer_count: int = Field(ge=0)
    premature_fd_closures_365d: int = Field(ge=0)
    confidence: BaselineConfidence
    algorithm_version: str = "baseline_v1"


# ---------- Events, stages and episodes (§5) ----------


class EventFacts(_Model):
    """What the stage tracker needs to know about one account event."""

    event_id: str
    event_type: EventType
    occurred_at: datetime
    amount_paise: int | None = None
    maturity_date: date | None = None  # FD_CLOSED
    to_account: str | None = None  # INTERNAL_TRANSFER_IN target, or FD proceeds account
    payee_id: str | None = None  # PAYEE_ADDED


class StageEvent(_Model):
    stage: Stage
    event_id: str
    occurred_at: datetime
    amount_paise: int | None = None
    payee_id: str | None = None


class WatchPoint(_Model):
    at: datetime
    score: int
    tier: Tier
    trigger_event_id: str


class Episode(_Model):
    status: EpisodeStatus
    opened_at: datetime
    last_stage_at: datetime
    closed_at: datetime | None = None
    stages: tuple[StageEvent, ...] = ()
    watch_score: int = 0
    watch_tier: Tier = Tier.LOW
    watch_history: tuple[WatchPoint, ...] = ()


# ---------- Signals (§6.1) ----------


class CallSignal(_Model):
    """Consented flag only: no caller number, app name or content (NFR-08)."""

    call_type: CallType
    caller_known: bool
    duration_min: int = Field(ge=0, le=1440)
    ended_at: datetime | None = None
    observed_at: datetime


class Signals(_Model):
    fri_rating: FriRating | None = None
    fri_unavailable: bool = False
    fri_linked_msisdn_last4: str | None = None
    call: CallSignal | None = None
    teller_items: tuple[TellerItem, ...] = ()
    trusted_contact_changed_at: datetime | None = None


# ---------- Transfer assessment (§3) ----------


class PayeeFacts(_Model):
    payee_id: str
    payee_ref: str
    added_at: datetime
    prior_successful_transfers: int = Field(ge=0)
    recurring_amount_paise: int | None = None


class TransferFacts(_Model):
    transfer_ref: str
    amount_paise: int = Field(gt=0)
    rail: Rail
    channel: Channel
    initiated_at: datetime
    source_account_balance_paise: int = Field(ge=0)
    payee: PayeeFacts


class AssessmentInput(_Model):
    """Everything the engine sees. Deliberately no age, gender, location or language (ADR-010)."""

    customer_id: str
    now: datetime
    baseline: Baseline
    episode_stages: tuple[StageEvent, ...] = ()
    transfer: TransferFacts
    signals: Signals = Signals()
    has_active_trusted_contact: bool = False


class Reason(_Model):
    code: str
    points: int
    stage: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    text_en: str
    text_ta: str


class Assessment(_Model):
    raw_score: int
    score: int = Field(ge=0, le=100)
    tier: Tier
    decision: Decision
    overrides_applied: tuple[str, ...] = ()
    initial_hold_status: HoldStatus | None = None
    reasons: tuple[Reason, ...]
    config_version: str
    is_s4: bool = False
