"""T-026: stage detection (AI_DESIGN §5.1) and canonical order (§5.3)."""

from datetime import date, timedelta

from app.domain.enums import EventType, Stage
from app.domain.models import EventFacts
from app.domain.stages import (
    canonical_order_count,
    canonical_sequence,
    detect_stage,
    is_high_value,
    pooled_amount,
)
from tests.factories import (
    HERO_FD,
    HERO_PAYEE,
    HERO_POOL_1,
    HERO_POOL_2,
    baseline,
    cfg,
    ist,
    rupees,
    stage,
)


def test_premature_fd_closure_is_s1() -> None:
    assert detect_stage(HERO_FD, baseline(), [], cfg()) is Stage.S1_LIQUIDATION


def test_fd_closed_at_maturity_is_not_s1() -> None:
    matured = HERO_FD.model_copy(update={"maturity_date": date(2026, 10, 1)})
    assert detect_stage(matured, baseline(), [], cfg()) is None


def test_payee_added_is_s3() -> None:
    assert detect_stage(HERO_PAYEE, baseline(), [], cfg()) is Stage.S3_NEW_PAYEE


def test_routine_events_are_not_stages() -> None:
    debit = EventFacts(event_id="E1", event_type=EventType.ROUTINE_DEBIT, occurred_at=ist(1, 9))
    assert detect_stage(debit, baseline(), [], cfg()) is None


def test_pooling_counts_fd_proceeds_into_same_account() -> None:
    assert detect_stage(HERO_POOL_1, baseline(), [HERO_FD], cfg()) is Stage.S2_POOLING


def test_single_inbound_transfer_is_not_pooling() -> None:
    assert detect_stage(HERO_POOL_1, baseline(), [], cfg()) is None


def test_pooling_needs_both_thresholds() -> None:
    small = [
        HERO_POOL_1.model_copy(update={"amount_paise": rupees(40_000)}),
        HERO_POOL_2.model_copy(update={"amount_paise": rupees(40_000)}),
    ]
    # ₹80,000 is below the ₹1,00,000 floor.
    assert detect_stage(small[1], baseline(10_000), small[:1], cfg()) is None
    # ₹11 L is above ₹1 L but below 5× a ₹5 L median (₹25 L).
    assert detect_stage(HERO_POOL_2, baseline(5_00_000), [HERO_POOL_1], cfg()) is None
    assert detect_stage(HERO_POOL_2, baseline(40_000), [HERO_POOL_1], cfg()) is Stage.S2_POOLING


def test_pooling_window_is_72_hours() -> None:
    old = HERO_POOL_1.model_copy(
        update={"occurred_at": HERO_POOL_2.occurred_at - timedelta(hours=73)}
    )
    assert detect_stage(HERO_POOL_2, baseline(), [old], cfg()) is None


def test_pooling_into_different_accounts_does_not_combine() -> None:
    other = HERO_POOL_1.model_copy(update={"to_account": "XXXXXX9999"})
    assert detect_stage(HERO_POOL_2, baseline(), [other], cfg()) is None


def test_pooled_amount_excludes_fd_proceeds() -> None:
    assert pooled_amount(HERO_POOL_2, [HERO_FD, HERO_POOL_1], cfg()) == rupees(11_00_000)


def test_high_value_needs_both_floor_and_multiple() -> None:
    assert is_high_value(rupees(46_00_000), baseline(40_000), cfg())
    assert not is_high_value(rupees(1_99_999), baseline(1_000), cfg())  # below ₹2 L
    assert not is_high_value(rupees(40_00_000), baseline(5_00_000), cfg())  # 8×


def test_canonical_order_allows_gaps() -> None:
    stages = [stage(Stage.S1_LIQUIDATION, ist(1, 9)), stage(Stage.S3_NEW_PAYEE, ist(2, 9))]
    assert canonical_order_count(stages) == 2


def test_out_of_order_stages_count_longest_ordered_run() -> None:
    stages = [
        stage(Stage.S3_NEW_PAYEE, ist(1, 9)),
        stage(Stage.S1_LIQUIDATION, ist(2, 9)),
        stage(Stage.S2_POOLING, ist(3, 9)),
    ]
    assert canonical_sequence(stages) == [Stage.S1_LIQUIDATION, Stage.S2_POOLING]


def test_repeated_stage_uses_first_occurrence() -> None:
    stages = [
        stage(Stage.S2_POOLING, ist(1, 9)),
        stage(Stage.S1_LIQUIDATION, ist(2, 9)),
        stage(Stage.S2_POOLING, ist(3, 9)),
    ]
    assert canonical_order_count(stages) == 1


def test_empty_sequence() -> None:
    assert canonical_order_count([]) == 0
