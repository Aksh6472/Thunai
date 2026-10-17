"""T-006: scoring config schema and loader (AI_DESIGN §6)."""

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from app.core.scoring_config import (
    DEFAULT_SCORING_CONFIG_PATH,
    ScoringConfigError,
    load_scoring_config,
)
from app.domain.config import ScoringConfig, Tier


@pytest.fixture
def raw() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(DEFAULT_SCORING_CONFIG_PATH.read_text(encoding="utf-8"))
    return data


def test_shipped_config_loads_with_version() -> None:
    cfg = load_scoring_config()
    assert cfg.config_version == "scoring_v1@2026-10-17"


def test_shipped_config_matches_ai_design_key_values() -> None:
    cfg = load_scoring_config()
    assert (cfg.tiers.medium, cfg.tiers.high, cfg.tiers.very_high) == (30, 55, 75)
    assert cfg.stages.min_high_value_paise == 20_000_000
    assert cfg.overrides.hold_floor_paise == 5_000_000
    assert cfg.overrides.fri_very_high_floor_tier is Tier.HIGH
    assert cfg.windows.episode_quiet_days == 7
    assert cfg.stages.pooling_window_hours == 72
    assert cfg.points.teller.cap == 30
    assert cfg.points.established_payee.points == -25
    assert cfg.points.matches_regular_pattern.points == -15


def test_hero_p1_worked_example_totals_115() -> None:
    """AI_DESIGN §6.4: P1 adds up to 115 using the configured points."""
    p = load_scoring_config().points
    total = (
        p.fd_premature_closure.default
        + p.funds_pooled
        + p.new_payee[0].points  # < 2 h
        + p.high_value_to_payee.bands[-1].points  # 115x >= 100x
        + p.balance_drain.points
        + p.stage_sequence[-1].points  # 4 stages
        + p.long_call_unknown[-1].points  # 190 min
        + p.fri_risk.high
    )
    assert total == 115


@pytest.mark.parametrize(
    ("score", "tier"),
    [(0, Tier.LOW), (29, Tier.LOW), (30, Tier.MEDIUM), (54, Tier.MEDIUM),
     (55, Tier.HIGH), (74, Tier.HIGH), (75, Tier.VERY_HIGH), (100, Tier.VERY_HIGH)],
)  # fmt: skip
def test_tier_boundaries(score: int, tier: Tier) -> None:
    assert load_scoring_config().tiers.tier_for(score) is tier


@pytest.mark.parametrize(
    "tiers",
    [
        {"medium": 55, "high": 30, "very_high": 75},
        {"medium": 30, "high": 30, "very_high": 75},
        {"medium": 30, "high": 80, "very_high": 75},
    ],
)
def test_rejects_non_increasing_tier_thresholds(raw: dict[str, Any], tiers: dict[str, int]) -> None:
    raw["tiers"] = tiers
    with pytest.raises(ValidationError, match="tier thresholds must be strictly increasing"):
        ScoringConfig.from_mapping(raw)


def test_rejects_unordered_bands(raw: dict[str, Any]) -> None:
    bad = copy.deepcopy(raw)
    bad["points"]["high_value_to_payee"]["bands"].reverse()
    with pytest.raises(ValidationError, match="high-value multiples"):
        ScoringConfig.from_mapping(bad)


def test_rejects_non_negative_dampener(raw: dict[str, Any]) -> None:
    raw["points"]["established_payee"]["points"] = 25
    with pytest.raises(ValidationError):
        ScoringConfig.from_mapping(raw)


def test_rejects_unknown_keys(raw: dict[str, Any]) -> None:
    raw["points"]["age_bonus"] = 10  # protected attributes must never sneak in as inputs
    with pytest.raises(ValidationError):
        ScoringConfig.from_mapping(raw)


def test_config_is_immutable() -> None:
    cfg = load_scoring_config()
    with pytest.raises(ValidationError):
        cfg.tiers.medium = 10  # type: ignore[misc]


def test_loader_wraps_invalid_file(tmp_path: Path, raw: dict[str, Any]) -> None:
    raw["tiers"]["high"] = 10
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ScoringConfigError, match="invalid scoring config"):
        load_scoring_config(path)


def test_loader_wraps_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ScoringConfigError, match="cannot read"):
        load_scoring_config(tmp_path / "nope.yaml")
