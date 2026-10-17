"""AC-14: a one-seed run produces every report section with the synthetic disclaimer."""

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from app.models import Base
from sim.evaluate import DISCLAIMER, evaluate


@pytest.fixture
def clean_after(migrated_engine: Engine) -> Iterator[None]:
    yield
    tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    with migrated_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


def test_evaluate_writes_full_report(tmp_path: Path, clean_after: None) -> None:
    summary = asyncio.run(evaluate([0], tmp_path, background=True))
    md_path, json_path = (Path(f) for f in summary["files"])
    md = md_path.read_text(encoding="utf-8")
    for section in (
        DISCLAIMER,
        "## Headline metrics",
        "## Per family",
        "## Tier by label",
        "## Reason frequency",
        "Coercion interception rate",
        "False hold rate",
        "modelled",
        "scoring_v1@2026-10-17",
        "(held out)",
    ):
        assert section in md, section
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["metrics"]["interception"]["n"] == 7
    assert data["metrics"]["explanation_coverage"]["rate"] == 1.0
    assert {row["family"] for row in data["per_family"]} >= {"P1", "N1", "BG"}
