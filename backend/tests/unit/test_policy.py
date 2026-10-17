"""T-029: tier → decision with overrides (AI_DESIGN §6.2–6.3). Table-driven."""

import pytest

from app.domain.enums import Decision, FriRating, HoldStatus, Tier
from app.domain.policy import decide, max_decision, max_tier
from tests.factories import cfg, rupees

BIG = rupees(5_00_000)
SMALL = rupees(10_000)

CASES = [
    # tier, amount, fri, active contact -> decision, tier, initial status, overrides
    (Tier.LOW, BIG, None, True, Decision.ALLOW, Tier.LOW, None, ()),
    (Tier.MEDIUM, BIG, None, True, Decision.WARN, Tier.MEDIUM, None, ()),
    (Tier.HIGH, BIG, None, True, Decision.HOLD, Tier.HIGH, HoldStatus.AWAITING_CONTACT, ()),
    (
        Tier.HIGH,
        BIG,
        None,
        False,
        Decision.HOLD,
        Tier.HIGH,
        HoldStatus.AWAITING_OFFICER,
        ("NO_ACTIVE_TRUSTED_CONTACT",),
    ),
    (
        Tier.VERY_HIGH,
        BIG,
        None,
        True,
        Decision.HOLD,
        Tier.VERY_HIGH,
        HoldStatus.AWAITING_OFFICER,
        (),
    ),
    (
        Tier.VERY_HIGH,
        BIG,
        None,
        False,
        Decision.HOLD,
        Tier.VERY_HIGH,
        HoldStatus.AWAITING_OFFICER,
        (),
    ),
    (
        Tier.LOW,
        BIG,
        FriRating.VERY_HIGH,
        True,
        Decision.HOLD,
        Tier.HIGH,
        HoldStatus.AWAITING_CONTACT,
        ("FRI_VERY_HIGH_FLOOR",),
    ),
    (
        Tier.VERY_HIGH,
        BIG,
        FriRating.VERY_HIGH,
        True,
        Decision.HOLD,
        Tier.VERY_HIGH,
        HoldStatus.AWAITING_OFFICER,
        (),
    ),
    (Tier.MEDIUM, BIG, FriRating.HIGH, True, Decision.WARN, Tier.MEDIUM, None, ()),
    (Tier.HIGH, SMALL, None, True, Decision.WARN, Tier.HIGH, None, ("BELOW_FLOOR_NO_HOLD",)),
    (
        Tier.LOW,
        SMALL,
        FriRating.VERY_HIGH,
        True,
        Decision.WARN,
        Tier.HIGH,
        None,
        ("FRI_VERY_HIGH_FLOOR", "BELOW_FLOOR_NO_HOLD"),
    ),
    (
        Tier.HIGH,
        rupees(50_000),
        None,
        True,
        Decision.HOLD,
        Tier.HIGH,
        HoldStatus.AWAITING_CONTACT,
        (),
    ),
]


@pytest.mark.parametrize(
    ("tier", "amount", "fri", "contact", "decision", "final_tier", "status", "overrides"), CASES
)
def test_policy_table(
    tier: Tier,
    amount: int,
    fri: FriRating | None,
    contact: bool,
    decision: Decision,
    final_tier: Tier,
    status: HoldStatus | None,
    overrides: tuple[str, ...],
) -> None:
    result = decide(tier, amount, fri, contact, cfg())
    assert result.decision is decision
    assert result.tier is final_tier
    assert result.initial_hold_status is status
    assert result.overrides == overrides


def test_escalation_helpers_never_lower() -> None:
    assert max_tier(Tier.VERY_HIGH, Tier.HIGH) is Tier.VERY_HIGH
    assert max_tier(Tier.MEDIUM, Tier.HIGH) is Tier.HIGH
    assert max_decision(Decision.HOLD, Decision.WARN) is Decision.HOLD
    assert max_decision(Decision.ALLOW, Decision.WARN) is Decision.WARN
