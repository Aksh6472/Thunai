"""Per-customer baseline (AI_DESIGN §4). Pure: inputs in, Baseline out."""

import math
import statistics
from collections.abc import Sequence
from datetime import datetime, timedelta

from app.domain.config import ScoringConfig
from app.domain.enums import BaselineConfidence
from app.domain.models import Baseline, FdClosure, OutboundDebit


def percentile_linear(sorted_values: Sequence[int], q: float) -> float:
    """Same as numpy's default ('linear') percentile, for q in [0, 1]."""
    if not sorted_values:
        raise ValueError("percentile of an empty sequence")
    position = q * (len(sorted_values) - 1)
    lo, hi = math.floor(position), math.ceil(position)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (position - lo)


def compute_baseline(
    debits: Sequence[OutboundDebit],
    fd_closures: Sequence[FdClosure],
    first_activity_at: datetime | None,
    now: datetime,
    cfg: ScoringConfig,
) -> Baseline:
    params = cfg.baseline
    since = now - timedelta(days=params.lookback_days)
    amounts = sorted(
        d.amount_paise
        for d in debits
        if not d.to_own_account
        and since <= d.occurred_at <= now
        and d.amount_paise >= params.min_qualifying_amount_paise
    )
    history_days = max(0, (now - first_activity_at).days) if first_activity_at else 0
    fd_since = now - timedelta(days=params.fd_closure_lookback_days)
    premature = sum(
        1
        for c in fd_closures
        if fd_since <= c.closed_at <= now and c.closed_at.date() < c.maturity_date
    )

    enough = len(amounts) >= params.min_qualifying_transfers
    median = round(statistics.median(amounts)) if enough else params.population_default_median_paise
    p95 = (
        round(percentile_linear(amounts, 0.95))
        if amounts
        else params.population_default_median_paise
    )
    low = history_days < params.min_history_days or not enough
    return Baseline(
        history_days=history_days,
        median_outbound_paise=max(1, median),
        p95_outbound_paise=p95,
        qualifying_transfer_count=len(amounts),
        premature_fd_closures_365d=premature,
        confidence=BaselineConfidence.LOW if low else BaselineConfidence.OK,
    )
