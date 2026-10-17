"""Everything a service needs from the running app, passed explicitly (no globals)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import Clock
from app.core.rate_limit import RateLimiter
from app.core.settings import Settings
from app.domain.config import ScoringConfig
from app.integrations.fri.base import FriClient
from app.integrations.notifier.base import Notifier
from app.integrations.notifier.console import ConsoleNotifier


def _run_now(fn: Callable[..., Any], *args: Any) -> None:
    fn(*args)


@dataclass
class Ctx:
    settings: Settings
    cfg: ScoringConfig
    clock: Clock
    fri: FriClient
    console: ConsoleNotifier
    real_notifier: Notifier | None
    session_factory: sessionmaker[Session]
    limiter: RateLimiter
    # Runs work after the response (FastAPI BackgroundTasks); inline by default.
    schedule: Callable[..., None] = field(default=_run_now)
