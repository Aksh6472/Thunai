"""DoT FRI adapter interface (FR-06a). The MVP implementation is simulated (A-03, ADR-016)."""

from typing import Protocol

from sqlalchemy.orm import Session

from app.domain.enums import FriRating


class FriUnavailable(Exception):
    """The lookup failed or timed out. The engine treats this as unknown (0 points)."""


class FriClient(Protocol):
    def rating(self, session: Session, msisdn_hmac: str) -> FriRating | None:
        """The rating for a payee-linked number, None if unrated. Raises FriUnavailable."""
        ...
