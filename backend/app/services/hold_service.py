"""Hold lifecycle (FR-11, FR-13, DATABASE_SCHEMA §3.13). Transitions only via the domain table."""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, InvalidStateTransition, NoteRequired, NotFound
from app.core.security import Principal
from app.domain.enums import (
    ActorType,
    CancelledReason,
    ContactResponse,
    EpisodeStatus,
    HoldStatus,
    HoldTier,
    OfficerDecision,
    ResolvedByType,
    Role,
)
from app.domain.transitions import (
    ACTIVE_HOLD_STATUSES,
    HoldEvent,
    TransitionNotAllowed,
    next_hold_status,
)
from app.models import Customer, Hold, RiskAssessment, Transfer
from app.repositories import customers, transfers
from app.services import contact_service, episode_service, transfer_ops
from app.services.audit_service import audit
from app.services.context import Ctx

logger = logging.getLogger(__name__)

NOTE_MIN, NOTE_MAX = 10, 1000


def transition(hold: Hold, event: HoldEvent) -> None:
    try:
        hold.status = next_hold_status(hold.status, event, hold.tier)
    except TransitionNotAllowed:
        raise InvalidStateTransition("The hold is already resolved.") from None


def episode_id_for(session: Session, hold: Hold) -> uuid.UUID | None:
    assessment = session.get(RiskAssessment, hold.assessment_id)
    return assessment.episode_id if assessment else None


def create_hold(
    session: Session,
    ctx: Ctx,
    transfer: Transfer,
    assessment: RiskAssessment,
    tier: HoldTier,
    status: HoldStatus,
    now: datetime,
) -> Hold:
    hold = Hold(
        transfer_id=transfer.id,
        assessment_id=assessment.id,
        tier=tier,
        status=status,
        created_at=now,
        cooling_off_until=now + timedelta(minutes=ctx.settings.cooling_off_minutes),
    )
    session.add(hold)
    session.flush()
    audit(
        session,
        "HOLD_CREATED",
        entity_type="hold",
        entity_id=hold.id,
        actor_type=ActorType.SYSTEM,
        details={"tier": tier.value, "status": status.value, "transfer_ref": transfer.transfer_ref},
    )
    # A VERY_HIGH hold still notifies an *active* contact; the response is recorded for the
    # officer. A contact inside the 72 h activation delay is never notified (AC-12).
    contact = customers.current_trusted_contact(session, transfer.customer_id)
    if contact is not None and contact_service.is_active(contact, now):
        contact_service.create_request(session, ctx, hold, contact)
    logger.info("hold.created", extra={"tier": tier.value, "status": status.value})
    return hold


def escalate_to_very_high(session: Session, hold: Hold, actor_id: str) -> None:
    if hold.tier is HoldTier.VERY_HIGH:
        return
    hold.tier = HoldTier.VERY_HIGH
    transition(hold, HoldEvent.ESCALATED_TO_VERY_HIGH)
    audit(
        session,
        "HOLD_ESCALATED",
        entity_type="hold",
        entity_id=hold.id,
        actor_type=ActorType.STAFF,
        actor_id=actor_id,
        details={"tier": "VERY_HIGH", "status": hold.status.value},
    )


def expire_cooling_off(session: Session, now: datetime) -> int:
    """Lazy expiry (ARCHITECTURE §4.7): AWAITING_CONTACT past cooling-off → AWAITING_OFFICER."""
    due = session.scalars(
        select(Hold)
        .where(Hold.status == HoldStatus.AWAITING_CONTACT, Hold.cooling_off_until < now)
        .with_for_update(skip_locked=True)
    ).all()
    for hold in due:
        transition(hold, HoldEvent.COOLING_OFF_EXPIRED)
        audit(
            session,
            "HOLD_COOLING_OFF_EXPIRED",
            entity_type="hold",
            entity_id=hold.id,
            actor_type=ActorType.SYSTEM,
        )
    if due:
        session.commit()
    return len(due)


