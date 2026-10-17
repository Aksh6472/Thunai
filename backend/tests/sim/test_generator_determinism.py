"""T-022: the same seed gives identical data; seeding is fast (AC: ≤ 10 s)."""

import hashlib
import json
import time

from sim.generator import generate
from sim.plan import plan_scenario
from sim.scenarios.schema import load_all


def _canonical(seed: int) -> str:
    population = generate(seed, load_all())
    dump = [
        {
            "spec": g.spec.model_dump(mode="json"),
            "history": [
                (h.at.isoformat(), h.kind, h.amount_paise, h.account, h.payee_ref)
                for h in g.history
            ],
        }
        for g in population
    ]
    return hashlib.sha256(json.dumps(dump, sort_keys=True).encode()).hexdigest()


def test_seed_42_is_identical_twice() -> None:
    assert _canonical(42) == _canonical(42)


def test_different_seeds_differ() -> None:
    assert _canonical(42) != _canonical(117)


def test_population_has_fifty_fictional_customers() -> None:
    population = generate(42, load_all())
    assert len(population) == 50
    assert len({g.spec.ref for g in population}) == 50
    assert all("(fictional)" in g.spec.display_name for g in population)


def test_generation_is_fast() -> None:
    started = time.perf_counter()
    generate(42, load_all())
    assert time.perf_counter() - started < 2


def test_seed_42_plan_is_exact_and_other_seeds_randomise() -> None:
    p1 = load_all()["P1"]
    golden = plan_scenario(p1, 42)
    assert golden[-1].body["amount_paise"] == 460000000
    assert golden[-1].body["transfer_ref"] == "TRF-P1-0001"
    other = plan_scenario(p1, 150)
    assert other[-1].body["transfer_ref"] == "TRF-P1-0001-S150"
    assert plan_scenario(p1, 150)[-1].body == other[-1].body  # deterministic per seed
