"""Ingestion DTOs (API_SPEC §4). Payloads are validated per event_type; unknown fields are 422."""

from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StringConstraints

from app.domain.enums import CallType, Channel, Language, Tier
from app.schemas.common import RequestModel, ResponseModel

Ref = Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")]
MaskedAccount = Annotated[str, StringConstraints(pattern=r"^[X0-9]{6,20}$")]
E164 = Annotated[str, StringConstraints(pattern=r"^\+[1-9]\d{7,14}$")]
Ifsc = Annotated[str, StringConstraints(pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=120)]
Paise = Annotated[int, Field(ge=0, le=10**13)]


class FdClosedPayload(RequestModel):
    maturity_date: date
    proceeds_to_account: MaskedAccount


class InternalTransferPayload(RequestModel):
    from_account: MaskedAccount
    to_account: MaskedAccount


class PayeeAddedPayload(RequestModel):
    payee_ref: Ref
    display_name: ShortText
    bank_name: ShortText
    ifsc: Ifsc
    masked_account: MaskedAccount
    channel: Channel
    linked_msisdn: E164 | None = None  # HMAC'd on receipt, never stored raw


class TrustedContactPayload(RequestModel):
    display_name: ShortText
    relationship: Annotated[str, StringConstraints(min_length=1, max_length=40)]
    phone_e164: E164  # encrypted on receipt
    preferred_language: Language


class RoutinePayload(RequestModel):
    counterparty: ShortText
    payee_ref: Ref | None = None


class _EventBase(RequestModel):
    event_id: Ref
    customer_ref: Ref
    occurred_at: AwareDatetime
    account_ref: MaskedAccount | None = None
    amount_paise: Paise | None = None


class FdClosedEvent(_EventBase):
    event_type: Literal["FD_CLOSED"]
    amount_paise: Paise
    payload: FdClosedPayload


class InternalTransferEvent(_EventBase):
    event_type: Literal["INTERNAL_TRANSFER_IN"]
    amount_paise: Paise
    payload: InternalTransferPayload


class PayeeAddedEvent(_EventBase):
    event_type: Literal["PAYEE_ADDED"]
    payload: PayeeAddedPayload


class TrustedContactChangedEvent(_EventBase):
    event_type: Literal["TRUSTED_CONTACT_CHANGED"]
    payload: TrustedContactPayload


class RoutineDebitEvent(_EventBase):
    event_type: Literal["ROUTINE_DEBIT"]
    amount_paise: Paise
    payload: RoutinePayload


class RoutineCreditEvent(_EventBase):
    event_type: Literal["ROUTINE_CREDIT"]
    amount_paise: Paise
    payload: RoutinePayload


EventIn = Annotated[
    FdClosedEvent
    | InternalTransferEvent
    | PayeeAddedEvent
    | TrustedContactChangedEvent
    | RoutineDebitEvent
    | RoutineCreditEvent,
    Field(discriminator="event_type"),
]


class EpisodeWatch(ResponseModel):
    id: str
    watch_score: int
    watch_tier: Tier


class EventAccepted(ResponseModel):
    event_id: str
    stage_detected: str | None
    episode: EpisodeWatch | None


class CallSignalIn(RequestModel):
    """Consented flag only. There is no caller number, app name, audio or content field (NFR-08)."""

    customer_ref: Ref
    call_type: CallType
    caller_known: bool
    duration_min: int = Field(ge=0, le=1440)
    ended_at: AwareDatetime | None = None
    observed_at: AwareDatetime


class CallSignalAccepted(ResponseModel):
    accepted: bool = True
    episode: EpisodeWatch | None
