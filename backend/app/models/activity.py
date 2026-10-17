"""Events, transfers, signals, baselines, episodes and assessments (DATABASE_SCHEMA §3.7–3.12)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import (
    AssessmentTrigger,
    BaselineConfidence,
    CancelledReason,
    Channel,
    Decision,
    EpisodeStatus,
    EventType,
    Rail,
    SignalSource,
    SignalType,
    Stage,
    Tier,
    TransferStatus,
)
from app.models.base import Base, StrEnumType, created_at_column, enum_check, uuid_pk


class AccountEvent(Base):
    __tablename__ = "account_events"
    __table_args__ = (
        enum_check("event_type", EventType),
        CheckConstraint(
            "stage IS NULL OR stage IN ('S1_LIQUIDATION', 'S2_POOLING', 'S3_NEW_PAYEE')",
            name="stage_valid",
        ),
        CheckConstraint("amount_paise IS NULL OR amount_paise >= 0", name="amount_non_negative"),
        Index("ix_account_events_customer_occurred", "customer_id", text("occurred_at DESC")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[str] = mapped_column(unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"))
    account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id"))
    event_type: Mapped[EventType] = mapped_column(StrEnumType(EventType, 32))
    amount_paise: Mapped[int | None]
    occurred_at: Mapped[datetime]
    payload: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    stage: Mapped[Stage | None] = mapped_column(StrEnumType(Stage, 16))
    request_hash: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = created_at_column()


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="amount_positive"),
        enum_check("rail", Rail),
        enum_check("channel", Channel),
        enum_check("status", TransferStatus),
        enum_check("cancelled_reason", CancelledReason, nullable=True),
        Index("ix_transfers_customer_initiated", "customer_id", text("initiated_at DESC")),
        Index("ix_transfers_status", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    transfer_ref: Mapped[str] = mapped_column(unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"))
    from_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    payee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payees.id"), index=True)
    amount_paise: Mapped[int]
    rail: Mapped[Rail] = mapped_column(StrEnumType(Rail, 8))
    channel: Mapped[Channel] = mapped_column(StrEnumType(Channel, 16))
    status: Mapped[TransferStatus] = mapped_column(StrEnumType(TransferStatus, 16))
    initiated_at: Mapped[datetime]
    decided_at: Mapped[datetime | None]
    executed_at: Mapped[datetime | None]
    cancelled_reason: Mapped[CancelledReason | None] = mapped_column(
        StrEnumType(CancelledReason, 48)
    )
    # Evaluation only. The engine never reads it (enforced by tests/test_architecture.py).
    scenario_label: Mapped[str | None] = mapped_column(String(8))
    request_hash: Mapped[str] = mapped_column(String(64))


class CustomerBaseline(Base):
    __tablename__ = "customer_baselines"
    __table_args__ = (enum_check("confidence", BaselineConfidence),)

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), primary_key=True)
    computed_at: Mapped[datetime]
    history_days: Mapped[int]
    median_outbound_paise: Mapped[int]
    p95_outbound_paise: Mapped[int]
    qualifying_transfer_count: Mapped[int]
    premature_fd_closures_365d: Mapped[int]
    confidence: Mapped[BaselineConfidence] = mapped_column(StrEnumType(BaselineConfidence, 4))
    algorithm_version: Mapped[str]


class RiskEpisode(Base):
    __tablename__ = "risk_episodes"
    __table_args__ = (
        enum_check("status", EpisodeStatus),
        enum_check("watch_tier", Tier),
        CheckConstraint("watch_score BETWEEN 0 AND 100", name="watch_score_range"),
        Index(
            "uq_risk_episodes_one_open",
            "customer_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[EpisodeStatus] = mapped_column(StrEnumType(EpisodeStatus, 24))
    opened_at: Mapped[datetime]
    last_stage_at: Mapped[datetime]
    closed_at: Mapped[datetime | None]
    stages: Mapped[list[Any]]
    watch_score: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    watch_tier: Mapped[Tier] = mapped_column(StrEnumType(Tier, 16))
    watch_history: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        enum_check("signal_type", SignalType),
        enum_check("source", SignalSource),
        Index(
            "ix_signals_customer_type_observed",
            "customer_id",
            "signal_type",
            text("observed_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"))
    transfer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transfers.id"))
    signal_type: Mapped[SignalType] = mapped_column(StrEnumType(SignalType, 24))
    value: Mapped[dict[str, Any]]
    source: Mapped[SignalSource] = mapped_column(StrEnumType(SignalSource, 24))
    observed_at: Mapped[datetime]
    recorded_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"))


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        enum_check("trigger", AssessmentTrigger),
        enum_check("tier", Tier),
        enum_check("decision", Decision),
        CheckConstraint("score BETWEEN 0 AND 100", name="score_range"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    transfer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transfers.id"), index=True)
    episode_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("risk_episodes.id"))
    trigger: Mapped[AssessmentTrigger] = mapped_column(StrEnumType(AssessmentTrigger, 24))
    raw_score: Mapped[int] = mapped_column(SmallInteger)
    score: Mapped[int] = mapped_column(SmallInteger)
    tier: Mapped[Tier] = mapped_column(StrEnumType(Tier, 16))
    decision: Mapped[Decision] = mapped_column(StrEnumType(Decision, 8))
    reasons: Mapped[list[Any]]
    overrides_applied: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    input_snapshot: Mapped[dict[str, Any]]
    config_version: Mapped[str]
    assessed_at: Mapped[datetime]
