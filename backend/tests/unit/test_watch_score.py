"""T-026 acceptance: the hero's watch score climbs 15 → 40 → 63 over days 1–3 (AC-01)."""

from app.domain.enums import Tier
from app.domain.episodes import watch_score
from tests.factories import (
    HERO_CALL_DAY2,
    HERO_CALL_DAY3_MORNING,
    HERO_STAGES,
    baseline,
    cfg,
    ist,
)


def test_hero_day_1_fd_broken_is_15_low() -> None:
    score, tier, _ = watch_score(HERO_STAGES[:1], baseline(), None, None, ist(1, 10, 5), cfg())
    assert (score, tier) == (15, Tier.LOW)


def test_hero_day_2_pooled_plus_long_call_is_40_medium() -> None:
    score, tier, reasons = watch_score(
        HERO_STAGES[:3], baseline(), HERO_CALL_DAY2, None, ist(2, 18, 40), cfg()
    )
    assert (score, tier) == (40, Tier.MEDIUM)
    assert {r.code for r in reasons} == {
        "FD_PREMATURE_CLOSURE",
        "FUNDS_POOLED",
        "LONG_CALL_UNKNOWN",
    }


def test_hero_day_3_new_payee_and_sequence_is_63_high() -> None:
    score, tier, reasons = watch_score(
        HERO_STAGES, baseline(), HERO_CALL_DAY3_MORNING, None, ist(3, 9, 12), cfg()
    )
    assert (score, tier) == (63, Tier.HIGH)
    points = {r.code: r.points for r in reasons}
    assert points["NEW_PAYEE"] == 15
    assert points["STAGE_SEQUENCE"] == 8


def test_stale_call_does_not_count() -> None:
    score, _, reasons = watch_score(
        HERO_STAGES[:3], baseline(), HERO_CALL_DAY2, None, ist(3, 9, 12), cfg()
    )
    assert score == 25
    assert "LONG_CALL_UNKNOWN" not in {r.code for r in reasons}


def test_recent_contact_change_adds_ten() -> None:
    score, _, reasons = watch_score(
        HERO_STAGES[:1], baseline(), None, ist(1, 8, 0), ist(1, 10, 5), cfg()
    )
    assert score == 25
    assert "TRUSTED_CONTACT_RECENTLY_CHANGED" in {r.code for r in reasons}


def test_watch_score_excludes_transfer_reasons() -> None:
    _, _, reasons = watch_score(HERO_STAGES, baseline(), None, None, ist(3, 9, 12), cfg())
    codes = {r.code for r in reasons}
    assert not codes & {"HIGH_VALUE_TO_PAYEE", "BALANCE_DRAIN", "FRI_RISK", "ESTABLISHED_PAYEE"}
