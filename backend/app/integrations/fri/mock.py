"""SIMULATED FRI ratings from the fri_mock_ratings table. Not real DoT data."""

import time

from sqlalchemy.orm import Session

from app.domain.enums import FriRating
from app.integrations.fri.base import FriUnavailable
from app.models import FriMockRating


class MockFriClient:
    def __init__(self, *, timeout_ms: int = 300, latency_ms: int = 0) -> None:
        self.timeout_ms = timeout_ms
        self.latency_ms = latency_ms  # artificial delay, to exercise the timeout path

    def rating(self, session: Session, msisdn_hmac: str) -> FriRating | None:
        if self.latency_ms > self.timeout_ms:
            time.sleep(self.timeout_ms / 1000)
            raise FriUnavailable("timeout")
        if self.latency_ms:
            time.sleep(self.latency_ms / 1000)
        row = session.get(FriMockRating, msisdn_hmac)
        return row.rating if row else None
