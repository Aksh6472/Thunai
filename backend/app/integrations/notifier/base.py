"""Notifier interface (ADR-006). Real channels fall back to the console notifier on failure."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.enums import DeliveryChannel


@dataclass(frozen=True)
class Recipient:
    phone_e164: str | None = None
    telegram_chat_id: str | None = None
    display_name: str = ""


@dataclass(frozen=True)
class DeliveryResult:
    ok: bool
    channel: DeliveryChannel
    error_code: str | None = None


class Notifier(Protocol):
    channel: DeliveryChannel

    def send(self, to: Recipient, text: str) -> DeliveryResult: ...
