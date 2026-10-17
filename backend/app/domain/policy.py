"""Tier → decision, with deterministic overrides (AI_DESIGN §6.2–6.3). Pure."""

from dataclasses import dataclass

from app.domain.config import ScoringConfig
from app.domain.enums import DECISION_ORDER, TIER_ORDER, Decision, FriRating, HoldStatus, Tier

FRI_VERY_HIGH_FLOOR = "FRI_VERY_HIGH_FLOOR"
NO_ACTIVE_TRUSTED_CONTACT = "NO_ACTIVE_TRUSTED_CONTACT"
BELOW_FLOOR_NO_HOLD = "BELOW_FLOOR_NO_HOLD"

TIER_DECISION = {
    Tier.LOW: Decision.ALLOW,
    Tier.MEDIUM: Decision.WARN,
    Tier.HIGH: Decision.HOLD,
    Tier.VERY_HIGH: Decision.HOLD,
}


@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    tier: Tier
    overrides: tuple[str, ...]
    initial_hold_status: HoldStatus | None


def max_tier(a: Tier, b: Tier) -> Tier:
    return a if TIER_ORDER.index(a) >= TIER_ORDER.index(b) else b


def max_decision(a: Decision, b: Decision) -> Decision:
    return a if DECISION_ORDER.index(a) >= DECISION_ORDER.index(b) else b


def decide(
    tier: Tier,
    amount_paise: int,
    fri_rating: FriRating | None,
    has_active_contact: bool,
    cfg: ScoringConfig,
) -> PolicyResult:
    overrides: list[str] = []
    floor = cfg.overrides.fri_very_high_floor_tier
    if fri_rating is FriRating.VERY_HIGH and max_tier(tier, floor) is not tier:
        tier = floor
        overrides.append(FRI_VERY_HIGH_FLOOR)

    decision = TIER_DECISION[tier]
    if decision is Decision.HOLD and amount_paise < cfg.overrides.hold_floor_paise:
        decision = Decision.WARN
        overrides.append(BELOW_FLOOR_NO_HOLD)

    hold_status = None
    if decision is Decision.HOLD:
        if tier is Tier.VERY_HIGH:
            hold_status = HoldStatus.AWAITING_OFFICER
        elif has_active_contact:
            hold_status = HoldStatus.AWAITING_CONTACT
        else:
            hold_status = HoldStatus.AWAITING_OFFICER
            overrides.append(NO_ACTIVE_TRUSTED_CONTACT)
    return PolicyResult(decision, tier, tuple(overrides), hold_status)
