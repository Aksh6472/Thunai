"""Trusted-contact page DTOs (API_SPEC §9). Minimal, consented data only."""

from datetime import datetime
from typing import Literal

from app.domain.enums import Channel, ContactResponse, Language
from app.schemas.common import RequestModel, ResponseModel


class TrustedView(ResponseModel):
    customer_first_name: str
    amount_display: str
    channel: Channel
    held_at: datetime
    bank_helpline: str
    language: Language
    already_responded: bool


class TrustedResponseIn(RequestModel):
    response: ContactResponse


class TrustedResponseOut(ResponseModel):
    result_key: Literal["RELEASED", "SENT_TO_OFFICER"]
    message: str