def check_branch(principal: Principal, customer: Customer | None) -> Customer:
    """Branch scoping. Unknown or other-branch objects are 404, never 403 (SECURITY T-07)."""
    if customer is None:
        raise NotFound("hold")
    if principal.role is Role.ADMIN or principal.is_service:
        return customer
    if principal.branch_code != customer.branch_code:
        raise NotFound("hold")
    return customer


def load_for_staff(
    session: Session, hold_id: uuid.UUID, principal: Principal, *, for_update: bool = False
) -> tuple[Hold, Transfer, Customer]:
    hold = transfers.hold_by_id(session, hold_id, for_update=for_update)
    if hold is None:
        raise NotFound("hold")
    transfer = session.get(Transfer, hold.transfer_id)
    if transfer is None:
        raise NotFound("hold")
    customer = check_branch(principal, session.get(Customer, transfer.customer_id))
    return hold, transfer, customer


def officer_decision(
    session: Session,
    ctx: Ctx,
    hold_id: uuid.UUID,
    decision: OfficerDecision,
    note: str | None,
    principal: Principal,
) -> Hold:
    if principal.role is not Role.OFFICER:
        raise Forbidden()  # separation of duties: ADMIN can't resolve holds
    note = (note or "").strip()
    if not NOTE_MIN <= len(note) <= NOTE_MAX:
        raise NoteRequired()
    expire_cooling_off(session, ctx.clock.now())
    hold, transfer, _ = load_for_staff(session, hold_id, principal, for_update=True)
    if hold.status not in ACTIVE_HOLD_STATUSES:
        raise InvalidStateTransition("The hold is already resolved.")
    now = ctx.clock.now()
    officer_id = uuid.UUID(principal.id)
    if decision is OfficerDecision.KEEP_HOLDING:
        transition(hold, HoldEvent.OFFICER_KEEP_HOLDING)
        action = "OFFICER_KEEP_HOLDING"
    elif decision is OfficerDecision.RELEASE:
        transition(hold, HoldEvent.OFFICER_RELEASE)
        transfer_ops.execute(session, transfer, now, ctx.cfg)
        episode_service.close_episode(
            session, episode_id_for(session, hold), EpisodeStatus.CLOSED_BENIGN, now
        )
        action = "HOLD_RELEASED"
    else:
        transition(hold, HoldEvent.OFFICER_CANCEL)
        reason = (
            CancelledReason.CONTACT_REPORTED_SCAM_OFFICER_CONFIRMED
            if hold.contact_response is ContactResponse.REPORT_SUSPICIOUS
            else CancelledReason.OFFICER_CANCELLED
        )
        transfer_ops.cancel(transfer, reason)
        episode_service.close_episode(
            session, episode_id_for(session, hold), EpisodeStatus.CLOSED_CONFIRMED_RISK, now
        )
        action = "HOLD_CANCELLED"
    if hold.status not in ACTIVE_HOLD_STATUSES:
        hold.resolved_at = now
        hold.resolved_by_type = ResolvedByType.OFFICER
        hold.resolved_by_staff_id = officer_id
        hold.resolution_note = note
    audit(
        session,
        action,
        entity_type="hold",
        entity_id=hold.id,
        actor_type=ActorType.STAFF,
        actor_id=principal.id,
        details={"decision": decision.value, "note": note},
    )
    session.commit()
    logger.info("hold.resolved", extra={"decision": decision.value})
    return hold


def customer_cancel(
    session: Session, hold: Hold, transfer: Transfer, ctx: Ctx, customer_id: str
) -> None:
    transition(hold, HoldEvent.CUSTOMER_CANCEL)
    hold.resolved_at = ctx.clock.now()
    hold.resolved_by_type = ResolvedByType.CUSTOMER
    transfer_ops.cancel(transfer, CancelledReason.CUSTOMER_CANCELLED)
    audit(
        session,
        "HOLD_CANCELLED_BY_CUSTOMER",
        entity_type="hold",
        entity_id=hold.id,
        actor_type=ActorType.CUSTOMER,
        actor_id=customer_id,
    )
