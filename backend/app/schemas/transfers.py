"""Transfer assessment, customer app and hold DTOs (API_SPEC §2.5, §4–§6)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import AwareDatetime, Field

from app.domain.enums import (
    Channel,
    ContactResponse,
    Decision,
    DeliveryChannel,
    DeliveryStatus,
    HoldStatus,
    OfficerDecision,
    Rail,
    Tier,
    TransferStatus,
)
from app.schemas.common import RequestModel, ResponseModel
from app.schemas.events import MaskedAccount, Paise, Ref


class ReasonOut(ResponseModel):
    code: str
    points: int
    stage: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    text_en: str
    text_ta: str


class AssessmentResult(ResponseModel):
    transfer_ref: str
    transfer_status: TransferStatus
    decision: Decision
    tier: Tier
    score: int
    raw_score: int
    reasons: list[ReasonOut]
    overrides_applied: list[str]
    hold_id: str | None
    assessment_id: str
    trigger: str
    config_version: str
    assessed_at: datetime


class TransferAssessIn(RequestModel):
    transfer_ref: Ref
    customer_ref: Ref
    from_account: MaskedAccount
    payee_ref: Ref
    amount_paise: Paise = Field(gt=0)
    rail: Rail
    channel: Channel
    initiated_at: AwareDatetime
    scenario_label: str | None = Field(default=None, pattern=r"^[PN][0-9]{1,2}$")


class CustomerTransferIn(RequestModel):
    transfer_ref: Ref
    from_account: MaskedAccount
    payee_ref: Ref
    amount_paise: Paise = Field(gt=0)
    rail: Rail
    initiated_at: AwareDatetime | None = None


class ContactAsked(ResponseModel):
    display_name: str
    relationship: str


class CustomerTransferOut(ResponseModel):
    """Customer-safe: no score, tier or reasons (ADR-013, SECURITY T-19)."""

    transfer_ref: str
    transfer_status: TransferStatus
    decision: Decision
    hold_id: str | None = None
    hold_status: HoldStatus | None = None
    message_key: str
    contact_asked: ContactAsked | None = None


class WarningResponseIn(RequestModel):
    action: Literal["CONTINUE", "CANCEL"]


class TransferStatusOut(ResponseModel):
    transfer_ref: str
    transfer_status: TransferStatus


class OfficerDecisionIn(RequestModel):
    decision: OfficerDecision
    note: str | None = Field(default=None, max_length=1000)


class CustomerBrief(ResponseModel):
    id: str
    external_ref: str
    display_name: str


class HoldListItem(ResponseModel):
    id: str | None
    transfer_ref: str
    customer: CustomerBrief
    amount_paise: int
    tier: Tier
    status: str
    transfer_status: TransferStatus
    channel: Channel
    contact_response: ContactResponse | None
    top_reasons: list[ReasonOut]
    created_at: datetime
    cooling_off_until: datetime | None


class Page[T](ResponseModel):
    items: list[T]
    next_cursor: str | None


class ContactRequestOut(ResponseModel):
    id: str
    channel: DeliveryChannel
    delivery_status: DeliveryStatus
    delivery_error: str | None
    sent_at: datetime
    expires_at: datetime
    opened_at: datetime | None
    responded_at: datetime | None
    response: ContactResponse | None


class PayeeOut(ResponseModel):
    payee_ref: str
    display_name: str
    bank_name: str
    ifsc: str
    masked_account: str
    linked_msisdn_last4: str | None
    added_at: datetime


class TransferOut(ResponseModel):
    transfer_ref: str
    amount_paise: int
    rail: Rail
    channel: Channel
    status: TransferStatus
    initiated_at: datetime
    decided_at: datetime | None
    executed_at: datetime | None
    from_account_masked: str
    cancelled_reason: str | None


class WatchPointOut(ResponseModel):
    at: datetime
    score: int
    tier: Tier
    trigger_event_id: str


class StageOut(ResponseModel):
    stage: str
    event_id: str
    occurred_at: datetime
    amount_paise: int | None = None


class EpisodeOut(ResponseModel):
    id: str
    status: str
    opened_at: datetime
    last_stage_at: datetime
    closed_at: datetime | None
    watch_score: int
    watch_tier: Tier
    stages: list[StageOut]
    watch_history: list[WatchPointOut]


class AuditOut(ResponseModel):
    occurred_at: datetime
    actor_type: str
    action: str
    details: dict[str, Any]


class TrustedContactBrief(ResponseModel):
    display_name: str
    relationship: str
    phone_last4: str
    status: str
    effective_from: datetime
    active: bool


class HoldDetail(ResponseModel):
    id: str
    tier: Tier
    status: HoldStatus
    contact_response: ContactResponse | None
    created_at: datetime
    cooling_off_until: datetime
    resolved_at: datetime | None
    resolved_by_type: str | None
    resolution_note: str | None
    customer: CustomerBrief
    transfer: TransferOut
    payee: PayeeOut
    assessments: list[AssessmentResult]
    episode: EpisodeOut | None
    trusted_contact: TrustedContactBrief | None
    contact_requests: list[ContactRequestOut]
    report_id: str | None
    audit: list[AuditOut]
