"""T-014: every (state, event) pair for holds and transfers (TESTING.md §2). Table-driven."""

import itertools

import pytest

from app.domain.enums import HoldStatus, HoldTier, TransferStatus
from app.domain.transitions import (
    HoldEvent,
    TransitionNotAllowed,
    next_hold_status,
    next_transfer_status,
)

A_C, A_O = HoldStatus.AWAITING_CONTACT, HoldStatus.AWAITING_OFFICER
REL, CAN = HoldStatus.RELEASED, HoldStatus.CANCELLED
E = HoldEvent

EXPECTED_HIGH = {
    (A_C, E.CONTACT_CONFIRM_GENUINE): REL,
    (A_C, E.CONTACT_REPORT_SUSPICIOUS): A_O,
    (A_C, E.CONTACT_CANNOT_REACH): A_O,
    (A_C, E.COOLING_OFF_EXPIRED): A_O,
    (A_C, E.ESCALATED_TO_VERY_HIGH): A_O,
    (A_C, E.CUSTOMER_CANCEL): CAN,
    (A_C, E.OFFICER_RELEASE): REL,
    (A_C, E.OFFICER_CANCEL): CAN,
    (A_C, E.OFFICER_KEEP_HOLDING): A_C,
    (A_O, E.CONTACT_CONFIRM_GENUINE): A_O,
    (A_O, E.CONTACT_REPORT_SUSPICIOUS): A_O,
    (A_O, E.CONTACT_CANNOT_REACH): A_O,
    (A_O, E.ESCALATED_TO_VERY_HIGH): A_O,
    (A_O, E.OFFICER_RELEASE): REL,
    (A_O, E.OFFICER_CANCEL): CAN,
    (A_O, E.OFFICER_KEEP_HOLDING): A_O,
    (A_O, E.CUSTOMER_CANCEL): CAN,
}


@pytest.mark.parametrize(("status", "event"), list(itertools.product(HoldStatus, HoldEvent)))
def test_every_hold_pair_for_high_tier(status: HoldStatus, event: HoldEvent) -> None:
    expected = EXPECTED_HIGH.get((status, event))
    if expected is None:
        with pytest.raises(TransitionNotAllowed):
            next_hold_status(status, event, HoldTier.HIGH)
    else:
        assert next_hold_status(status, event, HoldTier.HIGH) is expected


def test_very_high_hold_is_never_released_by_the_contact() -> None:
    assert next_hold_status(A_O, E.CONTACT_CONFIRM_GENUINE, HoldTier.VERY_HIGH) is A_O
    assert next_hold_status(A_C, E.CONTACT_CONFIRM_GENUINE, HoldTier.VERY_HIGH) is A_C


def test_resolved_holds_are_terminal() -> None:
    for status, event in itertools.product((REL, CAN), HoldEvent):
        with pytest.raises(TransitionNotAllowed):
            next_hold_status(status, event, HoldTier.VERY_HIGH)


T = TransferStatus
ALLOWED_TRANSFER = {
    (T.PENDING, T.EXECUTED),
    (T.PENDING, T.WARNED),
    (T.PENDING, T.HELD),
    (T.WARNED, T.EXECUTED),
    (T.WARNED, T.CANCELLED),
    (T.WARNED, T.HELD),
    (T.HELD, T.EXECUTED),
    (T.HELD, T.CANCELLED),
}


@pytest.mark.parametrize(("current", "target"), list(itertools.product(T, T)))
def test_every_transfer_pair(current: TransferStatus, target: TransferStatus) -> None:
    if (current, target) in ALLOWED_TRANSFER:
        assert next_transfer_status(current, target) is target
    else:
        with pytest.raises(TransitionNotAllowed):
            next_transfer_status(current, target)
