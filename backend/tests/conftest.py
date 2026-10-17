from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from app.core.settings import Settings, load_settings
from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings for tests: THUNAI_ENV=test (rate limits off) against the thunai_test DB."""
    base = load_settings()
    return load_settings(
        env="test",
        demo_mode=True,
        database_url=base.test_database_url or base.database_url,
        notifier="console",
        llm_enabled=False,
    )


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    return create_app(test_settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """In-process HTTP client (TESTING.md §1): real routing, no network."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
