"""Read-side queries for staff screens (FR-16). Each endpoint stays within a handful of queries."""

import base64
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, case, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.core.errors import BadRequest
from app.domain.enums import HoldStatus, HoldTier, Tier
from app.models import (
    AuditLog,
    ContactRequest,
    Customer,
    FraudReport,
    Hold,
    Payee,
    RiskAssessment,
    Transfer,
)


def encode_cursor(values: list[Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(values, default=str).encode()).decode()


def decode_cursor(cursor: str | None) -> list[Any] | None:
    if not cursor:
        return None
    try:
        values = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except (ValueError, json.JSONDecodeError):
        raise BadRequest("Invalid cursor.") from None
    if not isinstance(values, list):
        raise BadRequest("Invalid cursor.")
    return values


TIER_RANK = case((Hold.tier == HoldTier.VERY_HIGH, 0), else_=1)


def hold_rows(
    session: Session,
    *,
    branch_code: str | None,
    statuses: list[HoldStatus] | None,
    tier: Tier | None,
    limit: int,
    cursor: list[Any] | None,
    channel: str | None = None,
) -> list[tuple[Hold, Transfer, Customer]]:
    """VERY_HIGH first, then cooling_off_until ascending, then id (stable)."""
    stmt: Select[Hold, Transfer, Customer] = (
        select(Hold, Transfer, Customer)
        .join(Transfer, Transfer.id == Hold.transfer_id)
        .join(Customer, Customer.id == Transfer.customer_id)
    )
    if branch_code:
        stmt = stmt.where(Customer.branch_code == branch_code)
    if statuses:
        stmt = stmt.where(Hold.status.in_(statuses))
    if tier is not None:
        stmt = stmt.where(Hold.tier == tier.value)
    if channel:
        stmt = stmt.where(Transfer.channel == channel)
    if cursor:
        try:
            rank, cooling, hold_id = (
                int(cursor[0]),
                datetime.fromisoformat(cursor[1]),
                uuid.UUID(cursor[2]),
            )
        except (ValueError, IndexError, TypeError):
            raise BadRequest("Invalid cursor.") from None
        stmt = stmt.where(
            tuple_(TIER_RANK, Hold.cooling_off_until, Hold.id) > tuple_(rank, cooling, hold_id)
        )
    stmt = stmt.order_by(TIER_RANK, Hold.cooling_off_until, Hold.id).limit(limit + 1)
    return [(row[0], row[1], row[2]) for row in session.execute(stmt).all()]


def hold_cursor(hold: Hold) -> str:
    rank = 0 if hold.tier is HoldTier.VERY_HIGH else 1
    return encode_cursor([rank, hold.cooling_off_until.isoformat(), str(hold.id)])


def latest_assessments(
    session: Session, transfer_ids: list[uuid.UUID]
) -> dict[uuid.UUID, RiskAssessment]:
    if not transfer_ids:
        return {}
    rows = session.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.transfer_id.in_(transfer_ids))
        .order_by(RiskAssessment.transfer_id, RiskAssessment.assessed_at.desc(), RiskAssessment.id)
        .ext(distinct_on(RiskAssessment.transfer_id))
    ).all()
    return {r.transfer_id: r for r in rows}


def hold_detail_core(
    session: Session, hold_id: uuid.UUID
) -> tuple[Hold, Transfer, Customer, Payee, str, uuid.UUID | None] | None:
    from app.models import Account

    row = session.execute(
        select(Hold, Transfer, Customer, Payee, Account.masked_number, FraudReport.id)
        .join(Transfer, Transfer.id == Hold.transfer_id)
        .join(Customer, Customer.id == Transfer.customer_id)
        .join(Payee, Payee.id == Transfer.payee_id)
        .join(Account, Account.id == Transfer.from_account_id)
        .outerjoin(FraudReport, FraudReport.hold_id == Hold.id)
        .where(Hold.id == hold_id)
    ).first()
    if row is None:
        return None
    return row[0], row[1], row[2], row[3], row[4], row[5]


def contact_requests(session: Session, hold_id: uuid.UUID) -> list[ContactRequest]:
    return list(
        session.scalars(
            select(ContactRequest)
            .where(ContactRequest.hold_id == hold_id)
            .order_by(ContactRequest.created_at, ContactRequest.id)
        )
    )


def recent_audit(
    session: Session, entity_type: str, entity_ids: list[str], limit: int = 10
) -> list[AuditLog]:
    return list(
        session.scalars(
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id.in_(entity_ids))
            .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
    )


def customer_search(
    session: Session, *, branch_code: str | None, search: str | None, limit: int, after: str | None
) -> list[Customer]:
    stmt = select(Customer)
    if branch_code:
        stmt = stmt.where(Customer.branch_code == branch_code)
    if search:
        pattern = f"%{search.replace('%', '').replace('_', '')}%"
        stmt = stmt.where(
            or_(Customer.external_ref.ilike(pattern), Customer.display_name.ilike(pattern))
        )
    if after:
        stmt = stmt.where(Customer.external_ref > after)
    return list(session.scalars(stmt.order_by(Customer.external_ref).limit(limit + 1)))


def count(session: Session, stmt: Select[int]) -> int:
    return int(session.scalar(stmt) or 0)


def count_where(session: Session, *conditions: Any) -> Select[int]:
    return select(func.count()).select_from(Hold).where(and_(*conditions))
