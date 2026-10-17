"""Teller DTOs (API_SPEC §7)."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.domain.enums import TellerItem, Tier
from app.schemas.common import RequestModel, ResponseModel


class ChecklistIn(RequestModel):
    items: list[TellerItem] = Field(max_length=4)
    # Stored for the report; NEVER scored (A-07, SECURITY T-01).
    customer_said: Annotated[str, StringConstraints(max_length=500)] | None = None


class ScriptStep(ResponseModel):
    id: str
    text: str


class ScriptOut(ResponseModel):
    lang: Literal["en", "ta"]
    tier: Tier
    steps: list[ScriptStep]
    reviewed_by_native_speaker: bool
