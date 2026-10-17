"""Stage-based reason drafts shared by the watch score and the transfer score (AI_DESIGN §6.1)."""

from collections.abc import Sequence

from app.domain.config import ScoringConfig
from app.domain.enums import Stage
from app.domain.models import Baseline, StageEvent
from app.domain.signals import ReasonDraft
from app.domain.stages import canonical_sequence


def _first(stages: Sequence[StageEvent], stage: Stage) -> StageEvent | None:
    matching = [s for s in stages if s.stage is stage]
    return min(matching, key=lambda s: s.occurred_at) if matching else None


def fd_reason(
    stages: Sequence[StageEvent], baseline: Baseline, cfg: ScoringConfig
) -> ReasonDraft | None:
    event = _first(stages, Stage.S1_LIQUIDATION)
    if event is None:
        return None
    weights = cfg.points.fd_premature_closure
    habitual = baseline.premature_fd_closures_365d >= weights.habitual_min_closures
    return ReasonDraft(
        "FD_PREMATURE_CLOSURE",
        weights.habitual if habitual else weights.default,
        Stage.S1_LIQUIDATION.value,
        {"amount_paise": event.amount_paise, "event_id": event.event_id, "habitual": habitual},
    )


def pooled_reason(stages: Sequence[StageEvent], cfg: ScoringConfig) -> ReasonDraft | None:
    pooled = [s for s in stages if s.stage is Stage.S2_POOLING]
    if not pooled:
        return None
    latest = max(pooled, key=lambda s: s.occurred_at)
    return ReasonDraft(
        "FUNDS_POOLED",
        cfg.points.funds_pooled,
        Stage.S2_POOLING.value,
        {
            "amount_paise": latest.amount_paise,
            "event_id": latest.event_id,
            "window_hours": cfg.stages.pooling_window_hours,
        },
    )


def sequence_reason(stages: Sequence[StageEvent], cfg: ScoringConfig) -> ReasonDraft | None:
    sequence = canonical_sequence(stages)
    points = 0
    for band in cfg.points.stage_sequence:
        if len(sequence) >= band.min_stages:
            points = band.points
    if points == 0:
        return None
    return ReasonDraft(
        "STAGE_SEQUENCE",
        points,
        None,
        {"count": len(sequence), "stages": [s.value for s in sequence]},
    )
