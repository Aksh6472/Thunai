"""Customer app DTOs (API_SPEC §5)."""

from datetime import date, datetime
from typing import Annotated

from pydantic import StringConstraints

from app.domain.enums import AccountType, ConsentType, Language
from app.schemas.common import RequestModel, ResponseModel
from app.schemas.events import E164


class AccountOut(ResponseModel):
    masked_number: str
    account_type: AccountType
    balance_paise: int
    status: str
    maturity_date: date | None


class CustomerPayeeOut(ResponseModel):
    payee_ref: str
    display_name: str
    bank_name: str
    masked_account: str
    added_at: datetime


class CustomerContactOut(ResponseModel):
    display_name: str
    relationship: str
    phone_last4: str
    status: str
    effective_from: datetime


class CustomerOverview(ResponseModel):
    customer_ref: str
    display_name: str
    preferred_language: Language
    accounts: list[AccountOut]
    payees: list[CustomerPayeeOut]
    trusted_contact: CustomerContactOut | None
    consents: dict[str, bool]


class ConsentIn(RequestModel):
    consent_type: ConsentType
    granted: bool
    text_version: Annotated[str, StringConstraints(pattern=r"^[a-z_]+_v[0-9]+$", max_length=40)]


class ConsentOut(ResponseModel):
    consent_type: ConsentType
    granted: bool
    text_version: str
    recorded_at: datetime


class TrustedContactIn(RequestModel):
    display_name: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    relationship: Annotated[str, StringConstraints(min_length=1, max_length=40)]
    phone_e164: E164
    preferred_language: Language


class TrustedContactOut(ResponseModel):
    status: str
    effective_from: datetime
