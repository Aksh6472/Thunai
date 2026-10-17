"""Customer app (API_SPEC §5). Customers see only their own resources (404 otherwise)."""

import uuid

from sqlalchemy.orm import Session

from app.core.errors import InvalidStateTransition, NotFound, Unauthenticated
from app.core.security import Principal
from app.domain.enums import (
    ActorType,
    CancelledReason,
    Channel,
    ConsentType,
    TransferStatus,
)
from app.models import Consent, Customer, Hold, Transfer
from app.repositories import customers, transfers
from app.schemas.customer import (
    AccountOut,
    ConsentIn,
    ConsentOut,
    CustomerContactOut,
    CustomerOverview,
    CustomerPayeeOut,
    TrustedContactIn,
    TrustedContactOut,
)
from app.schemas.transfers import (
    ContactAsked,
    CustomerTransferIn,
    CustomerTransferOut,
    TransferStatusOut,
    WarningResponseIn,
)
from app.services import assessment_service, contact_service, hold_service, transfer_ops
from app.services.assessment_service import TransferRequest
from app.services.audit_service import audit
from app.services.context import Ctx
from app.services.ingest_service import replace_trusted_contact, request_hash

MESSAGE_KEYS = {
    TransferStatus.EXECUTED: "transfer.executed",
    TransferStatus.WARNED: "transfer.warned",
    TransferStatus.HELD: "transfer.held",
    TransferStatus.CANCELLED: "transfer.cancelled",
    TransferStatus.PENDING: "transfer.pending",
}


def me(session: Session, principal: Principal) -> Customer:
    try:
        customer = customers.by_id(session, uuid.UUID(principal.id))
    except ValueError:
        customer = None
    if customer is None:
        raise Unauthenticated()
    return customer


def _own_transfer(
    session: Session, customer: Customer, ref: str, *, for_update: bool = False
) -> Transfer:
    transfer = transfers.by_ref(session, ref, for_update=for_update)
    if transfer is None or transfer.customer_id != customer.id:
        raise NotFound("transfer")
    return transfer


def _contact_status(contact_status: str, active: bool) -> str:
    if contact_status == "REVOKED":
        return contact_status
    return "ACTIVE" if active else "PENDING_ACTIVATION"


def overview(session: Session, ctx: Ctx, principal: Principal) -> CustomerOverview:
    customer = me(session, principal)
    contact = customers.current_trusted_contact(session, customer.id)
    consents = {
        t.value: bool((c := customers.latest_consent(session, customer.id, t)) and c.granted)
        for t in ConsentType
    }
    return CustomerOverview(
        customer_ref=customer.external_ref,
        display_name=customer.display_name,
        preferred_language=customer.preferred_language,
        accounts=[
            AccountOut.model_validate(a) for a in customers.accounts_for(session, customer.id)
        ],
        payees=[
            CustomerPayeeOut.model_validate(p) for p in customers.payees_for(session, customer.id)
        ],
        trusted_contact=CustomerContactOut(
            display_name=contact.display_name,
            relationship=contact.relationship,
            phone_last4=contact.phone_last4,
            status=_contact_status(
                contact.status.value, contact_service.is_active(contact, ctx.clock.now())
            ),
            effective_from=contact.effective_from,
        )
        if contact
        else None,
        consents=consents,
    )


def customer_view(session: Session, transfer: Transfer, hold: Hold | None) -> CustomerTransferOut:
    """One generic outcome; never the score or reasons (ADR-013)."""
    from app.domain.enums import Decision

    decision = {
        TransferStatus.WARNED: Decision.WARN,
        TransferStatus.HELD: Decision.HOLD,
    }.get(transfer.status)
    if decision is None:
        decision = Decision.HOLD if hold else Decision.ALLOW
        if transfer.status is TransferStatus.CANCELLED and hold is None:
            decision = Decision.WARN
    asked = None
    if hold is not None and transfers.contact_requests_for_hold(session, hold.id):
        contact = customers.current_trusted_contact(session, transfer.customer_id)
        if contact is not None:
            asked = ContactAsked(
                display_name=contact.display_name, relationship=contact.relationship
            )
    return CustomerTransferOut(
        transfer_ref=transfer.transfer_ref,
        transfer_status=transfer.status,
        decision=decision,
        hold_id=str(hold.id) if hold else None,
        hold_status=hold.status if hold else None,
        message_key=MESSAGE_KEYS[transfer.status],
        contact_asked=asked,
    )


