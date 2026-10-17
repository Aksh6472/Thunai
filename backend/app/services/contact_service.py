"""Trusted-contact requests, delivery and responses (FR-12, ARCHITECTURE §4.3, SECURITY T-02..T-05).

Tokens: 32 random bytes, SHA-256 at rest, 30 min wall-clock TTL, single use (conditional UPDATE).
"""

import logging
import re
import uuid
from datetime import timedelta

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.branding import BANK_NAME
from app.core.clock import wall_now
from app.core.errors import ContactLinkExpired, InvalidStateTransition, NotFound
from app.core.security import decrypt_pii, new_contact_token, sha256_hex
from app.domain.enums import (
    ActorType,
    ContactResponse,
    DeliveryChannel,
    DeliveryStatus,
    EpisodeStatus,
    HoldStatus,
    Language,
    ResolvedByType,
)
from app.domain.money import format_inr
from app.domain.transitions import ACTIVE_HOLD_STATUSES, HoldEvent
from app.integrations.notifier.base import Recipient
from app.models import ContactRequest, Customer, Hold, Transfer, TrustedContact
from app.repositories import customers, transfers
from app.schemas.trusted import TrustedResponseOut, TrustedView
from app.services import episode_service, hold_service, transfer_ops
from app.services.audit_service import audit
from app.services.context import Ctx

logger = logging.getLogger(__name__)

BANK_HELPLINE = "1800-XXX-XXXX (fictional)"
RESEND_LIMIT = (3, 3600)  # 3 per hold per hour (SECURITY §8)
TOKEN_LIMIT = (10, 60)
IP_LIMIT = (30, 60)

_RESPONSE_EVENTS = {
    ContactResponse.CONFIRM_GENUINE: HoldEvent.CONTACT_CONFIRM_GENUINE,
    ContactResponse.REPORT_SUSPICIOUS: HoldEvent.CONTACT_REPORT_SUSPICIOUS,
    ContactResponse.CANNOT_REACH: HoldEvent.CONTACT_CANNOT_REACH,
}


def first_name(display_name: str) -> str:
    """'R. Kamala (fictional)' -> 'Kamala'. Honorifics and initials are skipped."""
    plain = re.sub(r"\(.*?\)", "", display_name).strip()
    for token in plain.split():
        if not token.endswith(".") and len(token) > 1:
            return token
    return plain or display_name


def is_active(contact: TrustedContact | None, at: object) -> bool:
    return contact is not None and contact.effective_from <= at  # type: ignore[operator]


def message_text(customer: Customer, amount_paise: int, language: Language, link: str) -> str:
    """DESIGN §6.3 SMS template (≤ 300 characters in English)."""
    name, amount = first_name(customer.display_name), format_inr(amount_paise)
    if language is Language.TA:
        return (
            f"[{BANK_NAME}] பாதுகாப்பு சரிபார்ப்பு: {name} அவர்களின் {amount} பரிமாற்றம் "
            f"நிறுத்தி வைக்கப்பட்டுள்ளது. உங்களுக்குத் தெரிந்த எண்ணில் அவர்களை அழைத்து, பின் பதிலளிக்கவும்: "
            f"{link} . OTP/PIN ஒருபோதும் கேட்க மாட்டோம்."
        )
    return (
        f"[{BANK_NAME}] Safety check: {name}'s transfer of {amount} is paused. Call them on a "
        f"number you know, then respond: {link} . We never ask for OTP/PIN."
    )


def create_request(
    session: Session, ctx: Ctx, hold: Hold, contact: TrustedContact
) -> ContactRequest:
    token = new_contact_token()
    channel = ctx.real_notifier.channel if ctx.real_notifier else DeliveryChannel.CONSOLE
    request = ContactRequest(
        hold_id=hold.id,
        trusted_contact_id=contact.id,
        token_hash=sha256_hex(token),
        channel=channel,
        delivery_status=DeliveryStatus.QUEUED,
        expires_at=wall_now() + timedelta(minutes=ctx.settings.contact_token_ttl_minutes),
    )
    session.add(request)
    session.flush()
    audit(
        session,
        "CONTACT_REQUESTED",
        entity_type="hold",
        entity_id=hold.id,
        actor_type=ActorType.SYSTEM,
        details={"contact_request_id": str(request.id), "channel": channel.value},
    )
    # Dispatched after commit, so a notifier failure never rolls back the hold (ARCHITECTURE §4.2).
    ctx.schedule(dispatch, ctx, request.id, token)
    return request


