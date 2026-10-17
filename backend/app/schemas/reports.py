"""1930 / cybercrime.gov.in report drafts (API_SPEC §8)."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints

from app.domain.enums import NarrativeSource, ReportStatus
from app.schemas.common import RequestModel, ResponseModel

DISCLAIMER = "Draft for officer review. Not submitted. File via 1930 or cybercrime.gov.in."


class ReportCreateIn(RequestModel):
    use_llm: bool = False


class CustomerReported(RequestModel):
    claimed_agency: Annotated[str, StringConstraints(max_length=64)] | None = None
    scammer_numbers_given_by_customer: list[
        Annotated[str, StringConstraints(pattern=r"^\+?[0-9 \-]{6,20}$")]
    ] = Field(default_factory=list, max_length=5)
    platform: Annotated[str, StringConstraints(max_length=64)] | None = None
    notes: Annotated[str, StringConstraints(max_length=1000)] | None = None


class ReportPatchIn(RequestModel):
    customer_reported: CustomerReported | None = None
    narrative_text: Annotated[str, StringConstraints(min_length=1, max_length=4000)] | None = None
    status: Literal["DRAFT", "READY"] | None = None


class MarkFiledIn(RequestModel):
    acknowledgement_number: Annotated[
        str, StringConstraints(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9/\-]+$")
    ]


class ReportOut(ResponseModel):
    id: str
    hold_id: str
    status: ReportStatus
    structured_fields: dict[str, Any]
    customer_reported: dict[str, Any]
    narrative_text: str
    narrative_source: NarrativeSource
    acknowledgement_number: str | None
    disclaimer: str = DISCLAIMER
    updated_at: datetime
