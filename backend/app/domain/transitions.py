"""Explicit state-transition tables for transfers and holds (DATABASE_SCHEMA §3.8, §3.13). Pure.

State changes happen only through these tables (CLAUDE.md §7).
"""

from enum import StrEnum

from app.domain.enums import HoldStatus, HoldTier, TransferStatus


class TransitionNotAllowed(ValueError):
    """The requested event is not allowed from the current state."""


TRANSFER_TRANSITIONS: dict[TransferStatus, frozenset[TransferStatus]] = {
    TransferStatus.PENDING: frozenset(
        {TransferStatus.EXECUTED, TransferStatus.WARNED, TransferStatus.HELD}
    ),
    TransferStatus.WARNED: frozenset(
        {TransferStatus.EXECUTED, TransferStatus.CANCELLED, TransferStatus.HELD}
    ),
    TransferStatus.HELD: frozenset({TransferStatus.EXECUTED, TransferStatus.CANCELLED}),
    TransferStatus.EXECUTED: frozenset(),
    TransferStatus.CANCELLED: frozenset(),
}


def next_transfer_status(current: TransferStatus, target: TransferStatus) -> TransferStatus:
    """WARNED → HELD exists for teller escalation (API_SPEC §7: WARN → HOLD)."""
    if target not in TRANSFER_TRANSITIONS[current]:
        raise TransitionNotAllowed(f"transfer {current} -> {target}")
    return target


class HoldEvent(StrEnum):
    CONTACT_CONFIRM_GENUINE = "CONTACT_CONFIRM_GENUINE"
    CONTACT_REPORT_SUSPICIOUS = "CONTACT_REPORT_SUSPICIOUS"
    CONTACT_CANNOT_REACH = "CONTACT_CANNOT_REACH"
    COOLING_OFF_EXPIRED = "COOLING_OFF_EXPIRED"
    ESCALATED_TO_VERY_HIGH = "ESCALATED_TO_VERY_HIGH"
    OFFICER_RELEASE = "OFFICER_RELEASE"
    OFFICER_CANCEL = "OFFICER_CANCEL"
    OFFICER_KEEP_HOLDING = "OFFICER_KEEP_HOLDING"
    CUSTOMER_CANCEL = "CUSTOMER_CANCEL"


_A_CONTACT, _A_OFFICER = HoldStatus.AWAITING_CONTACT, HoldStatus.AWAITING_OFFICER
_RELEASED, _CANCELLED = HoldStatus.RELEASED, HoldStatus.CANCELLED

# (status, event) -> next status, for a HIGH hold. VERY_HIGH differs only where noted below.
HOLD_TRANSITIONS: dict[tuple[HoldStatus, HoldEvent], HoldStatus] = {
    (_A_CONTACT, HoldEvent.CONTACT_CONFIRM_GENUINE): _RELEASED,
    (_A_CONTACT, HoldEvent.CONTACT_REPORT_SUSPICIOUS): _A_OFFICER,
    (_A_CONTACT, HoldEvent.CONTACT_CANNOT_REACH): _A_OFFICER,
    (_A_CONTACT, HoldEvent.COOLING_OFF_EXPIRED): _A_OFFICER,
    (_A_CONTACT, HoldEvent.ESCALATED_TO_VERY_HIGH): _A_OFFICER,
    (_A_CONTACT, HoldEvent.CUSTOMER_CANCEL): _CANCELLED,
    (_A_CONTACT, HoldEvent.OFFICER_RELEASE): _RELEASED,
    (_A_CONTACT, HoldEvent.OFFICER_CANCEL): _CANCELLED,
    (_A_CONTACT, HoldEvent.OFFICER_KEEP_HOLDING): _A_CONTACT,
    # Once an officer owns the hold, contact responses are recorded but change nothing.
    (_A_OFFICER, HoldEvent.CONTACT_CONFIRM_GENUINE): _A_OFFICER,
    (_A_OFFICER, HoldEvent.CONTACT_REPORT_SUSPICIOUS): _A_OFFICER,
    (_A_OFFICER, HoldEvent.CONTACT_CANNOT_REACH): _A_OFFICER,
    (_A_OFFICER, HoldEvent.ESCALATED_TO_VERY_HIGH): _A_OFFICER,
    (_A_OFFICER, HoldEvent.OFFICER_RELEASE): _RELEASED,
    (_A_OFFICER, HoldEvent.OFFICER_CANCEL): _CANCELLED,
    (_A_OFFICER, HoldEvent.OFFICER_KEEP_HOLDING): _A_OFFICER,
    (_A_OFFICER, HoldEvent.CUSTOMER_CANCEL): _CANCELLED,
}

ACTIVE_HOLD_STATUSES = frozenset({_A_CONTACT, _A_OFFICER})


def next_hold_status(current: HoldStatus, event: HoldEvent, tier: HoldTier) -> HoldStatus:
    """VERY_HIGH holds can never be released by the trusted contact (ADR-012)."""
    if tier is HoldTier.VERY_HIGH and event is HoldEvent.CONTACT_CONFIRM_GENUINE:
        if current in ACTIVE_HOLD_STATUSES:
            return current
    target = HOLD_TRANSITIONS.get((current, event))
    if target is None:
        raise TransitionNotAllowed(f"hold {current} --{event}-->")
    return target
