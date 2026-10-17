"""Event and call-signal ingestion (FR-03, FR-06b, ARCHITECTURE §4.1).

Events for one customer are serialised by locking the customer row.
"""

import hashlib
import json
import logging
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import Conflict, ConsentRequired, IdempotencyConflict, NotFound
from app.core.security import encrypt_pii, hmac_msisdn
from app.core.settings import Settings
from app.domain.config import ScoringConfig
from app.domain.enums import (
    AccountStatus,
    ActorType,
    ConsentType,
    EventType,
    SignalSource,
    SignalType,
    Stage,
    TrustedContactStatus,
)
from app.domain.models import StageEvent
from app.domain.stages import detect_stage, pooled_amount
from app.models import AccountEvent, Customer, Payee, RiskEpisode, Signal, TrustedContact
from app.repositories import customers, events, risk
from app.schemas.events import (
    CallSignalAccepted,
    CallSignalIn,
    EpisodeWatch,
    EventAccepted,
    EventIn,
    PayeeAddedEvent,
    TrustedContactChangedEvent,
)
from app.services import baseline_service, episode_service
from app.services.audit_service import audit
from app.services.engine_io import event_facts

logger = logging.getLogger(__name__)


def request_hash(body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _watch(row: RiskEpisode | None) -> EpisodeWatch | None:
    if row is None:
        return None
    return EpisodeWatch(id=str(row.id), watch_score=row.watch_score, watch_tier=row.watch_tier)


def ingest_event(
    session: Session, body: EventIn, settings: Settings, cfg: ScoringConfig
) -> tuple[EventAccepted, bool]:
    """Returns (result, replayed)."""
    digest = request_hash(body.model_dump(mode="json"))
    existing = events.by_event_id(session, body.event_id)
    if existing is not None:
        if existing.request_hash != digest:
            raise IdempotencyConflict()
        return _replay(session, existing), True

    customer = customers.by_ref(session, body.customer_ref, for_update=True)
    if customer is None:
        raise NotFound("customer")
    stored_payload = _apply_side_effects(session, customer, body, settings)

    row = AccountEvent(
        event_id=body.event_id,
        customer_id=customer.id,
        account_id=_account_id(session, customer, body.account_ref),
        event_type=EventType(body.event_type),
        amount_paise=body.amount_paise,
        occurred_at=body.occurred_at,
        payload=stored_payload,
        request_hash=digest,
    )
    session.add(row)
    session.flush()

    episode_row = _track_stage(session, customer, row, cfg)
    if episode_row is None and row.event_type is EventType.TRUSTED_CONTACT_CHANGED:
        episode_row = episode_service.current_open(session, customer.id, row.occurred_at, cfg)
        if episode_row is not None:
            baseline = baseline_service.get_or_compute(session, customer.id, row.occurred_at, cfg)
            episode_service.refresh_watch(
                session, episode_row, baseline, row.occurred_at, row.event_id, cfg
            )
    if episode_row is None:
        episode_row = risk.open_episode(session, customer.id)
    result = EventAccepted(
        event_id=row.event_id,
        stage_detected=row.stage.value if row.stage else None,
        episode=_watch(episode_row),
    )
    session.commit()
    logger.info(
        "event.ingested",
        extra={"event_type": row.event_type.value, "stage": result.stage_detected},
    )
    return result, False


def _account_id(session: Session, customer: Customer, masked: str | None) -> uuid.UUID | None:
    if masked is None:
        return None
    account = customers.account_by_masked(session, customer.id, masked)
    return account.id if account else None


def _adjust_balance(session: Session, customer: Customer, masked: str | None, delta: int) -> None:
    if masked is None:
        return
    account = customers.account_by_masked(session, customer.id, masked)
    if account is not None:
        account.balance_paise = max(0, account.balance_paise + delta)


def _apply_side_effects(
    session: Session, customer: Customer, body: EventIn, settings: Settings
) -> dict[str, Any]:
    """Update simulated balances, payees and contacts. Returns the payload to store (no raw PII)."""
    payload: dict[str, Any] = body.payload.model_dump(mode="json")
    amount = body.amount_paise or 0
    if body.event_type == "FD_CLOSED":
        fd = customers.account_by_masked(session, customer.id, body.account_ref or "")
        if fd is not None:
            fd.balance_paise = 0
            fd.status = AccountStatus.CLOSED
        _adjust_balance(session, customer, payload["proceeds_to_account"], amount)
    elif body.event_type == "INTERNAL_TRANSFER_IN":
        _adjust_balance(session, customer, payload["from_account"], -amount)
        _adjust_balance(session, customer, payload["to_account"], amount)
    elif body.event_type == "ROUTINE_DEBIT":
        _adjust_balance(session, customer, body.account_ref, -amount)
    elif body.event_type == "ROUTINE_CREDIT":
        _adjust_balance(session, customer, body.account_ref, amount)
    elif isinstance(body, PayeeAddedEvent):
        payload = _add_payee(session, customer, body, settings)
    elif isinstance(body, TrustedContactChangedEvent):
        payload = _change_contact(session, customer, body, settings)
    return payload


def _add_payee(
    session: Session, customer: Customer, body: PayeeAddedEvent, settings: Settings
) -> dict[str, Any]:
    p = body.payload
    if customers.payee_by_ref(session, customer.id, p.payee_ref) is not None:
        raise Conflict(f"Payee {p.payee_ref} already exists.")
    payee = Payee(
        customer_id=customer.id,
        payee_ref=p.payee_ref,
        display_name=p.display_name,
        bank_name=p.bank_name,
        ifsc=p.ifsc,
        masked_account=p.masked_account,
        linked_msisdn_hmac=hmac_msisdn(p.linked_msisdn, settings) if p.linked_msisdn else None,
        linked_msisdn_last4=p.linked_msisdn[-4:] if p.linked_msisdn else None,
        added_at=body.occurred_at,
        added_channel=p.channel,
    )
    session.add(payee)
    session.flush()
    stored = p.model_dump(mode="json", exclude={"linked_msisdn"})
    stored["payee_id"] = str(payee.id)
    stored["linked_msisdn_last4"] = payee.linked_msisdn_last4
    return stored


def _change_contact(
    session: Session, customer: Customer, body: TrustedContactChangedEvent, settings: Settings
) -> dict[str, Any]:
    p = body.payload
    replace_trusted_contact(
        session,
        customer,
        display_name=p.display_name,
        relationship=p.relationship,
        phone_e164=p.phone_e164,
        language=p.preferred_language,
        registered_at=body.occurred_at,
        settings=settings,
        actor_type=ActorType.SERVICE,
    )
    stored = p.model_dump(mode="json", exclude={"phone_e164"})
    stored["phone_last4"] = p.phone_e164[-4:]
    return stored


def replace_trusted_contact(
    session: Session,
    customer: Customer,
    *,
    display_name: str,
    relationship: str,
    phone_e164: str,
    language: str,
    registered_at: Any,
    settings: Settings,
    actor_type: ActorType,
    telegram_chat_id: str | None = None,
) -> TrustedContact:
    """FR-24: a new or changed contact is effective only after the activation delay."""
    current = customers.current_trusted_contact(session, customer.id)
    if current is not None:
        current.status = TrustedContactStatus.REVOKED
        session.flush()
    contact = TrustedContact(
        customer_id=customer.id,
        display_name=display_name,
        relationship=relationship,
        phone_ciphertext=encrypt_pii(phone_e164, settings),
        phone_last4=phone_e164[-4:],
        telegram_chat_id_ciphertext=encrypt_pii(telegram_chat_id, settings)
        if telegram_chat_id
        else None,
        preferred_language=language,
        registered_at=registered_at,
        effective_from=registered_at + timedelta(hours=settings.trusted_contact_activation_hours),
        status=TrustedContactStatus.PENDING_ACTIVATION,
    )
    session.add(contact)
    session.flush()
    audit(
        session,
        "TRUSTED_CONTACT_REGISTERED",
        entity_type="trusted_contact",
        entity_id=contact.id,
        actor_type=actor_type,
        actor_id=customer.id if actor_type is ActorType.CUSTOMER else "simulator",
        details={
            "replaced": current is not None,
            "effective_from": contact.effective_from.isoformat(),
        },
    )
    return contact


def _track_stage(
    session: Session, customer: Customer, row: AccountEvent, cfg: ScoringConfig
) -> RiskEpisode | None:
    baseline = baseline_service.get_or_compute(session, customer.id, row.occurred_at, cfg)
    facts = event_facts(row)
    window = timedelta(hours=cfg.stages.pooling_window_hours)
    recent = [
        event_facts(e)
        for e in events.in_window(
            session,
            customer.id,
            row.occurred_at - window,
            row.occurred_at,
            (EventType.INTERNAL_TRANSFER_IN, EventType.FD_CLOSED),
        )
        if e.id != row.id
    ]
    stage = detect_stage(facts, baseline, recent, cfg)
    if stage is None:
        return None
    row.stage = stage
    amount = row.amount_paise
    if stage is Stage.S2_POOLING:
        amount = pooled_amount(facts, recent, cfg)
    stage_event = StageEvent(
        stage=stage,
        event_id=row.event_id,
        occurred_at=row.occurred_at,
        amount_paise=amount,
        payee_id=facts.payee_id,
    )
    episode_row = episode_service.record_stage(session, customer.id, stage_event, cfg)
    return episode_service.refresh_watch(
        session, episode_row, baseline, row.occurred_at, row.event_id, cfg
    )


def _replay(session: Session, row: AccountEvent) -> EventAccepted:
    """The original result: the watch point this event produced, if any."""
    episode_row = risk.latest_episode(session, row.customer_id)
    watch = _watch(risk.open_episode(session, row.customer_id))
    if row.stage is not None and episode_row is not None:
        for point in episode_row.watch_history:
            if point.get("trigger_event_id") == row.event_id:
                watch = EpisodeWatch(
                    id=str(episode_row.id), watch_score=point["score"], watch_tier=point["tier"]
                )
    return EventAccepted(
        event_id=row.event_id,
        stage_detected=row.stage.value if row.stage else None,
        episode=watch,
    )


def ingest_call_signal(
    session: Session, body: CallSignalIn, cfg: ScoringConfig
) -> CallSignalAccepted:
    customer = customers.by_ref(session, body.customer_ref, for_update=True)
    if customer is None:
        raise NotFound("customer")
    consent = customers.latest_consent(session, customer.id, ConsentType.CALL_SIGNAL)
    if consent is None or not consent.granted:
        raise ConsentRequired("The customer has not granted call-signal consent.")
    signal = Signal(
        customer_id=customer.id,
        signal_type=SignalType.CALL_RISK,
        value={
            "call_type": body.call_type.value,
            "caller_known": body.caller_known,
            "duration_min": body.duration_min,
            "ended_at": body.ended_at.isoformat() if body.ended_at else None,
        },
        source=SignalSource.DEVICE_SIMULATED,
        observed_at=body.observed_at,
    )
    session.add(signal)
    session.flush()
    episode_row = episode_service.current_open(session, customer.id, body.observed_at, cfg)
    if episode_row is not None:
        baseline = baseline_service.get_or_compute(session, customer.id, body.observed_at, cfg)
        episode_service.refresh_watch(
            session, episode_row, baseline, body.observed_at, f"SIG-{signal.id}", cfg
        )
    result = CallSignalAccepted(episode=_watch(episode_row))
    session.commit()
    return result
