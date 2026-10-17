"""Telegram Bot API sendMessage via httpx (FR-22). 5 s timeout."""

import httpx

from app.domain.enums import DeliveryChannel
from app.integrations.notifier.base import DeliveryResult, Recipient

TELEGRAM_API = "https://api.telegram.org"


class TelegramNotifier:
    channel = DeliveryChannel.TELEGRAM

    def __init__(self, bot_token: str, client: httpx.Client | None = None) -> None:
        self._token = bot_token
        self._client = client or httpx.Client(timeout=5.0)

    def send(self, to: Recipient, text: str) -> DeliveryResult:
        if not to.telegram_chat_id:
            return DeliveryResult(ok=False, channel=self.channel, error_code="NO_CHAT_ID")
        try:
            response = self._client.post(
                f"{TELEGRAM_API}/bot{self._token}/sendMessage",
                json={"chat_id": to.telegram_chat_id, "text": text},
                timeout=5.0,
            )
        except httpx.TimeoutException:
            return DeliveryResult(ok=False, channel=self.channel, error_code="TIMEOUT")
        except httpx.HTTPError:
            return DeliveryResult(ok=False, channel=self.channel, error_code="NETWORK_ERROR")
        if response.status_code >= 300:
            return DeliveryResult(
                ok=False, channel=self.channel, error_code=f"TELEGRAM_{response.status_code}"
            )
        return DeliveryResult(ok=True, channel=self.channel)
