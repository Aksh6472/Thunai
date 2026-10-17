"""Twilio SMS via httpx (FR-22). 5 s timeout; the caller falls back to console on failure."""

import logging

import httpx

from app.domain.enums import DeliveryChannel
from app.integrations.notifier.base import DeliveryResult, Recipient

logger = logging.getLogger(__name__)
TWILIO_API = "https://api.twilio.com/2010-04-01"


class TwilioNotifier:
    channel = DeliveryChannel.SMS

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._sid = account_sid
        self._token = auth_token
        self._from = from_number
        self._client = client or httpx.Client(timeout=5.0)

    def send(self, to: Recipient, text: str) -> DeliveryResult:
        if not to.phone_e164:
            return DeliveryResult(ok=False, channel=self.channel, error_code="NO_PHONE")
        try:
            response = self._client.post(
                f"{TWILIO_API}/Accounts/{self._sid}/Messages.json",
                data={"To": to.phone_e164, "From": self._from, "Body": text},
                auth=(self._sid, self._token),
                timeout=5.0,
            )
        except httpx.TimeoutException:
            return DeliveryResult(ok=False, channel=self.channel, error_code="TIMEOUT")
        except httpx.HTTPError:
            return DeliveryResult(ok=False, channel=self.channel, error_code="NETWORK_ERROR")
        if response.status_code >= 300:
            code = _twilio_code(response)
            logger.warning(
                "contact.sms_failed", extra={"status": response.status_code, "code": code}
            )
            return DeliveryResult(ok=False, channel=self.channel, error_code=code)
        return DeliveryResult(ok=True, channel=self.channel)


def _twilio_code(response: httpx.Response) -> str:
    try:
        return f"TWILIO_{response.json().get('code', response.status_code)}"
    except ValueError:
        return f"HTTP_{response.status_code}"
