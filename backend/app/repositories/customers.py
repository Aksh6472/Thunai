"""Customers, accounts, payees, trusted contacts, consents."""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import ConsentType, TrustedContactStatus
from app.models import Account, Consent, Customer, Payee, TrustedContact


def by_ref(session: Session, external_ref: str, *, for_update: bool = False) -> Customer | None:
    stmt = select(Customer).where(Customer.external_ref == external_ref)
    if for_update:
        stmt = stmt.with_for_update()
    return session.scalar(stmt)


def by_id(session: Session, customer_id: uuid.UUID, *, for_update: bool = False) -> Customer | None:
    stmt = select(Customer).where(Customer.id == customer_id)
    if for_update:
        stmt = stmt.with_for_update()
    return session.scalar(stmt)


def account_by_masked(session: Session, customer_id: uuid.UUID, masked: str) -> Account | None:
    return session.scalar(
        select(Account).where(Account.customer_id == customer_id, Account.masked_number == masked)
    )


def accounts_for(session: Session, customer_id: uuid.UUID) -> list[Account]:
    return list(
        session.scalars(
            select(Account).where(Account.customer_id == customer_id).order_by(Account.opened_at)
        )
    )


def payee_by_ref(session: Session, customer_id: uuid.UUID, payee_ref: str) -> Payee | None:
    return session.scalar(
        select(Payee).where(Payee.customer_id == customer_id, Payee.payee_ref == payee_ref)
    )


def payees_for(session: Session, customer_id: uuid.UUID) -> list[Payee]:
    return list(
        session.scalars(
            select(Payee).where(Payee.customer_id == customer_id).order_by(Payee.added_at.desc())
        )
    )


def current_trusted_contact(session: Session, customer_id: uuid.UUID) -> TrustedContact | None:
    """The single non-revoked contact (partial unique index), active or pending."""
    return session.scalar(
        select(TrustedContact).where(
            TrustedContact.customer_id == customer_id,
            TrustedContact.status != TrustedContactStatus.REVOKED,
        )
    )


def latest_contact_registration(session: Session, customer_id: uuid.UUID) -> datetime | None:
    value: datetime | None = session.scalar(
        select(func.max(TrustedContact.registered_at)).where(
            TrustedContact.customer_id == customer_id
        )
    )
    return value


def latest_consent(
    session: Session, customer_id: uuid.UUID, consent_type: ConsentType
) -> Consent | None:
    return session.scalar(
        select(Consent)
        .where(Consent.customer_id == customer_id, Consent.consent_type == consent_type)
        .order_by(Consent.recorded_at.desc(), Consent.id)
        .limit(1)
    )
