"""T-028 invariants over 1,000 seeded random inputs (TESTING.md §2, NFR-02/03)."""

import random
from datetime import timedelta

from app.domain.enums import (
    BaselineConfidence,
    CallType,
    Channel,
    Decision,
    FriRating,
    Rail,
    Stage,
    TellerItem,
)
from app.domain.models import (
    AssessmentInput,
    CallSignal,
    PayeeFacts,
    Signals,
    StageEvent,
    TransferFacts,
)
from app.domain.policy import TIER_DECISION
from app.domain.scoring import assess
from tests.factories import baseline, cfg, ist


def _random_input(rng: random.Random) -> AssessmentInput:
    now = ist(10, 12)
    stages = tuple(
        StageEvent(
            stage=rng.choice(list(Stage)[:3]),
            event_id=f"E{i}",
            occurred_at=now - timedelta(hours=rng.randint(1, 150)),
            amount_paise=rng.randint(1, 10**9),
        )
        for i in range(rng.randint(0, 5))
    )
    median = rng.randint(100, 10**7)
    call = None
    if rng.random() < 0.5:
        call = CallSignal(
            call_type=rng.choice(list(CallType)),
            caller_known=rng.random() < 0.3,
            duration_min=rng.randint(0, 600),
            observed_at=now - timedelta(minutes=rng.randint(0, 90)),
        )
    return AssessmentInput(
        customer_id="c",
        now=now,
        baseline=baseline(
            median // 100 + 1,
            premature=rng.randint(0, 3),
            confidence=rng.choice(list(BaselineConfidence)),
        ),
        episode_stages=stages,
        transfer=TransferFacts(
            transfer_ref="T",
            amount_paise=rng.randint(1, 10**10),
            rail=rng.choice(list(Rail)),
            channel=rng.choice(list(Channel)),
            initiated_at=now,
            source_account_balance_paise=rng.randint(0, 10**10),
            payee=PayeeFacts(
                payee_id="p",
                payee_ref="P",
                added_at=now - timedelta(minutes=rng.randint(0, 10**6)),
                prior_successful_transfers=rng.randint(0, 10),
                recurring_amount_paise=rng.choice([None, rng.randint(1, 10**9)]),
            ),
        ),
        signals=Signals(
            fri_rating=rng.choice([None, *FriRating]),
            call=call,
            teller_items=tuple(rng.sample(list(TellerItem), rng.randint(0, 4))),
            trusted_contact_changed_at=rng.choice([None, now - timedelta(days=rng.randint(0, 30))]),
        ),
        has_active_trusted_contact=rng.random() < 0.7,
    )


def test_invariants_hold_for_random_inputs() -> None:
    rng = random.Random(20261017)
    config = cfg()
    for _ in range(1000):
        result = assess(_random_input(rng), config)
        assert sum(r.points for r in result.reasons) == result.raw_score
        assert 0 <= result.score <= 100
        assert result.score == max(0, min(100, result.raw_score))
        expected_tier = config.tiers.tier_for(result.score)
        if "FRI_VERY_HIGH_FLOOR" not in result.overrides_applied:
            assert result.tier is expected_tier
        if "BELOW_FLOOR_NO_HOLD" not in result.overrides_applied:
            assert result.decision is TIER_DECISION[result.tier]
        if result.decision is not Decision.ALLOW:
            assert any(r.points for r in result.reasons)
        for reason in result.reasons:
            assert reason.text_en and reason.text_ta


def test_assessment_is_deterministic() -> None:
    """NFR-03: the same input gives the identical assessment."""
    rng_a, rng_b = random.Random(7), random.Random(7)
    for _ in range(50):
        assert assess(_random_input(rng_a), cfg()) == assess(_random_input(rng_b), cfg())


def test_input_snapshot_round_trips() -> None:
    """NFR-09: the stored input reproduces the identical result."""
    rng = random.Random(99)
    for _ in range(50):
        inp = _random_input(rng)
        restored = AssessmentInput.model_validate(inp.model_dump(mode="json"))
        assert assess(restored, cfg()) == assess(inp, cfg())
