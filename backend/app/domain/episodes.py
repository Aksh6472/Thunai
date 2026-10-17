"""Risk episodes and the watch score (AI_DESIGN §5.2). Pure."""

from datetime import datetime, timedelta

from app.domain.config import ScoringConfig
from app.domain.enums import EVENT_STAGES, EpisodeStatus, Stage, Tier
from app.domain.models import Baseline, CallSignal, Episode, Reason, StageEvent, WatchPoint
from app.domain.reasons import render_reasons
from app.domain.signals import ReasonDraft, call_reason, contact_changed_reason
from app.domain.stage_reasons import fd_reason, pooled_reason, sequence_reason


def is_expired(episode: Episode, at: datetime, cfg: ScoringConfig) -> bool:
    """An open episode closes 7 quiet days after its last stage event."""
    quiet = timedelta(days=cfg.windows.episode_quiet_days)
    return episode.status is EpisodeStatus.OPEN and at - episode.last_stage_at > quiet


def expire(episode: Episode, cfg: ScoringConfig) -> Episode:
    closed_at = episode.last_stage_at + timedelta(days=cfg.windows.episode_quiet_days)
    return episode.model_copy(update={"status": EpisodeStatus.EXPIRED, "closed_at": closed_at})


def close(episode: Episode, status: EpisodeStatus, at: datetime) -> Episode:
    if status is EpisodeStatus.OPEN:
        raise ValueError("close() needs a closed status")
    return episode.model_copy(update={"status": status, "closed_at": at})


def update_episode(episode: Episode | None, stage_event: StageEvent, cfg: ScoringConfig) -> Episode:
    """Open a new episode, or extend the open one. Expired episodes are replaced, never reopened."""
    if episode is not None and is_expired(episode, stage_event.occurred_at, cfg):
        episode = None
    if episode is None or episode.status is not EpisodeStatus.OPEN:
        return Episode(
            status=EpisodeStatus.OPEN,
            opened_at=stage_event.occurred_at,
            last_stage_at=stage_event.occurred_at,
            stages=(stage_event,),
        )
    stages = tuple(sorted((*episode.stages, stage_event), key=lambda s: s.occurred_at))
    return episode.model_copy(
        update={
            "stages": stages,
            "last_stage_at": max(episode.last_stage_at, stage_event.occurred_at),
        }
    )


def watch_score(
    stages: tuple[StageEvent, ...],
    baseline: Baseline,
    call: CallSignal | None,
    contact_changed_at: datetime | None,
    at: datetime,
    cfg: ScoringConfig,
) -> tuple[int, Tier, tuple[Reason, ...]]:
    """Pre-transfer score: stage reasons, a flat S3 value, the S1–S3 sequence, call, contact change.

    Transfer-specific reasons (amount, drain, FRI, teller, dampeners) are excluded (§5.2).
    """
    pre_transfer = tuple(s for s in stages if s.stage in EVENT_STAGES)
    drafts: list[ReasonDraft | None] = [
        fd_reason(pre_transfer, baseline, cfg),
        pooled_reason(pre_transfer, cfg),
    ]
    if any(s.stage is Stage.S3_NEW_PAYEE for s in pre_transfer):
        drafts.append(
            ReasonDraft(
                "NEW_PAYEE",
                cfg.points.watch_new_payee_flat,
                Stage.S3_NEW_PAYEE.value,
                {"payee_age_minutes": 0, "watch_flat": True},
            )
        )
    drafts += [
        sequence_reason(pre_transfer, cfg),
        call_reason(call, at, cfg),
        contact_changed_reason(contact_changed_at, at, cfg),
    ]
    reasons = render_reasons([d for d in drafts if d is not None])
    raw = sum(r.points for r in reasons)
    score = max(0, min(100, raw))
    return score, cfg.tiers.tier_for(score), reasons


def with_watch(
    episode: Episode, score: int, tier: Tier, at: datetime, trigger_event_id: str
) -> Episode:
    point = WatchPoint(at=at, score=score, tier=tier, trigger_event_id=trigger_event_id)
    return episode.model_copy(
        update={
            "watch_score": score,
            "watch_tier": tier,
            "watch_history": (*episode.watch_history, point),
        }
    )
