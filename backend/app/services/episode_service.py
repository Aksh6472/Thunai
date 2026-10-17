"""Persist episode changes and the watch score (AI_DESIGN §5.2)."""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.config import ScoringConfig
from app.domain.enums import EpisodeStatus
from app.domain.episodes import close, expire, is_expired, update_episode, watch_score, with_watch
from app.domain.models import Baseline, StageEvent
from app.models import RiskEpisode
from app.repositories import customers, events, risk
from app.services.engine_io import apply_episode, call_signal, episode_from_row, new_episode_row


def current_open(
    session: Session, customer_id: uuid.UUID, at: datetime, cfg: ScoringConfig
) -> RiskEpisode | None:
    """The open episode, after lazily expiring it if it has been quiet for 7 days."""
    row = risk.open_episode(session, customer_id, for_update=True)
    if row is None:
        return None
    episode = episode_from_row(row)
    if is_expired(episode, at, cfg):
        apply_episode(row, expire(episode, cfg))
        session.flush()
        return None
    return row


def record_stage(
    session: Session, customer_id: uuid.UUID, stage_event: StageEvent, cfg: ScoringConfig
) -> RiskEpisode:
    row = current_open(session, customer_id, stage_event.occurred_at, cfg)
    current = episode_from_row(row) if row else None
    updated = update_episode(current, stage_event, cfg)
    if row is None:
        row = new_episode_row(customer_id, updated)
        session.add(row)
        session.flush()
    else:
        apply_episode(row, updated)
    return row


def refresh_watch(
    session: Session,
    row: RiskEpisode,
    baseline: Baseline,
    at: datetime,
    trigger_id: str,
    cfg: ScoringConfig,
) -> RiskEpisode:
    episode = episode_from_row(row)
    call = call_signal(events.latest_call_signal(session, row.customer_id, at))
    contact_changed_at = customers.latest_contact_registration(session, row.customer_id)
    score, tier, _ = watch_score(episode.stages, baseline, call, contact_changed_at, at, cfg)
    apply_episode(row, with_watch(episode, score, tier, at, trigger_id))
    return row


def close_episode(
    session: Session, episode_id: uuid.UUID | None, status: EpisodeStatus, at: datetime
) -> None:
    if episode_id is None:
        return
    row = session.get(RiskEpisode, episode_id)
    if row is None or row.status is not EpisodeStatus.OPEN:
        return
    apply_episode(row, close(episode_from_row(row), status, at))
