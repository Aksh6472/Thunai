"""Stage detection (AI_DESIGN §5.1) and the canonical-order count (§5.3)."""

from collections.abc import Iterable, Sequence
from datetime import timedelta

from app.domain.config import ScoringConfig
from app.domain.enums import STAGE_ORDER, EventType, Stage
from app.domain.models import Baseline, EventFacts, StageEvent


def detect_stage(
    event: EventFacts,
    baseline: Baseline,
    recent_events: Sequence[EventFacts],
    cfg: ScoringConfig,
) -> Stage | None:
    """S1-S3 from an account event. `recent_events` are the customer's earlier events."""
    if event.event_type is EventType.FD_CLOSED:
        is_premature = (
            event.maturity_date is not None and event.occurred_at.date() < event.maturity_date
        )
        return Stage.S1_LIQUIDATION if is_premature else None
    if event.event_type is EventType.PAYEE_ADDED:
        return Stage.S3_NEW_PAYEE
    if event.event_type is EventType.INTERNAL_TRANSFER_IN:
        return Stage.S2_POOLING if _is_pooling(event, baseline, recent_events, cfg) else None
    return None


def _inbound_window(
    event: EventFacts, recent_events: Sequence[EventFacts], cfg: ScoringConfig
) -> list[EventFacts]:
    """Inbound money into the event's account within the pooling window, including the event.

    Inbound means internal transfers from the customer's own accounts, or FD proceeds.
    """
    if event.to_account is None:
        return []
    window_start = event.occurred_at - timedelta(hours=cfg.stages.pooling_window_hours)
    return [event] + [
        e
        for e in recent_events
        if e.event_id != event.event_id
        and e.to_account == event.to_account
        and e.event_type in (EventType.INTERNAL_TRANSFER_IN, EventType.FD_CLOSED)
        and window_start <= e.occurred_at <= event.occurred_at
    ]


def pooled_amount(
    event: EventFacts, recent_events: Sequence[EventFacts], cfg: ScoringConfig
) -> int:
    """Money moved in from the customer's other accounts (FD proceeds excluded), for evidence."""
    inbound = _inbound_window(event, recent_events, cfg)
    return sum(
        e.amount_paise or 0 for e in inbound if e.event_type is EventType.INTERNAL_TRANSFER_IN
    )


def _is_pooling(
    event: EventFacts, baseline: Baseline, recent_events: Sequence[EventFacts], cfg: ScoringConfig
) -> bool:
    """≥2 inbound transfers into one account within 72 h, sum ≥ ₹1 L and ≥ 5× median."""
    params = cfg.stages
    inbound = _inbound_window(event, recent_events, cfg)
    total = sum(e.amount_paise or 0 for e in inbound)
    return (
        len(inbound) >= params.pooling_min_inbound_count
        and total >= params.pooling_min_sum_paise
        and total >= params.pooling_min_multiple_of_median * baseline.median_outbound_paise
    )


def is_high_value(amount_paise: int, baseline: Baseline, cfg: ScoringConfig) -> bool:
    """S4: amount ≥ ₹2 L and ≥ 10× the customer's median outbound."""
    params = cfg.stages
    return (
        amount_paise >= params.min_high_value_paise
        and amount_paise
        >= params.high_value_min_multiple_of_median * baseline.median_outbound_paise
    )


def canonical_sequence(stages: Iterable[StageEvent]) -> list[Stage]:
    """Distinct stages appearing in canonical order S1→S2→S3→S4, by first occurrence (gaps ok).

    This is the longest increasing subsequence of canonical positions, ordered by time.
    """
    first_seen: dict[Stage, StageEvent] = {}
    for event in stages:
        current = first_seen.get(event.stage)
        if current is None or event.occurred_at < current.occurred_at:
            first_seen[event.stage] = event
    by_time = sorted(first_seen.values(), key=lambda e: (e.occurred_at, STAGE_ORDER.index(e.stage)))
    positions = [STAGE_ORDER.index(e.stage) for e in by_time]
    best: list[list[int]] = []
    for i, pos in enumerate(positions):
        prefix = max((best[j] for j in range(i) if positions[j] < pos), key=len, default=[])
        best.append([*prefix, pos])
    longest = max(best, key=len, default=[])
    return [STAGE_ORDER[pos] for pos in longest]


def canonical_order_count(stages: Iterable[StageEvent]) -> int:
    return len(canonical_sequence(stages))


def distinct_stages(stages: Iterable[StageEvent]) -> set[Stage]:
    return {s.stage for s in stages}
