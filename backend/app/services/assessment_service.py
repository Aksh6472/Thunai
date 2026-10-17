"""Transfer assessment orchestration (FR-09, ARCHITECTURE §4.2, ADR-014).

Fail closed: any unexpected error becomes 503 ASSESSMENT_UNAVAILABLE. Never ALLOW by default.
The engine never sees `scenario_label` (it is only written to the transfer row).
"""

import logging
import statistics
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import (
    AssessmentUnavailable,
    IdempotencyConflict,
    InsufficientBalance,
    NotFound,
    ThunaiError,
)
from app.core.security import Principal
from app.domain.enums import (
    ActorType,
    AssessmentTrigger,
    Channel,
    Decision,
    HoldTier,
    Rail,
    Stage,
    TellerItem,
    TransferStatus,
)
from app.domain.models import (
    Assessment,
    AssessmentInput,
    PayeeFacts,
    Signals,
    StageEvent,
    TransferFacts,
)
from app.domain.scoring import assess
from app.integrations.fri.base import FriUnavailable
from app.models import Customer, Hold, Payee, RiskAssessment, RiskEpisode, Transfer
from app.repositories import customers, events, risk, transfers
from app.schemas.transfers import AssessmentResult, ReasonOut
from app.services import (
    baseline_service,
    contact_service,
    episode_service,
    hold_service,
    transfer_ops,
)
from app.services.audit_service import audit
from app.services.context import Ctx
from app.services.engine_io import call_signal
from app.services.ingest_service import request_hash

logger = logging.getLogger(__name__)

STATUS_FOR_DECISION = {
    Decision.ALLOW: TransferStatus.EXECUTED,
    Decision.WARN: TransferStatus.WARNED,
    Decision.HOLD: TransferStatus.HELD,
}


@dataclass(frozen=True)
class TransferRequest:
    transfer_ref: str
    from_account: str
    payee_ref: str
    amount_paise: int
    rail: Rail
    channel: Channel
    initiated_at: datetime
    scenario_label: str | None
    digest: str


def to_result(transfer: Transfer, row: RiskAssessment, hold: Hold | None) -> AssessmentResult:
    return AssessmentResult(
        transfer_ref=transfer.transfer_ref,
        transfer_status=transfer.status,
        decision=row.decision,
        tier=row.tier,
        score=row.score,
        raw_score=row.raw_score,
        reasons=[ReasonOut.model_validate(r) for r in row.reasons],
        overrides_applied=list(row.overrides_applied),
        hold_id=str(hold.id) if hold else None,
        assessment_id=str(row.id),
        trigger=row.trigger.value,
        config_version=row.config_version,
        assessed_at=row.assessed_at,
    )


def existing_result(
    session: Session, transfer_ref: str, digest: str
) -> tuple[Transfer, RiskAssessment, Hold | None] | None:
    """Idempotency (API_SPEC §2.3): same body → original result; different body → 409."""
    transfer = transfers.by_ref(session, transfer_ref)
    if transfer is None:
        return None
    if transfer.request_hash != digest:
        raise IdempotencyConflict()
    row = risk.latest_assessment(session, transfer.id)
    if row is None:
        raise AssessmentUnavailable()
    return transfer, row, transfers.hold_for_transfer(session, transfer.id)


def assess_new(
    session: Session, ctx: Ctx, customer_ref: str, req: TransferRequest, *, check_balance: bool
) -> tuple[Transfer, RiskAssessment, Hold | None]:
    try:
        return _assess_new(session, ctx, customer_ref, req, check_balance=check_balance)
    except ThunaiError:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        logger.exception("assessment.failed")
        raise AssessmentUnavailable() from None


def _assess_new(
    session: Session, ctx: Ctx, customer_ref: str, req: TransferRequest, *, check_balance: bool
) -> tuple[Transfer, RiskAssessment, Hold | None]:
    customer = customers.by_ref(session, customer_ref, for_update=True)
    if customer is None:
        raise NotFound("customer")
    account = customers.account_by_masked(session, customer.id, req.from_account)
    if account is None:
        raise NotFound("account")
    payee = customers.payee_by_ref(session, customer.id, req.payee_ref)
    if payee is None:
        raise NotFound("payee")
    if check_balance and req.amount_paise > account.balance_paise:
        raise InsufficientBalance()

    now = ctx.clock.now()
    episode_row = episode_service.current_open(session, customer.id, req.initiated_at, ctx.cfg)
    inp = build_input(session, ctx, customer, req, account.balance_paise, payee, episode_row, now)
    result = assess(inp, ctx.cfg)

    transfer = Transfer(
        transfer_ref=req.transfer_ref,
        customer_id=customer.id,
        from_account_id=account.id,
        payee_id=payee.id,
        amount_paise=req.amount_paise,
        rail=req.rail,
        channel=req.channel,
        status=TransferStatus.PENDING,
        initiated_at=req.initiated_at,
        decided_at=now,
        scenario_label=req.scenario_label,
        request_hash=req.digest,
    )
    session.add(transfer)
    session.flush()

    if result.is_s4:
        stage = StageEvent(
            stage=Stage.S4_HIGH_VALUE,
            event_id=req.transfer_ref,
            occurred_at=req.initiated_at,
            amount_paise=req.amount_paise,
            payee_id=str(payee.id),
        )
        episode_row = episode_service.record_stage(session, customer.id, stage, ctx.cfg)

    row = save_assessment(
        session, transfer, episode_row, inp, result, AssessmentTrigger.INITIAL, now
    )
    hold = None
    if result.decision is Decision.ALLOW:
        transfer_ops.execute(session, transfer, now, ctx.cfg)
    else:
        transfer_ops.move(transfer, STATUS_FOR_DECISION[result.decision])
    if result.decision is Decision.HOLD and result.initial_hold_status is not None:
        hold = hold_service.create_hold(
            session,
            ctx,
            transfer,
            row,
            HoldTier(result.tier.value),
            result.initial_hold_status,
            now,
        )
    session.commit()
    logger.info(
        "assessment.created",
        extra={"tier": result.tier.value, "decision": result.decision.value, "score": result.score},
    )
    return transfer, row, hold


