"""T-016: a failed real channel marks the request FAILED and the console still has the link."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import DeliveryChannel, Role
from app.integrations.notifier.base import DeliveryResult, Recipient
from tests.scenario_helpers import staff_headers, wedding_hold

pytestmark = pytest.mark.anyio


class FailingSms:
    channel = DeliveryChannel.SMS

    def send(self, to: Recipient, text: str) -> DeliveryResult:
        return DeliveryResult(ok=False, channel=self.channel, error_code="TWILIO_21608")


async def test_sms_failure_falls_back_to_console(
    app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    app.state.real_notifier = FailingSms()
    hold = await wedding_hold(client, db, test_settings, service_headers)
    assert app.state.console_notifier.messages(1)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    detail = (await client.get(f"/api/v1/holds/{hold['hold_id']}", headers=officer)).json()
    [request] = detail["contact_requests"]
    assert (request["channel"], request["delivery_status"], request["delivery_error"]) == (
        "SMS",
        "FAILED",
        "TWILIO_21608",
    )
