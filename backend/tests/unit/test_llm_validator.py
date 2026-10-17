"""T-031: the deterministic validator rejects fabricated facts (AI_DESIGN §12.5)."""

from app.integrations.llm.base import Draft, Fact
from app.integrations.llm.validator import validate

FACTS = [
    Fact("F1", "[CUSTOMER] requested a RTGS transfer of ₹46,00,000."),
    Fact("F2", "The request was made on 03 Oct 2026, 11:20 IST at the branch counter."),
    Fact("F3", "Beneficiary account ending 4821 at Example Bank (IFSC EXMP0001234)."),
]
CLEAN = (
    "On 03 Oct 2026 at 11:20 IST, [CUSTOMER] requested an RTGS transfer of ₹46,00,000 to a "
    "beneficiary account ending 4821 at Example Bank. The transfer was paused."
)


def test_clean_narrative_passes() -> None:
    assert validate(Draft(CLEAN, ["F1", "F2", "F3"]), FACTS) is None


def test_fabricated_amount_is_rejected() -> None:
    bad = CLEAN.replace("₹46,00,000", "₹48,00,000")
    assert validate(Draft(bad, ["F1"]), FACTS) == "UNSUPPORTED_NUMBER"


def test_fabricated_date_is_rejected() -> None:
    bad = CLEAN.replace("03 Oct", "03 Nov")
    assert validate(Draft(bad, ["F1"]), FACTS) == "UNSUPPORTED_DATE"


def test_accusatory_terms_are_rejected() -> None:
    assert validate(Draft(CLEAN + " The fraudster called.", ["F1"]), FACTS) == "DENY_LIST"


def test_unknown_fact_ids_are_rejected() -> None:
    assert validate(Draft(CLEAN, ["F9"]), FACTS) == "UNKNOWN_FACT_ID"


def test_empty_is_rejected() -> None:
    assert validate(Draft("  ", []), FACTS) == "EMPTY"
