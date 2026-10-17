"""Injectable time (ARCHITECTURE §4.7, ADR-008).

Engine logic gets "now" from a Clock. Wall clock is used only for token expiry, rate limits
and created/received timestamps.

SimClock: sim_now advances from its anchor at `speed` simulated seconds per wall second.
The replayer re-anchors it at each step (POST /demo/clock). The state lives in memory in the
single API process (uvicorn --workers 1) and is persisted to `sim_state` so it survives restarts.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.models import SimState

logger = logging.getLogger(__name__)


class Clock(Protocol):
    def now(self) -> datetime: ...


def wall_now() -> datetime:
    return datetime.now(UTC)


class RealClock:
    def now(self) -> datetime:
        return wall_now()


class FixedClock:
    """For tests: time moves only when told to."""

    def __init__(self, at: datetime) -> None:
        self._at = at

    def now(self) -> datetime:
        return self._at

    def set(self, at: datetime) -> None:
        self._at = at

    def advance(self, delta: timedelta) -> None:
        self._at += delta


@dataclass(frozen=True)
class SimClockState:
    sim_now: datetime
    speed: float
    running_scenario: str | None
    anchored_at: datetime  # wall-clock time when sim_now was set


class SimClock:
    def __init__(
        self, session_factory: sessionmaker[Session], *, wall: Clock | None = None
    ) -> None:
        self._session_factory = session_factory
        self._wall = wall or RealClock()
        self._lock = threading.Lock()
        self._state: SimClockState | None = None

    def now(self) -> datetime:
        state = self.state()
        elapsed = (self._wall.now() - state.anchored_at).total_seconds()
        return state.sim_now + timedelta(seconds=elapsed * state.speed)

    def state(self) -> SimClockState:
        with self._lock:
            if self._state is None:
                self._state = self._load()
            return self._state

    def set(
        self,
        sim_now: datetime,
        *,
        speed: float | None = None,
        running_scenario: str | None = None,
        keep_scenario: bool = False,
    ) -> SimClockState:
        if sim_now.tzinfo is None:
            raise ValueError("sim_now must be timezone-aware")
        with self._lock:
            current = self._state or self._load()
            new = SimClockState(
                sim_now=sim_now.astimezone(UTC),
                speed=current.speed if speed is None else speed,
                running_scenario=current.running_scenario if keep_scenario else running_scenario,
                anchored_at=self._wall.now(),
            )
            self._persist(new)
            self._state = new
            return new

    def reload(self) -> None:
        with self._lock:
            self._state = None

    def _load(self) -> SimClockState:
        with self._session_factory() as session:
            row = session.get(SimState, 1)
            if row is None:
                logger.warning("sim_clock.no_state_row_using_wall_clock")
                now = self._wall.now()
                return SimClockState(sim_now=now, speed=1.0, running_scenario=None, anchored_at=now)
            return SimClockState(
                sim_now=row.sim_now,
                speed=row.speed,
                running_scenario=row.running_scenario,
                anchored_at=row.updated_at,
            )

    def _persist(self, state: SimClockState) -> None:
        with self._session_factory() as session:
            row = session.get(SimState, 1)
            if row is None:
                row = SimState(id=1)
                session.add(row)
            row.sim_now = state.sim_now
            row.speed = state.speed
            row.running_scenario = state.running_scenario
            row.updated_at = state.anchored_at
            session.commit()
