"""Report drafts for 1930 / cybercrime.gov.in (FR-15). Never auto-submitted."""

import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import Forbidden, InvalidStateTransition, NotFound
from app.core.security import Principal
from app.domain.enums import (
    ActorType,
    Channel,
    ContactResponse,
    NarrativeSource,
    ReportStatus,
    Role,
    SignalType,
    TransferStatus,
)
from app.domain.money import format_inr
from app.integrations.llm.template import render_narrative
from app.models import FraudReport, RiskEpisode
from app.repositories import events, queries, transfers
from app.schemas.reports import MarkFiledIn, ReportOut, ReportPatchIn
from app.services import hold_service
from app.services.audit_service import audit
from app.services.context import Ctx

IST = timezone(timedelta(hours=5, minutes=30))
INCIDENT_CATEGORY = "Online Financial Fraud — impersonation / 'digital arrest' (suspected)"
STAGE_TEXT = {
    "S1_LIQUIDATION": "Fixed deposit closed before maturity",
    "S2_POOLING": "Funds moved into one account from the customer's other accounts",
    "S3_NEW_PAYEE": "New beneficiary added",
    "S4_HIGH_VALUE": "Large transfer requested",
}
STATUS_TEXT = {
    TransferStatus.HELD: "HELD — not executed",
    TransferStatus.CANCELLED: "CANCELLED — not executed",
    TransferStatus.EXECUTED: "EXECUTED",
    TransferStatus.WARNED: "WARNED — not executed",
    TransferStatus.PENDING: "PENDING",
}
RESPONSE_TEXT = {
    ContactResponse.CONFIRM_GENUINE: "Trusted contact said the payment is genuine",
    ContactResponse.REPORT_SUSPICIOUS: "Trusted contact said this looks like a scam",
    ContactResponse.CANNOT_REACH: "Trusted contact could not reach the customer",
}


def _ist(dt: datetime) -> str:
    return dt.astimezone(IST).strftime("%d %b %Y, %H:%M IST")