def create_transfer(
    session: Session, ctx: Ctx, principal: Principal, body: CustomerTransferIn
) -> tuple[CustomerTransferOut, bool]:
    customer = me(session, principal)
    digest = request_hash({"customer_ref": customer.external_ref, **body.model_dump(mode="json")})
    existing = assessment_service.existing_result(session, body.transfer_ref, digest)
    if existing is not None:
        transfer, _, hold = existing
        return customer_view(session, transfer, hold), True
    req = TransferRequest(
        transfer_ref=body.transfer_ref,
        from_account=body.from_account,
        payee_ref=body.payee_ref,
        amount_paise=body.amount_paise,
        rail=body.rail,
        channel=Channel.APP,
        initiated_at=body.initiated_at or ctx.clock.now(),
        scenario_label=None,
        digest=digest,
    )
    transfer, _, hold = assessment_service.assess_new(
        session, ctx, customer.external_ref, req, check_balance=True
    )
    return customer_view(session, transfer, hold), False


def transfer_status(
    session: Session, ctx: Ctx, principal: Principal, ref: str
) -> CustomerTransferOut:
    hold_service.expire_cooling_off(session, ctx.clock.now())
    customer = me(session, principal)
    transfer = _own_transfer(session, customer, ref)
    return customer_view(session, transfer, transfers.hold_for_transfer(session, transfer.id))


def warning_response(
    session: Session, ctx: Ctx, principal: Principal, ref: str, body: WarningResponseIn
) -> TransferStatusOut:
    customer = me(session, principal)
    transfer = _own_transfer(session, customer, ref, for_update=True)
    if transfer.status is not TransferStatus.WARNED:
        raise InvalidStateTransition("This transfer is not waiting for a warning response.")
    if body.action == "CONTINUE":
        transfer_ops.execute(session, transfer, ctx.clock.now(), ctx.cfg)
        action = "WARNING_ACKNOWLEDGED_CONTINUE"
    else:
        transfer_ops.cancel(transfer, CancelledReason.CUSTOMER_CANCELLED)
        action = "WARNING_ACKNOWLEDGED_CANCEL"
    audit(
        session,
        action,
        entity_type="transfer",
        entity_id=transfer.transfer_ref,
        actor_type=ActorType.CUSTOMER,
        actor_id=customer.id,
    )
    session.commit()
    return TransferStatusOut(transfer_ref=transfer.transfer_ref, transfer_status=transfer.status)


def cancel(session: Session, ctx: Ctx, principal: Principal, ref: str) -> TransferStatusOut:
    customer = me(session, principal)
    transfer = _own_transfer(session, customer, ref, for_update=True)
    hold = transfers.hold_for_transfer(session, transfer.id)
    if transfer.status is not TransferStatus.HELD or hold is None:
        raise InvalidStateTransition("Only a paused transfer can be cancelled here.")
    hold = transfers.hold_by_id(session, hold.id, for_update=True)
    assert hold is not None  # noqa: S101 (row exists: just read it)
    hold_service.customer_cancel(session, hold, transfer, ctx, str(customer.id))
    session.commit()
    return TransferStatusOut(transfer_ref=transfer.transfer_ref, transfer_status=transfer.status)


def record_consent(session: Session, ctx: Ctx, principal: Principal, body: ConsentIn) -> ConsentOut:
    customer = me(session, principal)
    consent = Consent(
        customer_id=customer.id,
        consent_type=body.consent_type,
        granted=body.granted,
        text_version=body.text_version,
        recorded_at=ctx.clock.now(),
    )
    session.add(consent)
    audit(
        session,
        "CONSENT_CHANGED",
        entity_type="customer",
        entity_id=customer.id,
        actor_type=ActorType.CUSTOMER,
        actor_id=customer.id,
        details={
            "consent_type": body.consent_type.value,
            "granted": body.granted,
            "text_version": body.text_version,
        },
    )
    session.commit()
    return ConsentOut.model_validate(consent)


def register_contact(
    session: Session, ctx: Ctx, principal: Principal, body: TrustedContactIn
) -> TrustedContactOut:
    customer = me(session, principal)
    contact = replace_trusted_contact(
        session,
        customer,
        display_name=body.display_name,
        relationship=body.relationship,
        phone_e164=body.phone_e164,
        language=body.preferred_language,
        registered_at=ctx.clock.now(),
        settings=ctx.settings,
        actor_type=ActorType.CUSTOMER,
    )
    session.commit()
    return TrustedContactOut(status=contact.status.value, effective_from=contact.effective_from)