def dispatch(ctx: Ctx, request_id: uuid.UUID, token: str) -> None:
    with ctx.session_factory() as session:
        request = session.get(ContactRequest, request_id)
        if request is None:
            return
        contact = session.get(TrustedContact, request.trusted_contact_id)
        hold = session.get(Hold, request.hold_id)
        transfer = session.get(Transfer, hold.transfer_id) if hold else None
        customer = session.get(Customer, transfer.customer_id) if transfer else None
        if contact is None or transfer is None or customer is None:
            return
        link = f"{ctx.settings.public_web_url.rstrip('/')}/t/{token}"
        text = message_text(customer, transfer.amount_paise, contact.preferred_language, link)
        phone = decrypt_pii(contact.phone_ciphertext, ctx.settings)
        chat = (
            decrypt_pii(contact.telegram_chat_id_ciphertext, ctx.settings)
            if contact.telegram_chat_id_ciphertext
            else None
        )
        recipient = Recipient(
            phone_e164=phone, telegram_chat_id=chat, display_name=contact.display_name
        )
        # The console buffer always gets the message: it is the demo's QR fallback (ADR-006).
        ctx.console.send(recipient, text, link=link)
        status, error = DeliveryStatus.SENT, None
        if ctx.real_notifier is not None:
            result = ctx.real_notifier.send(recipient, text)
            if not result.ok:
                status, error = DeliveryStatus.FAILED, result.error_code
        request.delivery_status = status
        request.delivery_error = error
        audit(
            session,
            "CONTACT_SENT" if status is DeliveryStatus.SENT else "CONTACT_FAILED",
            entity_type="hold",
            entity_id=request.hold_id,
            actor_type=ActorType.SYSTEM,
            details={"contact_request_id": str(request.id), "error": error},
        )
        session.commit()
        logger.info("contact.sent" if error is None else "contact.failed", extra={"error": error})


def resend(session: Session, ctx: Ctx, hold_id: uuid.UUID, actor_id: str) -> ContactRequest:
    hold = transfers.hold_by_id(session, hold_id, for_update=True)
    if hold is None:
        raise NotFound("hold")
    if hold.status not in ACTIVE_HOLD_STATUSES:
        raise InvalidStateTransition("The hold is already resolved.")
    transfer = session.get(Transfer, hold.transfer_id)
    contact = customers.current_trusted_contact(session, transfer.customer_id) if transfer else None
    if not is_active(contact, ctx.clock.now()):
        raise InvalidStateTransition("There is no active trusted contact to message.")
    ctx.limiter.hit(f"resend:{hold.id}", *RESEND_LIMIT)
    now = wall_now()
    session.execute(
        update(ContactRequest)
        .where(
            ContactRequest.hold_id == hold.id,
            ContactRequest.responded_at.is_(None),
            ContactRequest.expires_at > now,
        )
        .values(expires_at=now)
    )
    audit(
        session,
        "CONTACT_RESENT",
        entity_type="hold",
        entity_id=hold.id,
        actor_type=ActorType.STAFF,
        actor_id=actor_id,
    )
    request = create_request(session, ctx, hold, contact)  # type: ignore[arg-type]
    session.commit()
    return request


def _lookup(session: Session, token: str) -> ContactRequest:
    request = transfers.contact_request_by_hash(session, sha256_hex(token))
    if request is None:
        raise NotFound("contact_link", "This link is not valid.")
    if request.responded_at is not None or request.expires_at <= wall_now():
        raise ContactLinkExpired()
    return request