def _age(delta: timedelta) -> str:
    hours = int(delta.total_seconds() // 3600)
    if hours < 1:
        return "less than an hour"
    return f"{hours} hours" if hours < 48 else f"{hours // 24} days"


def build_facts(
    session: Session, hold_id: uuid.UUID, customer_reported: dict[str, Any]
) -> dict[str, Any]:
    core = queries.hold_detail_core(session, hold_id)
    if core is None:
        raise NotFound("hold")
    hold, transfer, customer, payee, from_masked, _ = core
    timeline: list[dict[str, Any]] = []
    episode_id = hold_service.episode_id_for(session, hold)
    episode = session.get(RiskEpisode, episode_id) if episode_id else None
    seen: set[str] = set()
    for stage in episode.stages if episode else []:
        if stage["stage"] == "S4_HIGH_VALUE" or stage["stage"] in seen:
            continue
        seen.add(stage["stage"])
        at = datetime.fromisoformat(stage["occurred_at"])
        what = STAGE_TEXT[stage["stage"]]
        if stage.get("amount_paise"):
            what += f" ({format_inr(stage['amount_paise'])})"
        timeline.append({"at": at.isoformat(), "at_display": _ist(at), "what": what})
    call = events.latest_call_signal(session, customer.id, transfer.initiated_at)
    if (
        call is not None
        and call.signal_type is SignalType.CALL_RISK
        and not call.value.get("caller_known")
    ):
        timeline.append(
            {
                "at": call.observed_at.isoformat(),
                "at_display": _ist(call.observed_at),
                "what": (
                    f"Customer's phone reported a {call.value['duration_min']}-minute call "
                    "with an unknown caller (consented flag, simulated)"
                ),
            }
        )
    timeline.sort(key=lambda t: t["at"])
    structured = {
        "incident_category": INCIDENT_CATEGORY,
        "transaction": {
            "amount_paise": transfer.amount_paise,
            "rail": transfer.rail.value,
            "initiated_at": transfer.initiated_at.isoformat(),
            "status": STATUS_TEXT[transfer.status],
            "from_account_masked": from_masked,
            "beneficiary_bank": payee.bank_name,
            "beneficiary_ifsc": payee.ifsc,
            "beneficiary_account_masked": payee.masked_account,
        },
        "timeline": [{"at": t["at"], "what": t["what"]} for t in timeline],
        "safety_hold": {
            "placed_at": hold.created_at.isoformat(),
            "tier": hold.tier.value,
            "contact_response": RESPONSE_TEXT.get(hold.contact_response)
            if hold.contact_response
            else None,
        },
        "helpline": "1930",
        "portal": "https://cybercrime.gov.in",
    }
    narrative_facts = {
        "customer_name": customer.display_name,
        "initiated_at_display": _ist(transfer.initiated_at),
        "channel_display": "branch counter"
        if transfer.channel is Channel.BRANCH
        else "mobile app"
        if transfer.channel is Channel.APP
        else "net banking",
        "payee_age_display": _age(transfer.initiated_at - payee.added_at),
        "transaction": structured["transaction"],
        "timeline": timeline,
        "customer_reported": customer_reported,
    }
    return {
        "structured": structured,
        "narrative_facts": narrative_facts,
        "hold": hold,
        "customer": customer,
    }


def report_out(report: FraudReport) -> ReportOut:
    return ReportOut(
        id=str(report.id),
        hold_id=str(report.hold_id),
        status=report.status,
        structured_fields=report.structured_fields,
        customer_reported=report.customer_reported,
        narrative_text=report.narrative_text,
        narrative_source=report.narrative_source,
        acknowledgement_number=report.acknowledgement_number,
        updated_at=report.updated_at,
    )


def create_or_get(
    session: Session, ctx: Ctx, principal: Principal, hold_id: uuid.UUID, use_llm: bool
) -> tuple[ReportOut, bool, str | None]:
    """Returns (report, created, llm_fallback_reason)."""
    hold, _, _ = hold_service.load_for_staff(session, hold_id, principal)
    existing = transfers.report_for_hold(session, hold.id)
    if existing is not None:
        return report_out(existing), False, None
    facts = build_facts(session, hold.id, {})
    fallback = None
    narrative = render_narrative(facts["narrative_facts"])
    source = NarrativeSource.TEMPLATE
    if use_llm:
        fallback = "LLM_DISABLED" if not ctx.settings.llm_enabled else "LLM_NOT_CONFIGURED"
    staff_id = uuid.UUID(principal.id)
    report = FraudReport(
        hold_id=hold.id,
        status=ReportStatus.DRAFT,
        structured_fields=facts["structured"],
        customer_reported={},
        narrative_text=narrative,
        narrative_source=source,
        created_by_staff_id=staff_id,
        updated_by_staff_id=staff_id,
        updated_at=datetime.now(UTC),
    )
    session.add(report)
    session.flush()
    audit(
        session,
        "REPORT_CREATED",
        entity_type="hold",
        entity_id=hold.id,
        actor_type=ActorType.STAFF,
        actor_id=principal.id,
        details={"report_id": str(report.id), "narrative_source": source.value},
    )
    session.commit()
    return report_out(report), True, fallback


def _load(session: Session, principal: Principal, report_id: uuid.UUID) -> FraudReport:
    report = session.get(FraudReport, report_id)
    if report is None:
        raise NotFound("report")
    hold_service.load_for_staff(session, report.hold_id, principal)  # branch scope → 404
    return report


def get(session: Session, principal: Principal, report_id: uuid.UUID) -> ReportOut:
    return report_out(_load(session, principal, report_id))


def patch(
    session: Session, principal: Principal, report_id: uuid.UUID, body: ReportPatchIn
) -> ReportOut:
    report = _load(session, principal, report_id)
    if report.status is ReportStatus.FILED_EXTERNALLY:
        raise InvalidStateTransition("A filed report can no longer be edited.")
    changed = []
    if body.customer_reported is not None:
        report.customer_reported = body.customer_reported.model_dump(exclude_none=True)
        changed.append("customer_reported")
        if report.narrative_source is NarrativeSource.TEMPLATE and body.narrative_text is None:
            facts = build_facts(session, report.hold_id, report.customer_reported)
            report.narrative_text = render_narrative(facts["narrative_facts"])
    if body.narrative_text is not None:
        report.narrative_text = body.narrative_text
        report.narrative_source = NarrativeSource.EDITED
        changed.append("narrative_text")
    if body.status is not None:
        report.status = ReportStatus(body.status)
        changed.append("status")
    report.updated_by_staff_id = uuid.UUID(principal.id)
    report.updated_at = datetime.now(UTC)
    audit(
        session,
        "REPORT_UPDATED",
        entity_type="hold",
        entity_id=report.hold_id,
        actor_type=ActorType.STAFF,
        actor_id=principal.id,
        details={"report_id": str(report.id), "changed": changed},
    )
    session.commit()
    return report_out(report)


def mark_filed(
    session: Session, principal: Principal, report_id: uuid.UUID, body: MarkFiledIn
) -> ReportOut:
    if principal.role is not Role.OFFICER:
        raise Forbidden()
    report = _load(session, principal, report_id)
    report.status = ReportStatus.FILED_EXTERNALLY
    report.acknowledgement_number = body.acknowledgement_number
    report.updated_by_staff_id = uuid.UUID(principal.id)
    report.updated_at = datetime.now(UTC)
    audit(
        session,
        "REPORT_FILED_EXTERNALLY",
        entity_type="hold",
        entity_id=report.hold_id,
        actor_type=ActorType.STAFF,
        actor_id=principal.id,
        details={"report_id": str(report.id)},
    )
    session.commit()
    return report_out(report)
