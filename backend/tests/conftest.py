from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import FixedClock
from app.core.settings import BACKEND_DIR, Settings, load_settings
from app.db import make_engine
from app.main import create_app


def alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["url"] = url
    cfg.attributes["configure_logger"] = False
    return cfg


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


@pytest.fixture(scope="session")
def migrated_engine(test_settings: Settings) -> Iterator[Engine]:
    """The test DB, rebuilt from migrations once per session."""
    cfg = alembic_config(test_settings.database_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    engine = make_engine(test_settings.database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db(migrated_engine: Engine) -> Iterator[Session]:
    """A session inside an outer transaction that is rolled back after the test.

    Service code may call commit(): with create_savepoint it only releases a SAVEPOINT.
    """
    connection = migrated_engine.connect()
    outer = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
        autoflush=False,
    )
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


TEST_NOW = datetime(2026, 10, 3, 5, 50, tzinfo=UTC)  # 11:20 IST on hero day 3


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(TEST_NOW)


@pytest.fixture
def app(test_settings: Settings, clock: FixedClock, request: pytest.FixtureRequest) -> FastAPI:
    application = create_app(test_settings)
    application.state.clock = clock
    if "db" in request.fixturenames:
        # Route every request session through the test's rolled-back connection.
        session: Session = request.getfixturevalue("db")
        application.state.session_factory = sessionmaker(
            bind=session.get_bind(),
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
            autoflush=False,
        )
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """In-process HTTP client (TESTING.md §1): real routing, no network."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def service_headers(test_settings: Settings) -> dict[str, str]:
    return {"X-Thunai-Service-Key": test_settings.service_api_key}


@pytest.fixture
def committed_app(test_settings: Settings, migrated_engine: Engine) -> Iterator[FastAPI]:
    """An app on real, committed connections (concurrency, seeding). Tables are truncated after."""
    from sqlalchemy import text

    from app.models import Base

    application = create_app(test_settings)
    application.state.clock = FixedClock(TEST_NOW)
    yield application
    tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    with migrated_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def demo_app(test_settings: Settings, migrated_engine: Engine) -> Iterator[FastAPI]:
    """Demo-mode app with the real SimClock, seeded with seed 42. Truncated after."""
    from sqlalchemy import text

    from app.models import Base
    from sim.seed import seed

    application = create_app(test_settings)
    with application.state.session_factory() as session:
        seed(session, test_settings)
    application.state.clock.reload()
    yield application
    tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    with migrated_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
