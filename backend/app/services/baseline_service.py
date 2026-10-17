"""Load inputs, compute and upsert customer_baselines (AI_DESIGN §4, T-025)."""

import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.domain.baseline import compute_baseline
from app.domain.config import ScoringConfig
from app.domain.enums import EventType
from app.domain.models import Baseline, FdClosure, OutboundDebit
from app.models import CustomerBaseline
from app.repositories import customers, events, risk, transfers


def compute(
    session: Session, customer_id: uuid.UUID, now: datetime, cfg: ScoringConfig
) -> Baseline:
    debits = [
        OutboundDebit(amount_paise=t.amount_paise, occurred_at=t.executed_at or t.initiated_at)
        for t in transfers.executed_for_customer(session, customer_id)
    ]
    fd_closures: list[FdClosure] = []
    for event in events.of_types(
        session, customer_id, (EventType.ROUTINE_DEBIT, EventType.FD_CLOSED)
    ):
        if event.event_type is EventType.ROUTINE_DEBIT and event.amount_paise is not None:
            debits.append(
                OutboundDebit(amount_paise=event.amount_paise, occurred_at=event.occurred_at)
            )
        elif event.event_type is EventType.FD_CLOSED and event.payload.get("maturity_date"):
            fd_closures.append(
                FdClosure(
                    closed_at=event.occurred_at,
                    maturity_date=date.fromisoformat(event.payload["maturity_date"]),
                )
            )
    first_candidates = [a.opened_at for a in customers.accounts_for(session, customer_id)] + [
        t for t in [events.first_event_at(session, customer_id)] if t is not None
    ]
    first_activity = min(first_candidates) if first_candidates else None
    return compute_baseline(debits, fd_closures, first_activity, now, cfg)


def refresh(
    session: Session, customer_id: uuid.UUID, now: datetime, cfg: ScoringConfig
) -> Baseline:
    baseline = compute(session, customer_id, now, cfg)
    row = risk.baseline_for(session, customer_id) or CustomerBaseline(customer_id=customer_id)
    row.computed_at = now
    row.history_days = baseline.history_days
    row.median_outbound_paise = baseline.median_outbound_paise
    row.p95_outbound_paise = baseline.p95_outbound_paise
    row.qualifying_transfer_count = baseline.qualifying_transfer_count
    row.premature_fd_closures_365d = baseline.premature_fd_closures_365d
    row.confidence = baseline.confidence
    row.algorithm_version = baseline.algorithm_version
    session.add(row)
    return baseline


def get_or_compute(
    session: Session, customer_id: uuid.UUID, now: datetime, cfg: ScoringConfig
) -> Baseline:
    """The stored baseline (recomputed on seed and after executed transfers), else a fresh one."""
    row = risk.baseline_for(session, customer_id)
    if row is None:
        return refresh(session, customer_id, now, cfg)
    return Baseline(
        history_days=row.history_days,
        median_outbound_paise=row.median_outbound_paise,
        p95_outbound_paise=row.p95_outbound_paise,
        qualifying_transfer_count=row.qualifying_transfer_count,
        premature_fd_closures_365d=row.premature_fd_closures_365d,
        confidence=row.confidence,
        algorithm_version=row.algorithm_version,
    )
