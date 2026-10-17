"""Staff read views of holds (API_SPEC §6)."""

import uuid

from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.core.security import Principal
from app.domain.enums import HoldStatus, Role, Tier
from app.models import Customer, Hold, RiskAssessment, RiskEpisode, Transfer, TrustedContact
from app.repositories import customers, queries, risk
from app.schemas.transfers import (
    AuditOut,
    ContactRequestOut,
    CustomerBrief,
    EpisodeOut,
    HoldDetail,
    HoldListItem,
    Page,
    PayeeOut,
    ReasonOut,
    StageOut,
    TransferOut,
    TrustedContactBrief,
    WatchPointOut,
)
from app.services import contact_service, hold_service
from app.services.assessment_service import to_result
from app.services.context import Ctx

MAX_LIMIT = 100


def branch_scope(principal: Principal) -> str | None:
    return None if principal.role is Role.ADMIN else principal.branch_code


def top_reasons(row: RiskAssessment | None, n: int = 3) -> list[ReasonOut]:
    if row is None:
        return []
    ranked = sorted(row.reasons, key=lambda r: (-abs(r["points"]), r["code"]))
    return [ReasonOut.model_validate(r) for r in ranked if r["points"]][:n]


def customer_brief(customer: Customer) -> CustomerBrief:
    return CustomerBrief(
        id=str(customer.id), external_ref=customer.external_ref, display_name=customer.display_name
    )


def list_item(
    hold: Hold, transfer: Transfer, customer: Customer, assessment: RiskAssessment | None
) -> HoldListItem:
    return HoldListItem(
        id=str(hold.id),
        transfer_ref=transfer.transfer_ref,
        customer=customer_brief(customer),
        amount_paise=transfer.amount_paise,
        tier=Tier(hold.tier.value),
        status=hold.status.value,
        transfer_status=transfer.status,
        channel=transfer.channel,
        contact_response=hold.contact_response,
        top_reasons=top_reasons(assessment),
        created_at=hold.created_at,
        cooling_off_until=hold.cooling_off_until,
    )


def list_holds(
    session: Session,
    ctx: Ctx,
    principal: Principal,
    *,
    status: HoldStatus | None,
    tier: Tier | None,
    limit: int,
    cursor: str | None,
) -> Page[HoldListItem]:
    hold_service.expire_cooling_off(session, ctx.clock.now())
    limit = max(1, min(limit, MAX_LIMIT))
    rows = queries.hold_rows(
        session,
        branch_code=branch_scope(principal),
        statuses=[status] if status else None,
        tier=tier,
        limit=limit,
        cursor=queries.decode_cursor(cursor),
    )
    page, more = rows[:limit], len(rows) > limit
    latest = queries.latest_assessments(session, [t.id for _, t, _ in page])
    items = [list_item(h, t, c, latest.get(t.id)) for h, t, c in page]
    next_cursor = queries.hold_cursor(page[-1][0]) if more and page else None
    return Page[HoldListItem](items=items, next_cursor=next_cursor)


def episode_out(row: RiskEpisode | None) -> EpisodeOut | None:
    if row is None:
        return None
    return EpisodeOut(
        id=str(row.id),
        status=row.status.value,
        opened_at=row.opened_at,
        last_stage_at=row.last_stage_at,
        closed_at=row.closed_at,
        watch_score=row.watch_score,
        watch_tier=row.watch_tier,
        stages=[StageOut.model_validate(s) for s in row.stages],
        watch_history=[WatchPointOut.model_validate(p) for p in row.watch_history],
    )


def hold_detail(session: Session, ctx: Ctx, principal: Principal, hold_id: uuid.UUID) -> HoldDetail:
    hold_service.expire_cooling_off(session, ctx.clock.now())
    core = queries.hold_detail_core(session, hold_id)
    if core is None:
        raise NotFound("hold")
    hold, transfer, customer, payee, from_masked, report_id = core
    hold_service.check_branch(principal, customer)
    assessments = risk.assessments_for_transfer(session, transfer.id)
    episode_id = next((a.episode_id for a in reversed(assessments) if a.episode_id), None)
    episode = session.get(RiskEpisode, episode_id) if episode_id else None
    contact = customers.current_trusted_contact(session, customer.id)
    requests = queries.contact_requests(session, hold.id)
    audit_rows = queries.recent_audit(session, "hold", [str(hold.id)])
    return HoldDetail(
        id=str(hold.id),
        tier=Tier(hold.tier.value),
        status=hold.status,
        contact_response=hold.contact_response,
        created_at=hold.created_at,
        cooling_off_until=hold.cooling_off_until,
        resolved_at=hold.resolved_at,
        resolved_by_type=hold.resolved_by_type.value if hold.resolved_by_type else None,
        resolution_note=hold.resolution_note,
        customer=customer_brief(customer),
        transfer=transfer_out(transfer, from_masked),
        payee=PayeeOut.model_validate(payee),
        assessments=[to_result(transfer, a, hold) for a in assessments],
        episode=episode_out(episode),
        trusted_contact=contact_brief(contact, ctx),
        contact_requests=[
            ContactRequestOut(
                id=str(r.id),
                channel=r.channel,
                delivery_status=r.delivery_status,
                delivery_error=r.delivery_error,
                sent_at=r.created_at,
                expires_at=r.expires_at,
                opened_at=r.opened_at,
                responded_at=r.responded_at,
                response=r.response,
            )
            for r in requests
        ],
        report_id=str(report_id) if report_id else None,
        audit=[
            AuditOut(
                occurred_at=a.occurred_at,
                actor_type=a.actor_type.value,
                action=a.action,
                details=a.details,
            )
            for a in audit_rows
        ],
    )


def transfer_out(transfer: Transfer, from_masked: str) -> TransferOut:
    return TransferOut(
        transfer_ref=transfer.transfer_ref,
        amount_paise=transfer.amount_paise,
        rail=transfer.rail,
        channel=transfer.channel,
        status=transfer.status,
        initiated_at=transfer.initiated_at,
        decided_at=transfer.decided_at,
        executed_at=transfer.executed_at,
        from_account_masked=from_masked,
        cancelled_reason=transfer.cancelled_reason.value if transfer.cancelled_reason else None,
    )


def contact_brief(contact: TrustedContact | None, ctx: Ctx) -> TrustedContactBrief | None:
    if contact is None:
        return None
    return TrustedContactBrief(
        display_name=contact.display_name,
        relationship=contact.relationship,
        phone_last4=contact.phone_last4,
        status=contact.status.value,
        effective_from=contact.effective_from,
        active=contact_service.is_active(contact, ctx.clock.now()),
    )
