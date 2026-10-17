"""T-007: clocks. SimClock maths uses a fixed wall clock so tests are deterministic."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import FixedClock, RealClock, SimClock

T0 = datetime(2026, 10, 1, 4, 30, tzinfo=UTC)
WALL = datetime(2026, 10, 17, 10, 0, tzinfo=UTC)


def test_real_clock_is_timezone_aware() -> None:
    assert RealClock().now().tzinfo is not None


def test_fixed_clock_moves_only_when_told() -> None:
    clock = FixedClock(T0)
    assert clock.now() == T0
    clock.advance(timedelta(hours=2))
    assert clock.now() == T0 + timedelta(hours=2)


@pytest.fixture
def sim(db: Session) -> tuple[SimClock, FixedClock]:
    wall = FixedClock(WALL)
    factory = sessionmaker(bind=db.get_bind(), join_transaction_mode="create_savepoint")
    return SimClock(factory, wall=wall), wall


def test_sim_clock_advances_at_speed(sim: tuple[SimClock, FixedClock]) -> None:
    clock, wall = sim
    clock.set(T0, speed=4320, running_scenario="P1")
    wall.advance(timedelta(seconds=20))
    assert clock.now() == T0 + timedelta(seconds=20 * 4320)  # 24 simulated hours


def test_sim_clock_frozen_at_speed_zero(sim: tuple[SimClock, FixedClock]) -> None:
    clock, wall = sim
    clock.set(T0, speed=0)
    wall.advance(timedelta(hours=5))
    assert clock.now() == T0


def test_sim_clock_state_is_persisted(sim: tuple[SimClock, FixedClock], db: Session) -> None:
    clock, wall = sim
    clock.set(T0, speed=60, running_scenario="N1")
    reloaded = SimClock(
        sessionmaker(bind=db.get_bind(), join_transaction_mode="create_savepoint"), wall=wall
    )
    state = reloaded.state()
    assert (state.sim_now, state.speed, state.running_scenario) == (T0, 60, "N1")


def test_sim_clock_rejects_naive_time(sim: tuple[SimClock, FixedClock]) -> None:
    clock, _ = sim
    with pytest.raises(ValueError, match="timezone-aware"):
        clock.set(datetime(2026, 10, 1, 10, 0))  # noqa: DTZ001
