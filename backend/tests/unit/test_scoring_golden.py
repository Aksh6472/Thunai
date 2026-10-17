"""T-028 golden tests: AI_DESIGN §6.4 worked examples, exactly."""

from app.domain.enums import Decision, HoldStatus, Tier
from app.domain.scoring import assess
from tests.factories import cfg, hero_input, n1_input, n4_input


def _points(assessment: object) -> dict[str, int]:
    return {r.code: r.points for r in assessment.reasons}  # type: ignore[attr-defined]


def test_hero_p1_is_115_very_high_hold() -> None:
    result = assess(hero_input(), cfg())
    assert _points(result) == {
        "FD_PREMATURE_CLOSURE": 15,
        "FUNDS_POOLED": 10,
        "NEW_PAYEE": 20,
        "HIGH_VALUE_TO_PAYEE": 20,
        "BALANCE_DRAIN": 5,
        "STAGE_SEQUENCE": 10,
        "LONG_CALL_UNKNOWN": 15,
        "FRI_RISK": 20,
    }
    assert (result.raw_score, result.score) == (115, 100)
    assert result.tier is Tier.VERY_HIGH
    assert result.decision is Decision.HOLD
    assert result.initial_hold_status is HoldStatus.AWAITING_OFFICER
    assert result.config_version == "scoring_v1@2026-10-17"
    assert result.is_s4


def test_hero_evidence_matches_the_story() -> None:
    reasons = {r.code: r for r in assess(hero_input(), cfg()).reasons}
    high_value = reasons["HIGH_VALUE_TO_PAYEE"]
    assert high_value.evidence["multiple_of_median"] == 115
    assert high_value.text_en == "₹46,00,000 is 115× this customer's usual transfer (₹40,000)."
    assert reasons["NEW_PAYEE"].evidence["payee_age_minutes"] == 128
    assert reasons["NEW_PAYEE"].text_en == "Payee was added 2 hours before this transfer."
    assert reasons["BALANCE_DRAIN"].evidence["percent_of_balance"] == 98
    assert reasons["FRI_RISK"].evidence["source"] == "SIMULATED"
    assert reasons["LONG_CALL_UNKNOWN"].evidence["source"] == "SIMULATED"
    assert reasons["STAGE_SEQUENCE"].evidence["stages"] == [
        "S1_LIQUIDATION",
        "S2_POOLING",
        "S3_NEW_PAYEE",
        "S4_HIGH_VALUE",
    ]


def test_hero_without_simulated_signals_is_still_very_high() -> None:
    """'Behaviour alone is enough': no FRI and no call signal gives 80."""
    result = assess(hero_input(fri=None, call=None), cfg())
    assert (result.raw_score, result.score, result.tier) == (80, 80, Tier.VERY_HIGH)
    assert result.decision is Decision.HOLD


def test_n1_property_instalment_is_allowed() -> None:
    result = assess(n1_input(), cfg())
    assert _points(result) == {
        "FD_PREMATURE_CLOSURE": 15,
        "FUNDS_POOLED": 10,
        "BALANCE_DRAIN": 5,
        "ESTABLISHED_PAYEE": -25,
    }
    assert (result.raw_score, result.score, result.tier) == (5, 5, Tier.LOW)
    assert result.decision is Decision.ALLOW
    assert not result.is_s4


def test_n4_wedding_is_an_expected_false_hold() -> None:
    result = assess(n4_input(), cfg())
    assert _points(result) == {
        "FD_PREMATURE_CLOSURE": 15,
        "FUNDS_POOLED": 10,
        "NEW_PAYEE": 15,
        "HIGH_VALUE_TO_PAYEE": 10,
        "STAGE_SEQUENCE": 10,
    }
    assert (result.raw_score, result.tier, result.decision) == (60, Tier.HIGH, Decision.HOLD)
    assert result.initial_hold_status is HoldStatus.AWAITING_CONTACT
