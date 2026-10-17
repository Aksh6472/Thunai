"""Signal adapters: map signals to reason drafts (AI_DESIGN §6.1, FR-06). Pure."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.domain.config import ScoringConfig
from app.domain.enums import FriRating, TellerItem
from app.domain.models import CallSignal

SIMULATED = "SIMULATED"


@dataclass(frozen=True)
class ReasonDraft:
    """A scored contribution before its EN/TA text is rendered."""

    code: str
    points: int
    stage: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


def is_call_fresh(call: CallSignal, at: datetime, cfg: ScoringConfig) -> bool:
    """Active (observed recently) or ended at most `call_freshness_minutes` before `at`."""
    window = timedelta(minutes=cfg.windows.call_freshness_minutes)
    if call.observed_at > at:
        return False
    reference = call.ended_at if call.ended_at is not None else call.observed_at
    return at - reference <= window


def call_reason(call: CallSignal | None, at: datetime, cfg: ScoringConfig) -> ReasonDraft | None:
    if call is None or call.caller_known or not is_call_fresh(call, at, cfg):
        return None
    points = 0
    for band in cfg.points.long_call_unknown:
        if call.duration_min >= band.min_duration_min:
            points = band.points
    if points == 0:
        return None
    return ReasonDraft(
        "LONG_CALL_UNKNOWN",
        points,
        evidence={
            "duration_min": call.duration_min,
            "call_type": call.call_type.value,
            "active": call.ended_at is None,
            "source": SIMULATED,
        },
    )


TELLER_CODES: dict[TellerItem, str] = {
    TellerItem.ON_CALL: "TELLER_ON_CALL",
    TellerItem.DISTRESSED: "TELLER_DISTRESSED",
    TellerItem.FOLLOWING_INSTRUCTIONS: "TELLER_FOLLOWING_INSTRUCTIONS",
    TellerItem.MENTIONS_AUTHORITY: "TELLER_MENTIONS_AUTHORITY",
}


def teller_reasons(items: tuple[TellerItem, ...], cfg: ScoringConfig) -> list[ReasonDraft]:
    """One reason per observed item. The teller total is capped (default 30).

    The cap is applied by trimming the lowest-value items last, so the reasons still sum exactly.
    """
    weights = cfg.points.teller
    raw = {
        TellerItem.ON_CALL: weights.on_call,
        TellerItem.DISTRESSED: weights.distressed,
        TellerItem.FOLLOWING_INSTRUCTIONS: weights.following_instructions,
        TellerItem.MENTIONS_AUTHORITY: weights.mentions_authority,
    }
    ordered = sorted(set(items), key=lambda i: (-raw[i], list(TellerItem).index(i)))
    remaining = weights.cap
    drafts = []
    for item in ordered:
        points = min(raw[item], remaining)
        remaining -= points
        evidence: dict[str, Any] = {"observed_by": "TELLER"}
        if points < raw[item]:
            evidence["capped"] = True
        drafts.append(ReasonDraft(TELLER_CODES[item], points, evidence=evidence))
    return drafts


def fri_reason(
    rating: FriRating | None, unavailable: bool, last4: str | None, cfg: ScoringConfig
) -> ReasonDraft | None:
    """FRI is optional (ADR-016): no number means no reason and no penalty."""
    if unavailable:
        return ReasonDraft("FRI_UNAVAILABLE", 0, evidence={"source": SIMULATED})
    if rating is None:
        return None
    points = {
        FriRating.MEDIUM: cfg.points.fri_risk.medium,
        FriRating.HIGH: cfg.points.fri_risk.high,
        FriRating.VERY_HIGH: cfg.points.fri_risk.very_high,
    }[rating]
    evidence: dict[str, Any] = {"rating": rating.value, "source": SIMULATED}
    if last4:
        evidence["linked_msisdn_last4"] = last4
    return ReasonDraft("FRI_RISK", points, evidence=evidence)


def contact_changed_reason(
    changed_at: datetime | None, at: datetime, cfg: ScoringConfig
) -> ReasonDraft | None:
    if changed_at is None or changed_at > at:
        return None
    age = at - changed_at
    if age > timedelta(days=cfg.windows.trusted_contact_changed_days):
        return None
    return ReasonDraft(
        "TRUSTED_CONTACT_RECENTLY_CHANGED",
        cfg.points.trusted_contact_recently_changed,
        evidence={"changed_hours_ago": int(age.total_seconds() // 3600)},
    )
