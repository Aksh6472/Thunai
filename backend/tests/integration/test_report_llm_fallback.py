"""T-031: LLM narrative is validated, re-identified locally, and falls back to the template."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import Role
from app.integrations.llm.base import Draft, Fact, NarrativeUnavailable
from tests.scenario_helpers import hero_hold, staff_headers

pytestmark = pytest.mark.anyio


class FakeDrafter:
    def __init__(self, narrative: str | None = None, error: str | None = None) -> None:
        self.narrative, self.error = narrative, error
        self.seen: list[Fact] = []

    def draft(self, facts: list[Fact]) -> Draft:
        self.seen = facts
        if self.error:
            raise NarrativeUnavailable(self.error)
        return Draft(self.narrative or "", ["F1"])


@pytest.fixture
def llm_app(app: FastAPI, test_settings: Settings) -> FastAPI:
    app.state.settings = test_settings.model_copy(
        update={"llm_enabled": True, "anthropic_api_key": "test"}
    )
    return app


async def _create(
    client: httpx.AsyncClient, db: Session, settings: Settings, headers: dict[str, str]
) -> httpx.Response:
    hold = await hero_hold(client, db, settings, headers)
    teller = staff_headers(db, settings, "teller.llm", Role.TELLER)
    return await client.post(
        f"/api/v1/holds/{hold['hold_id']}/report", json={"use_llm": True}, headers=teller
    )


async def test_valid_llm_narrative_is_used_and_reidentified(
    llm_app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    fake = FakeDrafter("[CUSTOMER] requested a transfer of ₹46,00,000, which was paused.")
    llm_app.state.narrative_drafter = fake
    r = await _create(client, db, test_settings, service_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["narrative_source"] == "LLM"
    assert body["narrative_text"].startswith("R. Kamala (fictional) requested")
    assert "x-thunai-llm-fallback" not in r.headers
    sent = " ".join(f.text for f in fake.seen)
    assert "Kamala" not in sent and "XXXXXX" not in sent  # pseudonymised input


async def test_fabricated_amount_falls_back_to_template(
    llm_app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    llm_app.state.narrative_drafter = FakeDrafter("[CUSTOMER] sent ₹99,00,000.")
    r = await _create(client, db, test_settings, service_headers)
    assert r.json()["narrative_source"] == "TEMPLATE"
    assert r.headers["x-thunai-llm-fallback"] == "LLM_VALIDATION_FAILED_UNSUPPORTED_NUMBER"


async def test_llm_error_falls_back_to_template(
    llm_app: FastAPI,
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
) -> None:
    llm_app.state.narrative_drafter = FakeDrafter(error="LLM_TIMEOUT")
    r = await _create(client, db, test_settings, service_headers)
    assert r.json()["narrative_source"] == "TEMPLATE"
    assert r.headers["x-thunai-llm-fallback"] == "LLM_TIMEOUT"
