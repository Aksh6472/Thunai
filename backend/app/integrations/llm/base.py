"""Report narrative drafters (FR-21, AI_DESIGN §12). The LLM is never on the decision path."""

from dataclasses import dataclass
from typing import Protocol


class NarrativeUnavailable(Exception):
    """The drafter failed; `reason` is a short code for the X-Thunai-LLM-Fallback header."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Fact:
    id: str
    text: str


@dataclass(frozen=True)
class Draft:
    narrative: str
    facts_used: list[str]


class NarrativeDrafter(Protocol):
    def draft(self, facts: list[Fact]) -> Draft:
        """Raises NarrativeUnavailable on any failure."""
        ...
