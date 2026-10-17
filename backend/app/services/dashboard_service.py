"""Ops dashboard reads (FR-16, API_SPEC §10). Urgency order follows DESIGN §5.2."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.core.security import Principal
from app.domain.enums import (
    TIER_ORDER,
    AssessmentTrigger,
    Decision,
    EpisodeStatus,
    HoldStatus,
    Tier,
    TransferStatus,
)
from app.models import (
    AccountEvent,
    Customer,
    Hold,
    RiskAssessment,
    RiskEpisode,
    Signal,
    Transfer,
)
from app.repositories import customers, queries, risk
from app.schemas.dashboard import (
    AccountBrief,
    AlertItem,
    BaselineOut,
    CustomerListItem,
    CustomerRisk,
    RecentAssessment,
    Summary,
    TimelineItem,
)
from app.schemas.transfers import Page
from app.services import hold_service
from app.services.context import Ctx
from app.services.hold_read_service import (
    branch_scope,
    contact_brief,
    customer_brief,
    episode_out,
    top_reasons,
)

IST = timezone(timedelta(hours=5, minutes=30))
ACTIVE = [HoldStatus.AWAITING_CONTACT, HoldStatus.AWAITING_OFFICER]
KIND_ORDER = {"HOLD": 0, "WARN": 1, "WATCH": 2}
WATCH_TIERS = [Tier.MEDIUM, Tier.HIGH, Tier.VERY_HIGH]


def _scope(stmt: Any, principal: Principal) -> Any:
    branch = branch_scope(principal)
    return stmt.where(Customer.branch_code == branch) if branch else stmt


def summary(session: Session, ctx: Ctx, principal: Principal) -> Summary:
    now = ctx.clock.now()
    hold_service.expire_cooling_off(session, now)
    holds = session.execute(
        _scope(
            select(Hold.status, func.count(), func.coalesce(func.sum(Transfer.amount_paise), 0))
            .join(Transfer, Transfer.id == Hold.transfer_id)
            .join(Customer, Customer.id == Transfer.customer_id)
            .where(Hold.status.in_(ACTIVE))
            .group_by(Hold.status),
            principal,
        )
    ).all()
    counts = {row[0]: int(row[1]) for row in holds}
    amount = sum(int(row[2]) for row in holds)
    day_start = now.astimezone(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    warnings = session.scalar(
        _scope(
            select(func.count())
            .select_from(RiskAssessment)
            .join(Transfer, Transfer.id == RiskAssessment.transfer_id)
            .join(Customer, Customer.id == Transfer.customer_id)
            .where(
                RiskAssessment.trigger == AssessmentTrigger.INITIAL,
                RiskAssessment.decision == Decision.WARN,
                RiskAssessment.assessed_at >= day_start,
            ),
            principal,
        )
    )
    watch = session.scalar(
        _scope(
            select(func.count())
            .select_from(RiskEpisode)
            .join(Customer, Customer.id == RiskEpisode.customer_id)
            .where(
                RiskEpisode.status == EpisodeStatus.OPEN, RiskEpisode.watch_tier.in_(WATCH_TIERS)
            ),
            principal,
        )
    )
    awaiting_contact = counts.get(HoldStatus.AWAITING_CONTACT, 0)
    awaiting_officer = counts.get(HoldStatus.AWAITING_OFFICER, 0)
    return Summary(
        active_holds=awaiting_contact + awaiting_officer,
        awaiting_contact=awaiting_contact,
        awaiting_officer=awaiting_officer,
        warnings_today=int(warnings or 0),
        watchlist_count=int(watch or 0),
        amount_on_hold_paise=amount,
    )


def alerts(
    session: Session,
    ctx: Ctx,
    principal: Principal,
    *,
    kind: str | None,
    tier: Tier | None,
    limit: int,
    cursor: str | None,
) -> Page[AlertItem]:
    hold_service.expire_cooling_off(session, ctx.clock.now())
    items: list[AlertItem] = []
    hold_rows = (
        queries.hold_rows(
            session,
            branch_code=branch_scope(principal),
            statuses=ACTIVE,
            tier=None,
            limit=1000,
            cursor=None,
        )
        if kind in (None, "HOLD")
        else []
    )
    warned = (
        session.execute(
            _scope(
                select(Transfer, Customer)
                .join(Customer, Customer.id == Transfer.customer_id)
                .where(Transfer.status == TransferStatus.WARNED),
                principal,
            ).limit(1000)
        ).all()
        if kind in (None, "WARN")
        else []
    )
    # One query for the latest assessment of every listed transfer (≤ 5 queries per request).
    latest = queries.latest_assessments(
        session, [t.id for _, t, _ in hold_rows] + [row[0].id for row in warned]
    )
    for hold, transfer, customer in hold_rows:
        reasons = top_reasons(latest.get(transfer.id), 1)
        items.append(
            AlertItem(
                kind="HOLD",
                id=str(hold.id),
                customer=customer_brief(customer),
                tier=Tier(hold.tier.value),
                status=hold.status.value,
                amount_paise=transfer.amount_paise,
                channel=transfer.channel,
                transfer_ref=transfer.transfer_ref,
                hold_id=str(hold.id),
                contact_response=hold.contact_response.value if hold.contact_response else None,
                top_reason=reasons[0] if reasons else None,
                created_at=hold.created_at,
                cooling_off_until=hold.cooling_off_until,
            )
        )
    for transfer, customer in warned:
        assessment = latest.get(transfer.id)
        reasons = top_reasons(assessment, 1)
        items.append(
            AlertItem(
                kind="WARN",
                id=transfer.transfer_ref,
                customer=customer_brief(customer),
                tier=assessment.tier if assessment else Tier.MEDIUM,
                status="WARNED",
                amount_paise=transfer.amount_paise,
                channel=transfer.channel,
                transfer_ref=transfer.transfer_ref,
                top_reason=reasons[0] if reasons else None,
                created_at=transfer.decided_at or transfer.initiated_at,
            )
        )
    if kind in (None, "WATCH"):
        watched = session.execute(
            _scope(
                select(RiskEpisode, Customer)
                .join(Customer, Customer.id == RiskEpisode.customer_id)
                .where(
                    RiskEpisode.status == EpisodeStatus.OPEN,
                    RiskEpisode.watch_tier.in_(WATCH_TIERS),
                ),
                principal,
            ).limit(1000)
        ).all()
        for episode, customer in watched:
            items.append(
                AlertItem(
                    kind="WATCH",
                    id=str(episode.id),
                    customer=customer_brief(customer),
                    tier=episode.watch_tier,
                    status="WATCHLIST",
                    watch_score=episode.watch_score,
                    created_at=episode.last_stage_at,
                )
            )
    if tier is not None:
        items = [i for i in items if i.tier is tier]
    far_future = datetime.max.replace(tzinfo=IST)
    items.sort(
        key=lambda i: (
            -TIER_ORDER.index(i.tier),
            KIND_ORDER[i.kind],
            i.cooling_off_until or far_future,
            -i.created_at.timestamp(),
            i.id,
        )
    )
    offset = 0
    decoded = queries.decode_cursor(cursor)
    if decoded:
        offset = int(decoded[0])
    limit = max(1, min(limit, 100))
    page = items[offset : offset + limit]
    more = offset + limit < len(items)
    return Page[AlertItem](
        items=page, next_cursor=queries.encode_cursor([offset + limit]) if more else None
    )


def search_customers(
    session: Session, principal: Principal, *, search: str | None, limit: int, cursor: str | None
) -> Page[CustomerListItem]:
    limit = max(1, min(limit, 100))
    decoded = queries.decode_cursor(cursor)
    rows = queries.customer_search(
        session,
        branch_code=branch_scope(principal),
        search=search,
        limit=limit,
        after=str(decoded[0]) if decoded else None,
    )
    page = rows[:limit]
    items = [
        CustomerListItem(
            id=str(c.id),
            external_ref=c.external_ref,
            display_name=c.display_name,
            preferred_language=c.preferred_language.value,
            branch_code=c.branch_code,
        )
        for c in page
    ]
    more = len(rows) > limit
    return Page[CustomerListItem](
        items=items, next_cursor=queries.encode_cursor([page[-1].external_ref]) if more else None
    )


def _customer(session: Session, principal: Principal, customer_id: uuid.UUID) -> Customer:
    customer = customers.by_id(session, customer_id)
    branch = branch_scope(principal)
    if customer is None or (branch and customer.branch_code != branch):
        raise NotFound("customer")
    return customer


def customer_risk(
    session: Session, ctx: Ctx, principal: Principal, customer_id: uuid.UUID
) -> CustomerRisk:
    customer = _customer(session, principal, customer_id)
    baseline = risk.baseline_for(session, customer.id)
    episode = risk.open_episode(session, customer.id) or risk.latest_episode(session, customer.id)
    recent = session.execute(
        select(RiskAssessment, Transfer, Hold.id)
        .join(Transfer, Transfer.id == RiskAssessment.transfer_id)
        .outerjoin(Hold, Hold.transfer_id == Transfer.id)
        .where(Transfer.customer_id == customer.id)
        .order_by(RiskAssessment.assessed_at.desc())
        .limit(10)
    ).all()
    return CustomerRisk(
        customer=customer_brief(customer),
        preferred_language=customer.preferred_language.value,
        accounts=[
            AccountBrief.model_validate(a) for a in customers.accounts_for(session, customer.id)
        ],
        baseline=BaselineOut.model_validate(baseline) if baseline else None,
        episode=episode_out(episode),
        trusted_contact=contact_brief(customers.current_trusted_contact(session, customer.id), ctx),
        recent_assessments=[
            RecentAssessment(
                transfer_ref=t.transfer_ref,
                amount_paise=t.amount_paise,
                decision=a.decision.value,
                tier=a.tier,
                score=a.score,
                trigger=a.trigger.value,
                assessed_at=a.assessed_at,
                transfer_status=t.status.value,
                hold_id=str(h) if h else None,
            )
            for a, t, h in recent
        ],
    )


EVENT_TITLES = {
    "FD_CLOSED": "Fixed deposit closed",
    "INTERNAL_TRANSFER_IN": "Money moved in from own account",
    "PAYEE_ADDED": "Payee added",
    "TRUSTED_CONTACT_CHANGED": "Trusted contact changed",
    "ROUTINE_DEBIT": "Routine debit",
    "ROUTINE_CREDIT": "Routine credit",
}


def timeline(
    session: Session, ctx: Ctx, principal: Principal, customer_id: uuid.UUID, days: int
) -> list[TimelineItem]:
    customer = _customer(session, principal, customer_id)
    since = ctx.clock.now() - timedelta(days=days)
    items: list[TimelineItem] = []
    for e in session.scalars(
        select(AccountEvent)
        .where(AccountEvent.customer_id == customer.id, AccountEvent.occurred_at >= since)
        .order_by(AccountEvent.occurred_at)
    ):
        items.append(
            TimelineItem(
                at=e.occurred_at,
                kind="EVENT",
                title=EVENT_TITLES[e.event_type.value],
                stage=e.stage.value if e.stage else None,
                amount_paise=e.amount_paise,
                detail={"event_id": e.event_id},
            )
        )
    for s in session.scalars(
        select(Signal).where(Signal.customer_id == customer.id, Signal.observed_at >= since)
    ):
        value = dict(s.value)
        title = (
            f"Call signal: {value.get('duration_min')} min, "
            f"{'known' if value.get('caller_known') else 'unknown'} caller (simulated)"
            if s.signal_type.value == "CALL_RISK"
            else "Teller checklist applied"
        )
        items.append(TimelineItem(at=s.observed_at, kind="SIGNAL", title=title, detail=value))
    for a, t in session.execute(
        select(RiskAssessment, Transfer)
        .join(Transfer, Transfer.id == RiskAssessment.transfer_id)
        .where(Transfer.customer_id == customer.id, RiskAssessment.assessed_at >= since)
    ).all():
        items.append(
            TimelineItem(
                at=a.assessed_at,
                kind="ASSESSMENT",
                title=(
                    f"{t.rail.value} {t.transfer_ref}: {a.decision.value} "
                    f"({a.tier.value}, {a.score})"
                ),
                amount_paise=t.amount_paise,
                detail={"transfer_status": t.status.value, "trigger": a.trigger.value},
            )
        )
    items.sort(key=lambda i: i.at)
    return items
