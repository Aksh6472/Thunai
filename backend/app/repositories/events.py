"""Account events and signals."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import EventType, SignalType
from app.models import AccountEvent, Signal


def by_event_id(session: Session, event_id: str) -> AccountEvent | None:
    return session.scalar(select(AccountEvent).where(AccountEvent.event_id == event_id))


def in_window(
    session: Session,
    customer_id: uuid.UUID,
    since: datetime,
    until: datetime,
    types: tuple[EventType, ...] | None = None,
) -> list[AccountEvent]:
    stmt = select(AccountEvent).where(
        AccountEvent.customer_id == customer_id,
        AccountEvent.occurred_at >= since,
        AccountEvent.occurred_at <= until,
    )
    if types:
        stmt = stmt.where(AccountEvent.event_type.in_(types))
    return list(session.scalars(stmt.order_by(AccountEvent.occurred_at)))


def of_types(
    session: Session, customer_id: uuid.UUID, types: tuple[EventType, ...]
) -> list[AccountEvent]:
    return list(
        session.scalars(
            select(AccountEvent)
            .where(AccountEvent.customer_id == customer_id, AccountEvent.event_type.in_(types))
            .order_by(AccountEvent.occurred_at)
        )
    )


def first_event_at(session: Session, customer_id: uuid.UUID) -> datetime | None:
    return session.scalar(
        select(AccountEvent.occurred_at)
        .where(AccountEvent.customer_id == customer_id)
        .order_by(AccountEvent.occurred_at)
        .limit(1)
    )


def latest_call_signal(session: Session, customer_id: uuid.UUID, at: datetime) -> Signal | None:
    return session.scalar(
        select(Signal)
        .where(
            Signal.customer_id == customer_id,
            Signal.signal_type == SignalType.CALL_RISK,
            Signal.observed_at <= at,
        )
        .order_by(Signal.observed_at.desc())
        .limit(1)
    )


def checklist_signals(session: Session, transfer_id: uuid.UUID) -> list[Signal]:
    return list(
        session.scalars(
            select(Signal)
            .where(
                Signal.transfer_id == transfer_id,
                Signal.signal_type == SignalType.TELLER_CHECKLIST,
            )
            .order_by(Signal.observed_at)
        )
    )
