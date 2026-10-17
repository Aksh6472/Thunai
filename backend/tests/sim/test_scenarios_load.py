"""T-023: every family loads, validates and matches AI_DESIGN §7.1."""

import pytest

from sim.scenarios.schema import TransferStep, load_all

FAMILIES = {f"P{i}" for i in range(1, 8)} | {f"N{i}" for i in range(1, 7)}


def test_all_thirteen_families_load() -> None:
    scenarios = load_all()
    assert set(scenarios) == FAMILIES
    assert {s.id for s in scenarios.values() if s.held_out} == {"P6", "N5"}


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_family_is_consistent(family: str) -> None:
    s = load_all()[family]
    assert s.label == ("coercion" if family.startswith("P") else "genuine")
    assert s.grounding and "(fictional)" in s.customer.display_name
    transfers = [step for step in s.steps if isinstance(step, TransferStep)]
    if s.label == "coercion":
        assert any(t.target for t in transfers)
    else:
        assert not any(t.target for t in transfers)


def test_hero_and_n1_customers_match_the_demo_script() -> None:
    scenarios = load_all()
    assert scenarios["P1"].customer.ref == "CUST-0007"
    assert scenarios["P1"].customer.language == "ta"
    assert scenarios["N1"].customer.ref == "CUST-0012"
    hero_transfer = [s for s in scenarios["P1"].steps if isinstance(s, TransferStep)][0]
    assert (hero_transfer.amount_rupees, hero_transfer.rail, hero_transfer.channel) == (
        4600000,
        "RTGS",
        "BRANCH",
    )
