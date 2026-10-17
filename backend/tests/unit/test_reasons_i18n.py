"""T-028: every reason code has EN and TA text; Indian number formatting (TESTING.md §2)."""

import pytest

from app.domain.i18n.reason_texts import RENDERERS, render
from app.domain.money import format_inr, group_indian

ALL_CODES = {
    "FD_PREMATURE_CLOSURE",
    "FUNDS_POOLED",
    "NEW_PAYEE",
    "HIGH_VALUE_TO_PAYEE",
    "BALANCE_DRAIN",
    "STAGE_SEQUENCE",
    "FRI_RISK",
    "FRI_UNAVAILABLE",
    "LONG_CALL_UNKNOWN",
    "TELLER_ON_CALL",
    "TELLER_DISTRESSED",
    "TELLER_FOLLOWING_INSTRUCTIONS",
    "TELLER_MENTIONS_AUTHORITY",
    "TRUSTED_CONTACT_RECENTLY_CHANGED",
    "ESTABLISHED_PAYEE",
    "MATCHES_REGULAR_PATTERN",
    "BASELINE_LOW_CONFIDENCE",
}

SAMPLE_EVIDENCE = {
    "amount_paise": 460000000,
    "median_outbound_paise": 4000000,
    "multiple_of_median": 115,
    "percent_of_balance": 98,
    "payee_age_minutes": 128,
    "stages": ["S1_LIQUIDATION", "S2_POOLING"],
    "count": 2,
    "rating": "HIGH",
    "duration_min": 190,
    "call_type": "VIDEO",
    "changed_hours_ago": 5,
    "payee_age_days": 730,
    "prior_successful_transfers": 8,
    "recurring_amount_paise": 50000000,
    "history_days": 12,
    "qualifying_transfer_count": 2,
}


def test_every_reason_code_has_a_renderer() -> None:
    assert set(RENDERERS) == ALL_CODES


@pytest.mark.parametrize("code", sorted(ALL_CODES))
def test_every_code_renders_english_and_tamil(code: str) -> None:
    text_en, text_ta = render(code, SAMPLE_EVIDENCE)
    assert text_en and text_ta
    assert any("஀" <= ch <= "௿" for ch in text_ta), "Tamil text has no Tamil script"


@pytest.mark.parametrize("code", sorted(ALL_CODES))
def test_no_accusatory_words(code: str) -> None:
    text_en, _ = render(code, SAMPLE_EVIDENCE)
    for word in ("fraud", "victim", "suspect", "blocked", "frozen", "criminal"):
        assert word not in text_en.lower()


def test_indian_grouping() -> None:
    assert format_inr(460000000) == "₹46,00,000"
    assert format_inr(4000000) == "₹40,000"
    assert format_inr(12345678900) == "₹12,34,56,789"
    assert format_inr(0) == "₹0"
    assert group_indian(999) == "999"
    assert group_indian(1000) == "1,000"
    assert group_indian(100000) == "1,00,000"


@pytest.mark.parametrize(
    ("hours", "phrase"), [(0, "less than an hour"), (1, "1 hour before"), (2, "2 hours before")]
)
def test_payee_age_is_grammatical(hours: int, phrase: str) -> None:
    text_en, _ = render("NEW_PAYEE", {"payee_age_minutes": hours * 60})
    assert phrase in text_en
