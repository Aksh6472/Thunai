"""Shared FastAPI dependencies. Auth dependencies are added in T-010."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.settings import Settings


def get_db(request: Request) -> Iterator[Session]:
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings
