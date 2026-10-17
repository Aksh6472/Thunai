"""Transfers, holds and contact requests."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import TransferStatus
from app.models import ContactRequest, FraudReport, Hold, Transfer


def by_ref(session: Session, transfer_ref: str, *, for_update: bool = False) -> Transfer | None:
    stmt = select(Transfer).where(Transfer.transfer_ref == transfer_ref)
    if for_update:
        stmt = stmt.with_for_update()
    return session.scalar(stmt)


def executed_to_payee(session: Session, payee_id: uuid.UUID, before: datetime) -> list[Transfer]:
    return list(
        session.scalars(
            select(Transfer).where(
                Transfer.payee_id == payee_id,
                Transfer.status == TransferStatus.EXECUTED,
                Transfer.initiated_at < before,
            )
        )
    )


def executed_for_customer(session: Session, customer_id: uuid.UUID) -> list[Transfer]:
    return list(
        session.scalars(
            select(Transfer).where(
                Transfer.customer_id == customer_id, Transfer.status == TransferStatus.EXECUTED
            )
        )
    )


def hold_for_transfer(session: Session, transfer_id: uuid.UUID) -> Hold | None:
    return session.scalar(select(Hold).where(Hold.transfer_id == transfer_id))


def hold_by_id(session: Session, hold_id: uuid.UUID, *, for_update: bool = False) -> Hold | None:
    stmt = select(Hold).where(Hold.id == hold_id)
    if for_update:
        stmt = stmt.with_for_update()
    return session.scalar(stmt)


def contact_requests_for_hold(session: Session, hold_id: uuid.UUID) -> list[ContactRequest]:
    return list(
        session.scalars(
            select(ContactRequest)
            .where(ContactRequest.hold_id == hold_id)
            .order_by(ContactRequest.created_at, ContactRequest.id)
        )
    )


def contact_request_by_hash(session: Session, token_hash: str) -> ContactRequest | None:
    return session.scalar(select(ContactRequest).where(ContactRequest.token_hash == token_hash))


def report_for_hold(session: Session, hold_id: uuid.UUID) -> FraudReport | None:
    return session.scalar(select(FraudReport).where(FraudReport.hold_id == hold_id))
