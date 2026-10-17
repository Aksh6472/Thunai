"""T-016: notifiers. Real channels are exercised only through httpx.MockTransport."""

import httpx
import pytest

from app.domain.enums import DeliveryChannel
from app.integrations.notifier.base import Recipient
from app.integrations.notifier.console import ConsoleNotifier
from app.integrations.notifier.telegram import TelegramNotifier
from app.integrations.notifier.twilio import TwilioNotifier

TO = Recipient(phone_e164="+919800000101", telegram_chat_id="12345", display_name="Arun")


def _client(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def test_console_keeps_last_50_newest_first() -> None:
    console = ConsoleNotifier()
    for i in range(55):
        console.send(TO, f"msg {i}", link=f"http://x/t/{i}")
    messages = console.messages(50)
    assert len(messages) == 50
    assert messages[0].text == "msg 54"
    assert messages[0].to == "…0101"


def test_twilio_success() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.content.decode()
        return httpx.Response(201, json={"sid": "SM1"})

    result = TwilioNotifier("AC1", "tok", "+15550001", _client(httpx.MockTransport(handler))).send(
        TO, "hi"
    )
    assert result.ok and result.channel is DeliveryChannel.SMS
    assert "Accounts/AC1/Messages.json" in str(seen["url"])
    assert "To=%2B919800000101" in str(seen["body"])


def test_twilio_4xx_reports_provider_code() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": 21608, "message": "unverified"})

    result = TwilioNotifier("AC1", "tok", "+15550001", _client(httpx.MockTransport(handler))).send(
        TO, "hi"
    )
    assert (result.ok, result.error_code) == (False, "TWILIO_21608")


@pytest.mark.parametrize("notifier_cls", ["twilio", "telegram"])
def test_timeouts_are_reported_not_raised(notifier_cls: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    client = _client(httpx.MockTransport(handler))
    notifier = (
        TwilioNotifier("AC1", "tok", "+15550001", client)
        if notifier_cls == "twilio"
        else TelegramNotifier("bot", client)
    )
    result = notifier.send(TO, "hi")
    assert (result.ok, result.error_code) == (False, "TIMEOUT")


def test_telegram_success_and_4xx() -> None:
    ok = TelegramNotifier(
        "bot", _client(httpx.MockTransport(lambda _: httpx.Response(200, json={"ok": True})))
    ).send(TO, "hi")
    assert ok.ok and ok.channel is DeliveryChannel.TELEGRAM
    bad = TelegramNotifier(
        "bot", _client(httpx.MockTransport(lambda _: httpx.Response(403, json={"ok": False})))
    ).send(TO, "hi")
    assert (bad.ok, bad.error_code) == (False, "TELEGRAM_403")


def test_missing_recipient_details() -> None:
    nobody = Recipient()
    assert TelegramNotifier("bot").send(nobody, "x").error_code == "NO_CHAT_ID"
    assert TwilioNotifier("a", "b", "c").send(nobody, "x").error_code == "NO_PHONE"
