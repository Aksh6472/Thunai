"""Teller console (FR-14, FR-06c). Re-scores may escalate, never de-escalate (API_SPEC §7)."""

import uuid
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.core.errors import InvalidStateTransition, NotFound
from app.core.security import Principal
from app.domain.enums import (
    AssessmentTrigger,
    Decision,
    HoldTier,
    SignalSource,
    SignalType,
    TellerItem,
    Tier,
    TransferStatus,
)
from app.domain.models import Assessment, AssessmentInput
from app.domain.policy import decide, max_decision, max_tier
from app.domain.scoring import assess
from app.models import Customer, RiskAssessment, RiskEpisode, Signal, Transfer
from app.repositories import customers, events, queries, risk, transfers
from app.schemas.teller import ChecklistIn, ScriptOut, ScriptStep
from app.schemas.transfers import AssessmentResult, HoldListItem, Page
from app.services import hold_service, transfer_ops
from app.services.assessment_service import save_assessment, to_result
from app.services.context import Ctx
from app.services.hold_read_service import branch_scope, customer_brief, list_item, top_reasons

SCRIPTS_PATH = Path(__file__).resolve().parents[1] / "domain" / "i18n" / "scripts.yaml"
NO_DE_ESCALATION = "NO_DE_ESCALATION"


def load_scripts(path: Path = SCRIPTS_PATH) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    for step in data["steps"]:
        if not (step.get("id") and step.get("en") and step.get("ta")):
            raise ValueError(f"script step incomplete: {step}")
    return data


def queue(session: Session, ctx: Ctx, principal: Principal) -> Page[HoldListItem]:
    """Branch-channel transfers that are WARNED or HELD, most urgent first."""
    hold_service.expire_cooling_off(session, ctx.clock.now())
    branch = branch_scope(principal)
    rows = queries.branch_queue(session, branch_code=branch)
    latest = queries.latest_assessments(session, [t.id for t, _, _ in rows])
    items = []
    for transfer, customer, hold in rows:
        assessment = latest.get(transfer.id)
        if hold is not None:
            items.append(list_item(hold, transfer, customer, assessment))
        elif assessment is not None:
            items.append(_warned_item(transfer, customer, assessment))
    items.sort(
        key=lambda i: (0 if i.tier is Tier.VERY_HIGH else 1, i.status == "WARNED", i.created_at)
    )
    return Page[HoldListItem](items=items, next_cursor=None)


def _warned_item(
    transfer: Transfer, customer: Customer, assessment: RiskAssessment
) -> HoldListItem:
    return HoldListItem(
        id=None,
        transfer_ref=transfer.transfer_ref,
        customer=customer_brief(customer),
        amount_paise=transfer.amount_paise,
        tier=assessment.tier,
        status="WARNED",
        transfer_status=transfer.status,
        channel=transfer.channel,
        contact_response=None,
        top_reasons=top_reasons(assessment),
        created_at=transfer.decided_at or transfer.initiated_at,
        cooling_off_until=None,
    )


def apply_checklist(
    session: Session, ctx: Ctx, principal: Principal, transfer_ref: str, body: ChecklistIn
) -> AssessmentResult:
    transfer = transfers.by_ref(session, transfer_ref, for_update=True)
    if transfer is None:
        raise NotFound("transfer")
    hold_service.check_branch(principal, customers.by_id(session, transfer.customer_id))
    if transfer.status not in (TransferStatus.WARNED, TransferStatus.HELD):
        raise InvalidStateTransition(
            f"Transfer already {transfer.status.value.lower()}: the checklist cannot change it."
        )
    previous = risk.latest_assessment(session, transfer.id)
    if previous is None:
        raise NotFound("transfer")

    now = ctx.clock.now()
    session.add(
        Signal(
            customer_id=transfer.customer_id,
            transfer_id=transfer.id,
            signal_type=SignalType.TELLER_CHECKLIST,
            value={"items": [i.value for i in body.items], "customer_said": body.customer_said},
            source=SignalSource.TELLER,
            observed_at=now,
            recorded_by_staff_id=uuid.UUID(principal.id),
        )
    )
    session.flush()
    observed: set[TellerItem] = set()
    for signal in events.checklist_signals(session, transfer.id):
        observed |= {TellerItem(i) for i in signal.value.get("items", [])}

    # Re-score the stored input with the teller's observations. `customer_said` is not an input.
    snapshot = AssessmentInput.model_validate(previous.input_snapshot)
    ordered = tuple(i for i in TellerItem if i in observed)
    inp = snapshot.model_copy(
        update={"signals": snapshot.signals.model_copy(update={"teller_items": ordered})}
    )
    result = _escalate_only(assess(inp, ctx.cfg), previous.tier, previous.decision, inp, ctx)

    episode = session.get(RiskEpisode, previous.episode_id) if previous.episode_id else None
    row = save_assessment(
        session, transfer, episode, inp, result, AssessmentTrigger.TELLER_CHECKLIST, now
    )
    hold = transfers.hold_for_transfer(session, transfer.id)
    if result.decision is Decision.HOLD and hold is None:
        transfer_ops.move(transfer, TransferStatus.HELD)
        status = result.initial_hold_status
        assert status is not None  # noqa: S101 (HOLD always carries an initial status)
        hold = hold_service.create_hold(
            session, ctx, transfer, row, HoldTier(result.tier.value), status, now
        )
    elif hold is not None and result.tier is Tier.VERY_HIGH:
        hold_service.escalate_to_very_high(session, hold, principal.id)
    session.commit()
    return to_result(transfer, row, hold)


def _escalate_only(
    result: Assessment, prev_tier: Tier, prev_decision: Decision, inp: AssessmentInput, ctx: Ctx
) -> Assessment:
    tier = max_tier(result.tier, prev_tier)
    decision = max_decision(result.decision, prev_decision)
    if (tier, decision) == (result.tier, result.decision):
        return result
    policy = decide(
        tier,
        inp.transfer.amount_paise,
        inp.signals.fri_rating,
        inp.has_active_trusted_contact,
        ctx.cfg,
    )
    return result.model_copy(
        update={
            "tier": tier,
            "decision": decision,
            "initial_hold_status": policy.initial_hold_status,
            "overrides_applied": (*result.overrides_applied, NO_DE_ESCALATION),
        }
    )


def script(
    session: Session,
    ctx: Ctx,
    principal: Principal,
    scripts: dict[str, Any],
    hold_id: uuid.UUID,
    lang: str,
) -> ScriptOut:
    hold, _, _ = hold_service.load_for_staff(session, hold_id, principal)
    return ScriptOut(
        lang=lang,  # type: ignore[arg-type]
        tier=Tier(hold.tier.value),
        steps=[ScriptStep(id=s["id"], text=s[lang]) for s in scripts["steps"]],
        reviewed_by_native_speaker=bool(scripts["reviewed_by_native_speaker"][lang]),
    )
