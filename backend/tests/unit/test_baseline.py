"""T-025: baseline statistics (AI_DESIGN §4)."""

import random
from datetime import date, timedelta

import numpy as np
import pytest

from app.domain.baseline import compute_baseline, percentile_linear
from app.domain.enums import BaselineConfidence
from app.domain.models import FdClosure, OutboundDebit
from tests.factories import cfg, ist, rupees

NOW = ist(1, 12)


def _debits(amounts: list[int], *, days_ago: int = 10) -> list[OutboundDebit]:
    return [
        OutboundDebit(amount_paise=a, occurred_at=NOW - timedelta(days=days_ago, minutes=i))
        for i, a in enumerate(amounts)
    ]


@pytest.mark.parametrize("seed", range(20))
def test_median_and_p95_match_numpy(seed: int) -> None:
    rng = random.Random(seed)
    amounts = [rng.randint(rupees(1_000), rupees(10_00_000)) for _ in range(rng.randint(5, 60))]
    result = compute_baseline(_debits(amounts), [], NOW - timedelta(days=200), NOW, cfg())
    assert abs(result.median_outbound_paise - float(np.median(amounts))) <= 0.5
    assert abs(result.p95_outbound_paise - float(np.percentile(amounts, 95))) <= 0.5


def test_percentile_linear_matches_numpy_on_small_lists() -> None:
    for values in ([5], [1, 2], [1, 2, 3, 4], [10, 20, 30, 40, 50]):
        assert percentile_linear(sorted(values), 0.95) == pytest.approx(np.percentile(values, 95))


def test_fewer_than_five_transfers_uses_population_default_and_low() -> None:
    result = compute_baseline(
        _debits([rupees(90_000)] * 4), [], NOW - timedelta(days=200), NOW, cfg()
    )
    assert result.median_outbound_paise == rupees(25_000)
    assert result.confidence is BaselineConfidence.LOW


def test_short_history_is_low_confidence() -> None:
    result = compute_baseline(
        _debits([rupees(5_000)] * 10), [], NOW - timedelta(days=29), NOW, cfg()
    )
    assert result.history_days == 29
    assert result.confidence is BaselineConfidence.LOW


def test_ok_confidence() -> None:
    result = compute_baseline(
        _debits([rupees(5_000)] * 10), [], NOW - timedelta(days=30), NOW, cfg()
    )
    assert result.confidence is BaselineConfidence.OK


def test_own_account_small_and_old_debits_are_excluded() -> None:
    debits = [
        *_debits([rupees(10_000)] * 5),
        OutboundDebit(
            amount_paise=rupees(9_00_000), occurred_at=NOW - timedelta(days=1), to_own_account=True
        ),
        OutboundDebit(amount_paise=rupees(999), occurred_at=NOW - timedelta(days=1)),
        OutboundDebit(amount_paise=rupees(9_00_000), occurred_at=NOW - timedelta(days=181)),
    ]
    result = compute_baseline(debits, [], NOW - timedelta(days=300), NOW, cfg())
    assert result.qualifying_transfer_count == 5
    assert result.median_outbound_paise == rupees(10_000)


def test_premature_fd_closures_in_last_365_days() -> None:
    closures = [
        FdClosure(closed_at=NOW - timedelta(days=10), maturity_date=date(2027, 1, 1)),
        FdClosure(closed_at=NOW - timedelta(days=100), maturity_date=date(2026, 12, 1)),
        FdClosure(
            closed_at=NOW - timedelta(days=50), maturity_date=(NOW - timedelta(days=50)).date()
        ),
        FdClosure(closed_at=NOW - timedelta(days=400), maturity_date=date(2027, 1, 1)),
    ]
    result = compute_baseline([], closures, None, NOW, cfg())
    assert result.premature_fd_closures_365d == 2
    assert result.history_days == 0
