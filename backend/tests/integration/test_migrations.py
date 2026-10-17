"""T-008: migrations round-trip, and the schema enforces its invariants (DATABASE_SCHEMA §3)."""

import uuid
from datetime import UTC, datetime

import pytest
from alembic import command
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import EpisodeStatus, Tier
from app.models import Base, Customer, RiskEpisode
from tests.conftest import alembic_config

NOW = datetime(2026, 10, 1, 4, 35, tzinfo=UTC)


def test_upgrade_downgrade_upgrade(migrated_engine: Engine, test_settings: Settings) -> None:
    cfg = alembic_config(test_settings.database_url)
    command.downgrade(cfg, "base")
    assert set(inspect(migrated_engine).get_table_names()) <= {"alembic_version"}
    command.upgrade(cfg, "head")
    tables = set(inspect(migrated_engine).get_table_names())
    assert set(Base.metadata.tables) <= tables


def _customer(db: Session) -> Customer:
    customer = Customer(
        external_ref=f"CUST-T{uuid.uuid4().hex[:6]}",
        display_name="Test (fictional)",
        branch_code="CHN001",
        created_at=NOW,
    )
    db.add(customer)
    db.flush()
    return customer


def _episode(customer: Customer, status: EpisodeStatus = EpisodeStatus.OPEN) -> RiskEpisode:
    return RiskEpisode(
        customer_id=customer.id,
        status=status,
        opened_at=NOW,
        last_stage_at=NOW,
        stages=[],
        watch_tier=Tier.LOW,
    )


def test_only_one_open_episode_per_customer(db: Session) -> None:
    customer = _customer(db)
    db.add(_episode(customer))
    db.add(_episode(customer, EpisodeStatus.EXPIRED))
    db.flush()
    db.add(_episode(customer))
    with pytest.raises(IntegrityError, match="uq_risk_episodes_one_open"):
        db.flush()


def test_negative_balance_rejected(db: Session) -> None:
    customer = _customer(db)
    with pytest.raises(IntegrityError, match="balance_non_negative"):
        db.execute(
            text(
                "INSERT INTO accounts (id, customer_id, account_type, masked_number, balance_paise,"
                " opened_at, status) VALUES (:id, :c, 'SAVINGS', 'XXXXXX0001', -1, now(), 'ACTIVE')"
            ),
            {"id": uuid.uuid4(), "c": customer.id},
        )


def test_unknown_enum_value_rejected(db: Session) -> None:
    with pytest.raises(IntegrityError, match="preferred_language_valid"):
        db.execute(
            text(
                "INSERT INTO customers (id, external_ref, display_name, preferred_language,"
                " branch_code, created_at) VALUES (:id, 'CUST-X', 'X', 'hi', 'CHN001', now())"
            ),
            {"id": uuid.uuid4()},
        )


def test_enum_columns_load_as_enum_members(db: Session) -> None:
    customer = _customer(db)
    db.add(_episode(customer))
    db.flush()
    db.expire_all()
    episode = db.query(RiskEpisode).filter_by(customer_id=customer.id).one()
    assert episode.status is EpisodeStatus.OPEN
    assert episode.watch_tier is Tier.LOW
