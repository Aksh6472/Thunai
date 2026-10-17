"""Scoring configuration model (AI_DESIGN §4–§6).

Pure: this module validates an already-parsed mapping. Reading the YAML file is done by
`app.core.scoring_config.load_scoring_config`, because the domain does no I/O.
"""

from datetime import date
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Tier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _require_strictly_increasing(values: list[float], what: str) -> None:
    if any(b <= a for a, b in zip(values, values[1:], strict=False)):
        raise ValueError(f"{what} must be strictly increasing, got {values}")


class TierThresholds(_Frozen):
    medium: int = Field(gt=0, le=100)
    high: int = Field(gt=0, le=100)
    very_high: int = Field(gt=0, le=100)

    @model_validator(mode="after")
    def _increasing(self) -> Self:
        _require_strictly_increasing([self.medium, self.high, self.very_high], "tier thresholds")
        return self

    def tier_for(self, score: int) -> Tier:
        if score >= self.very_high:
            return Tier.VERY_HIGH
        if score >= self.high:
            return Tier.HIGH
        if score >= self.medium:
            return Tier.MEDIUM
        return Tier.LOW


class FdPrematureClosurePoints(_Frozen):
    default: int = Field(ge=0)
    habitual: int = Field(ge=0)
    habitual_min_closures: int = Field(ge=1)

    @model_validator(mode="after")
    def _habit_dampens(self) -> Self:
        if self.habitual > self.default:
            raise ValueError("habitual FD points must not exceed default points")
        return self


class NewPayeeBand(_Frozen):
    max_age_hours: int = Field(gt=0)
    points: int = Field(ge=0)


class MultipleBand(_Frozen):
    min_multiple: float = Field(gt=0)
    points: int = Field(ge=0)


class HighValuePoints(_Frozen):
    min_amount_paise: int = Field(gt=0)
    bands: list[MultipleBand] = Field(min_length=1)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        _require_strictly_increasing([b.min_multiple for b in self.bands], "high-value multiples")
        _require_strictly_increasing([b.points for b in self.bands], "high-value points")
        return self


class BalanceDrainPoints(_Frozen):
    min_fraction_of_balance: float = Field(gt=0, le=1)
    points: int = Field(ge=0)


class StageSequenceBand(_Frozen):
    min_stages: int = Field(ge=2, le=4)
    points: int = Field(ge=0)


class FriRiskPoints(_Frozen):
    medium: int = Field(ge=0)
    high: int = Field(ge=0)
    very_high: int = Field(ge=0)

    @model_validator(mode="after")
    def _increasing(self) -> Self:
        _require_strictly_increasing([self.medium, self.high, self.very_high], "FRI points")
        return self


class CallDurationBand(_Frozen):
    min_duration_min: int = Field(gt=0)
    points: int = Field(ge=0)


class TellerPoints(_Frozen):
    on_call: int = Field(ge=0)
    distressed: int = Field(ge=0)
    following_instructions: int = Field(ge=0)
    mentions_authority: int = Field(ge=0)
    cap: int = Field(ge=0)


class EstablishedPayeePoints(_Frozen):
    min_payee_age_days: int = Field(gt=0)
    min_prior_successful_transfers: int = Field(ge=1)
    points: int = Field(lt=0)


class RegularPatternPoints(_Frozen):
    max_multiple_of_recurring: float = Field(gt=0)
    points: int = Field(lt=0)


class Points(_Frozen):
    fd_premature_closure: FdPrematureClosurePoints
    funds_pooled: int = Field(ge=0)
    new_payee: list[NewPayeeBand] = Field(min_length=1)
    high_value_to_payee: HighValuePoints
    balance_drain: BalanceDrainPoints
    stage_sequence: list[StageSequenceBand] = Field(min_length=1)
    fri_risk: FriRiskPoints
    long_call_unknown: list[CallDurationBand] = Field(min_length=1)
    teller: TellerPoints
    trusted_contact_recently_changed: int = Field(ge=0)
    established_payee: EstablishedPayeePoints
    matches_regular_pattern: RegularPatternPoints
    watch_new_payee_flat: int = Field(ge=0)

    @model_validator(mode="after")
    def _bands_ordered(self) -> Self:
        # New payee: younger payee (smaller max age) scores more.
        _require_strictly_increasing([b.max_age_hours for b in self.new_payee], "new-payee ages")
        _require_strictly_increasing(
            [-b.points for b in self.new_payee], "new-payee points (descending)"
        )
        _require_strictly_increasing(
            [b.min_stages for b in self.stage_sequence], "stage-sequence counts"
        )
        _require_strictly_increasing(
            [b.points for b in self.stage_sequence], "stage-sequence points"
        )
        _require_strictly_increasing(
            [b.min_duration_min for b in self.long_call_unknown], "call durations"
        )
        _require_strictly_increasing([b.points for b in self.long_call_unknown], "call points")
        return self


class Overrides(_Frozen):
    fri_very_high_floor_tier: Tier
    hold_floor_paise: int = Field(gt=0)


class BaselineParams(_Frozen):
    lookback_days: int = Field(gt=0)
    min_qualifying_amount_paise: int = Field(ge=0)
    min_qualifying_transfers: int = Field(ge=1)
    min_history_days: int = Field(ge=0)
    population_default_median_paise: int = Field(gt=0)
    fd_closure_lookback_days: int = Field(gt=0)


class StageParams(_Frozen):
    pooling_window_hours: int = Field(gt=0)
    pooling_min_inbound_count: int = Field(ge=1)
    pooling_min_sum_paise: int = Field(gt=0)
    pooling_min_multiple_of_median: float = Field(gt=0)
    min_high_value_paise: int = Field(gt=0)
    high_value_min_multiple_of_median: float = Field(gt=0)


class Windows(_Frozen):
    episode_quiet_days: int = Field(gt=0)
    call_freshness_minutes: int = Field(gt=0)
    trusted_contact_changed_days: int = Field(gt=0)
    trusted_contact_activation_hours: int = Field(ge=0)
    cooling_off_minutes: int = Field(gt=0)


class ScoringConfig(_Frozen):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    effective_date: date
    tiers: TierThresholds
    points: Points
    overrides: Overrides
    baseline: BaselineParams
    stages: StageParams
    windows: Windows

    @property
    def config_version(self) -> str:
        return f"{self.name}@{self.effective_date.isoformat()}"

    @classmethod
    def from_mapping(cls, data: Any) -> "ScoringConfig":
        """Validate a parsed YAML mapping. Raises `pydantic.ValidationError` on bad config."""
        return cls.model_validate(data)
