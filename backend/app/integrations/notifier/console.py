"""Console notifier: always available, no network (NFR-04). Keeps the last 50 messages in memory.

The buffer feeds GET /demo/console-messages (and its QR code). Logs never contain the link token.
"""

import logging
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime

from app.core.clock import wall_now
from app.domain.enums import DeliveryChannel
from app.integrations.notifier.base import DeliveryResult, Recipient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConsoleMessage:
    at: datetime
    to: str
    text: str
    link: str | None


class ConsoleNotifier:
    channel = DeliveryChannel.CONSOLE

    def __init__(self, capacity: int = 50) -> None:
        self._buffer: deque[ConsoleMessage] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def send(self, to: Recipient, text: str, link: str | None = None) -> DeliveryResult:
        masked = f"…{to.phone_e164[-4:]}" if to.phone_e164 else to.display_name or "contact"
        with self._lock:
            self._buffer.append(ConsoleMessage(at=wall_now(), to=masked, text=text, link=link))
        logger.info("contact.console_message", extra={"to": masked})
        return DeliveryResult(ok=True, channel=self.channel)

    def messages(self, limit: int = 20) -> list[ConsoleMessage]:
        with self._lock:
            return list(self._buffer)[-limit:][::-1]

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
