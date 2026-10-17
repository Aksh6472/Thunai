"""Holds, contact requests, reports, audit, simulated FRI, sim state (DATABASE_SCHEMA §3.13+)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import (
    ActorType,
    ContactResponse,
    DeliveryChannel,
    DeliveryStatus,
    FriRating,
    HoldStatus,
    HoldTier,
    NarrativeSource,
    ReportStatus,
    ResolvedByType,
)
from app.models.base import Base, StrEnumType, created_at_column, enum_check, uuid_pk


class Hold(Base):
    __tablename__ = "holds"
    __table_args__ = (
        enum_check("tier", HoldTier),
        enum_check("status", HoldStatus),
        enum_check("contact_response", ContactResponse, nullable=True),
        enum_check("resolved_by_type", ResolvedByType, nullable=True),
        CheckConstraint(
            "resolution_note IS NULL OR char_length(resolution_note) <= 1000",
            name="note_length",
        ),
        CheckConstraint(
            "resolved_by_type IS DISTINCT FROM 'OFFICER' OR resolution_note IS NOT NULL",
            name="officer_note_required",
        ),
        Index("ix_holds_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    transfer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transfers.id"), unique=True)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("risk_assessments.id"))
    tier: Mapped[HoldTier] = mapped_column(StrEnumType(HoldTier, 16))
    status: Mapped[HoldStatus] = mapped_column(StrEnumType(HoldStatus, 24))
    contact_response: Mapped[ContactResponse | None] = mapped_column(
        StrEnumType(ContactResponse, 24)
    )
    created_at: Mapped[datetime]
    cooling_off_until: Mapped[datetime]
    resolved_at: Mapped[datetime | None]
    resolved_by_type: Mapped[ResolvedByType | None] = mapped_column(StrEnumType(ResolvedByType, 24))
    resolved_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"))
    resolution_note: Mapped[str | None]


class ContactRequest(Base):
    __tablename__ = "contact_requests"
    __table_args__ = (
        enum_check("channel", DeliveryChannel),
        enum_check("delivery_status", DeliveryStatus),
        enum_check("response", ContactResponse, nullable=True),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    hold_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("holds.id"), index=True)
    trusted_contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trusted_contacts.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    channel: Mapped[DeliveryChannel] = mapped_column(StrEnumType(DeliveryChannel, 16))
    delivery_status: Mapped[DeliveryStatus] = mapped_column(StrEnumType(DeliveryStatus, 16))
    delivery_error: Mapped[str | None]
    expires_at: Mapped[datetime]
    opened_at: Mapped[datetime | None]
    responded_at: Mapped[datetime | None]
    response: Mapped[ContactResponse | None] = mapped_column(StrEnumType(ContactResponse, 24))
    created_at: Mapped[datetime] = created_at_column()


class FraudReport(Base):
    __tablename__ = "fraud_reports"
    __table_args__ = (
        enum_check("status", ReportStatus),
        enum_check("narrative_source", NarrativeSource),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    hold_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("holds.id"), unique=True)
    status: Mapped[ReportStatus] = mapped_column(StrEnumType(ReportStatus, 24))
    structured_fields: Mapped[dict[str, Any]]
    customer_reported: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    narrative_text: Mapped[str]
    narrative_source: Mapped[NarrativeSource] = mapped_column(StrEnumType(NarrativeSource, 16))
    acknowledgement_number: Mapped[str | None] = mapped_column(String(64))
    created_by_staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"))
    updated_by_staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = created_at_column()


class AuditLog(Base):
    """Append-only: the app has no update or delete path (tests/integration/test_audit.py)."""

    __tablename__ = "audit_log"
    __table_args__ = (
        enum_check("actor_type", ActorType),
        Index("ix_audit_log_entity", "entity_type", "entity_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = created_at_column()
    actor_type: Mapped[ActorType] = mapped_column(StrEnumType(ActorType, 24))
    actor_id: Mapped[str | None]
    action: Mapped[str]
    entity_type: Mapped[str]
    entity_id: Mapped[str]
    request_id: Mapped[str | None]
    details: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))


class FriMockRating(Base):
    """SIMULATED DoT FRI ratings. Not real DoT data."""

    __tablename__ = "fri_mock_ratings"
    __table_args__ = (enum_check("rating", FriRating),)

    msisdn_hmac: Mapped[str] = mapped_column(primary_key=True)
    rating: Mapped[FriRating] = mapped_column(StrEnumType(FriRating, 16))
    note: Mapped[str] = mapped_column(server_default="SIMULATED — not real DoT data")
    updated_at: Mapped[datetime]


class SimState(Base):
    """Demo only: a single row holding the simulated clock."""

    __tablename__ = "sim_state"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    sim_now: Mapped[datetime]
    speed: Mapped[float]
    running_scenario: Mapped[str | None]
    updated_at: Mapped[datetime]
