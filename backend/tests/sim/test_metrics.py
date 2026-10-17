"""T-030: metrics on small hand-computed cases."""

import pytest

from sim.metrics import (
    Record,
    amount_protected,
    explanation_coverage,
    false_hold,
    genuine_warning,
    interception,
    modelled_delay_minutes,
    per_family,
    tier_confusion,
    wilson,
)

L = 20_000_000  # ₹2 L


def rec(
    family: str,
    decision: str,
    *,
    label: str = "genuine",
    amount: int = L,
    target: bool = False,
    first: bool = False,
    tier: str = "LOW",
    hold_status: str | None = None,
) -> Record:
    reasons = [{"code": "X", "points": 30}] if decision != "ALLOW" else []
    return Record(
        seed=1,
        family=family,
        label=label,
        target=target,
        amount_paise=amount,
        decision=decision,
        tier=tier,
        hold_status=hold_status,
        reasons=reasons,
        raw_score=30 if reasons else 0,
        first_target=first,
    )


def test_wilson_matches_reference_values() -> None:
    low, high = wilson(9, 10)
    assert (round(low, 4), round(high, 4)) == (0.5958, 0.9821)
    assert wilson(0, 0) == (0.0, 0.0)
    low, high = wilson(0, 20)
    assert low == 0.0 and round(high, 4) == 0.1611


def test_interception_counts_first_target_only() -> None:
    records = [
        rec("P1", "HOLD", label="coercion", target=True, first=True),
        rec("P2", "WARN", label="coercion", target=True, first=True),
        rec("P2", "HOLD", label="coercion", target=True),  # a later transfer: not counted
    ]
    rate = interception(records)
    assert (rate.k, rate.n) == (1, 2)


def test_amount_protection() -> None:
    records = [
        rec("P1", "HOLD", label="coercion", target=True, first=True, amount=3 * L),
        rec("P2", "ALLOW", label="coercion", target=True, first=True, amount=L),
    ]
    assert amount_protected(records) == {
        "held_paise": 3 * L,
        "attempted_paise": 4 * L,
        "share": 0.75,
    }


def test_false_hold_and_warning_use_high_value_genuine_only() -> None:
    records = [
        rec("N4", "HOLD"),
        rec("N3", "WARN"),
        rec("N1", "ALLOW"),
        rec("BG", "HOLD", amount=L - 1),  # below ₹2 L: excluded
    ]
    assert (false_hold(records).k, false_hold(records).n) == (1, 3)
    assert (genuine_warning(records).k, genuine_warning(records).n) == (1, 3)


def test_explanation_coverage() -> None:
    good = rec("P1", "HOLD", label="coercion", first=True, target=True)
    bad = Record(**{**good.__dict__, "reasons": [], "raw_score": 0})
    rate = explanation_coverage([good, bad])
    assert (rate.k, rate.n) == (1, 2)


def test_per_family_and_confusion() -> None:
    records = [
        rec("P1", "HOLD", label="coercion", target=True, first=True, tier="VERY_HIGH"),
        rec("N4", "HOLD", tier="HIGH"),
        rec("N4", "ALLOW"),
    ]
    rows = {r["family"]: r for r in per_family(records)}
    assert rows["P1"]["interception"]["rate"] == 1.0
    assert rows["N4"]["false_hold"]["k"] == 1 and rows["N4"]["n"] == 2
    table = tier_confusion(records)
    assert table["coercion"]["VERY_HIGH"] == 1 and table["genuine"]["LOW"] == 1


def test_modelled_delay_is_deterministic_and_documented() -> None:
    records = [rec("N4", "HOLD", hold_status="AWAITING_CONTACT") for _ in range(200)]
    a, b = modelled_delay_minutes(records, seed=3), modelled_delay_minutes(records, seed=3)
    assert a == b
    assert 5 < a["median"] < 15  # median ≈ 8 min (with 15% at 240 min)
    officer_only = modelled_delay_minutes([rec("N5", "HOLD", hold_status="AWAITING_OFFICER")])
    assert officer_only["median"] == pytest.approx(240.0)