def build_input(
    session: Session,
    ctx: Ctx,
    customer: Customer,
    req: TransferRequest,
    balance_paise: int,
    payee: Payee,
    episode_row: RiskEpisode | None,
    now: datetime,
    teller_items: tuple[TellerItem, ...] = (),
) -> AssessmentInput:
    prior = transfers.executed_to_payee(session, payee.id, req.initiated_at)
    amounts = sorted(t.amount_paise for t in prior)
    fri_rating, fri_unavailable = None, False
    if payee.linked_msisdn_hmac:
        started = time.perf_counter()
        try:
            fri_rating = ctx.fri.rating(session, payee.linked_msisdn_hmac)
        except FriUnavailable:
            fri_unavailable = True
            logger.warning("fri.unavailable")
        if (time.perf_counter() - started) * 1000 > ctx.settings.fri_timeout_ms:
            fri_rating, fri_unavailable = None, True
            logger.warning("fri.timeout")
    contact = customers.current_trusted_contact(session, customer.id)
    stages = tuple(StageEvent.model_validate(s) for s in episode_row.stages) if episode_row else ()
    return AssessmentInput(
        customer_id=str(customer.id),
        now=now,
        baseline=baseline_service.get_or_compute(session, customer.id, now, ctx.cfg),
        episode_stages=stages,
        transfer=TransferFacts(
            transfer_ref=req.transfer_ref,
            amount_paise=req.amount_paise,
            rail=req.rail,
            channel=req.channel,
            initiated_at=req.initiated_at,
            source_account_balance_paise=balance_paise,
            payee=PayeeFacts(
                payee_id=str(payee.id),
                payee_ref=payee.payee_ref,
                added_at=payee.added_at,
                prior_successful_transfers=len(prior),
                recurring_amount_paise=round(statistics.median(amounts))
                if len(amounts) >= 2
                else None,
            ),
        ),
        signals=Signals(
            fri_rating=fri_rating,
            fri_unavailable=fri_unavailable,
            fri_linked_msisdn_last4=payee.linked_msisdn_last4 if fri_rating else None,
            call=call_signal(events.latest_call_signal(session, customer.id, now)),
            teller_items=teller_items,
            trusted_contact_changed_at=customers.latest_contact_registration(session, customer.id),
        ),
        has_active_trusted_contact=contact_service.is_active(contact, now),
    )


def save_assessment(
    session: Session,
    transfer: Transfer,
    episode_row: RiskEpisode | None,
    inp: AssessmentInput,
    result: Assessment,
    trigger: AssessmentTrigger,
    now: datetime,
) -> RiskAssessment:
    row = RiskAssessment(
        id=uuid.uuid4(),
        transfer_id=transfer.id,
        episode_id=episode_row.id if episode_row else None,
        trigger=trigger,
        raw_score=result.raw_score,
        score=result.score,
        tier=result.tier,
        decision=result.decision,
        reasons=[r.model_dump(mode="json") for r in result.reasons],
        overrides_applied=list(result.overrides_applied),
        input_snapshot=inp.model_dump(mode="json"),
        config_version=result.config_version,
        assessed_at=now,
    )
    session.add(row)
    session.flush()
    audit(
        session,
        "ASSESSMENT_CREATED",
        entity_type="transfer",
        entity_id=transfer.transfer_ref,
        actor_type=ActorType.SYSTEM,
        details={
            "assessment_id": str(row.id),
            "trigger": trigger.value,
            "tier": result.tier.value,
            "decision": result.decision.value,
            "score": result.score,
            "config_version": result.config_version,
        },
    )
    return row


def digest_of(body: dict[str, object]) -> str:
    return request_hash(body)


def get_result(session: Session, principal: Principal, transfer_ref: str) -> AssessmentResult:
    transfer = transfers.by_ref(session, transfer_ref)
    if transfer is None:
        raise NotFound("transfer")
    if not principal.is_service:
        hold_service.check_branch(principal, customers.by_id(session, transfer.customer_id))
    row = risk.latest_assessment(session, transfer.id)
    if row is None:
        raise NotFound("transfer")
    return to_result(transfer, row, transfers.hold_for_transfer(session, transfer.id))