def view(session: Session, ctx: Ctx, token: str, client_ip: str) -> TrustedView:
    ctx.limiter.hit(f"trusted-ip:{client_ip}", *IP_LIMIT)
    ctx.limiter.hit(f"trusted-token:{sha256_hex(token)}", *TOKEN_LIMIT)
    request = _lookup(session, token)
    hold = session.get(Hold, request.hold_id)
    transfer = session.get(Transfer, hold.transfer_id) if hold else None
    customer = session.get(Customer, transfer.customer_id) if transfer else None
    contact = session.get(TrustedContact, request.trusted_contact_id)
    if hold is None or transfer is None or customer is None or contact is None:
        raise NotFound("contact_link", "This link is not valid.")
    if request.opened_at is None:
        request.opened_at = wall_now()
        audit(
            session,
            "CONTACT_OPENED",
            entity_type="hold",
            entity_id=hold.id,
            actor_type=ActorType.TRUSTED_CONTACT,
            actor_id=request.id,
        )
        session.commit()
    # Only consented, minimal data: no payee, reasons, score, account or phone (SECURITY T-03).
    return TrustedView(
        customer_first_name=first_name(customer.display_name),
        amount_display=format_inr(transfer.amount_paise),
        channel=transfer.channel,
        held_at=hold.created_at,
        bank_helpline=BANK_HELPLINE,
        language=contact.preferred_language,
        already_responded=False,
    )


def respond(
    session: Session, ctx: Ctx, token: str, response: ContactResponse, client_ip: str
) -> TrustedResponseOut:
    ctx.limiter.hit(f"trusted-ip:{client_ip}", *IP_LIMIT)
    ctx.limiter.hit(f"trusted-token:{sha256_hex(token)}", *TOKEN_LIMIT)
    now_wall = wall_now()
    # Consume first: a concurrent double submit blocks on this row, then matches nothing (410).
    consumed = session.execute(
        update(ContactRequest)
        .where(
            ContactRequest.token_hash == sha256_hex(token),
            ContactRequest.responded_at.is_(None),
            ContactRequest.expires_at > now_wall,
        )
        .values(responded_at=now_wall, response=response)
        .returning(ContactRequest.id, ContactRequest.hold_id, ContactRequest.trusted_contact_id)
    ).first()
    if consumed is None:
        session.rollback()
        _lookup(session, token)  # raises 404 or 410
        raise ContactLinkExpired()

    hold = transfers.hold_by_id(session, consumed.hold_id, for_update=True)
    if hold is None or hold.status not in ACTIVE_HOLD_STATUSES:
        session.rollback()  # leave the token unused
        raise InvalidStateTransition("This transfer has already been resolved.")
    transfer = session.get(Transfer, hold.transfer_id)
    contact = session.get(TrustedContact, consumed.trusted_contact_id)
    if transfer is None or contact is None:
        session.rollback()
        raise NotFound("contact_link", "This link is not valid.")

    previous = hold.status
    hold.contact_response = response
    hold_service.transition(hold, _RESPONSE_EVENTS[response])
    now = ctx.clock.now()
    released = hold.status is HoldStatus.RELEASED
    if released:
        hold.resolved_at = now
        hold.resolved_by_type = ResolvedByType.TRUSTED_CONTACT
        transfer_ops.execute(session, transfer, now, ctx.cfg)
        episode_service.close_episode(
            session, hold_service.episode_id_for(session, hold), EpisodeStatus.CLOSED_BENIGN, now
        )
    audit(
        session,
        "CONTACT_RESPONDED",
        entity_type="hold",
        entity_id=hold.id,
        actor_type=ActorType.TRUSTED_CONTACT,
        actor_id=consumed.id,
        details={"response": response.value, "from": previous.value, "to": hold.status.value},
    )
    if released:
        audit(
            session,
            "HOLD_RELEASED",
            entity_type="hold",
            entity_id=hold.id,
            actor_type=ActorType.TRUSTED_CONTACT,
            actor_id=consumed.id,
        )
    session.commit()
    return TrustedResponseOut(
        result_key="RELEASED" if released else "SENT_TO_OFFICER",
        message=_result_message(released, contact.preferred_language),
    )


def _result_message(released: bool, language: Language) -> str:
    if language is Language.TA:
        if released:
            return "நன்றி — பரிமாற்றம் விடுவிக்கப்பட்டது."
        return (
            "நன்றி — வங்கி அதிகாரி இப்போது அவர்களைத் தொடர்பு கொள்வார். அவர்கள் ஆபத்தில் இருப்பதாக "
            "நினைத்தால் 1930 அல்லது 112 ஐ அழைக்கவும்."
        )
    if released:
        return "Thank you — the transfer has been released."
    return (
        "Thank you — a bank officer will contact them now. If you believe they are in danger, "
        "call 1930 or 112."
    )
