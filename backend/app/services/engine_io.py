"""Converters between ORM rows and pure domain types."""

from datetime import date
from typing import Any

from app.domain.enums import EpisodeStatus, EventType
from app.domain.models import CallSignal, Episode, EventFacts, StageEvent, WatchPoint
from app.models import AccountEvent, RiskEpisode, Signal


def event_facts(row: AccountEvent) -> EventFacts:
    payload: dict[str, Any] = row.payload or {}
    maturity = payload.get("maturity_date")
    to_account = None
    if row.event_type is EventType.INTERNAL_TRANSFER_IN:
        to_account = payload.get("to_account")
    elif row.event_type is EventType.FD_CLOSED:
        to_account = payload.get("proceeds_to_account")
    return EventFacts(
        event_id=row.event_id,
        event_type=row.event_type,
        occurred_at=row.occurred_at,
        amount_paise=row.amount_paise,
        maturity_date=date.fromisoformat(maturity) if maturity else None,
        to_account=to_account,
        payee_id=payload.get("payee_id"),
    )


def episode_from_row(row: RiskEpisode) -> Episode:
    return Episode(
        status=row.status,
        opened_at=row.opened_at,
        last_stage_at=row.last_stage_at,
        closed_at=row.closed_at,
        stages=tuple(StageEvent.model_validate(s) for s in row.stages),
        watch_score=row.watch_score,
        watch_tier=row.watch_tier,
        watch_history=tuple(WatchPoint.model_validate(p) for p in row.watch_history),
    )


def apply_episode(row: RiskEpisode, episode: Episode) -> RiskEpisode:
    row.status = episode.status
    row.opened_at = episode.opened_at
    row.last_stage_at = episode.last_stage_at
    row.closed_at = episode.closed_at
    row.stages = [s.model_dump(mode="json") for s in episode.stages]
    row.watch_score = episode.watch_score
    row.watch_tier = episode.watch_tier
    row.watch_history = [p.model_dump(mode="json") for p in episode.watch_history]
    return row


def new_episode_row(customer_id: Any, episode: Episode) -> RiskEpisode:
    row = RiskEpisode(customer_id=customer_id, status=EpisodeStatus.OPEN)
    return apply_episode(row, episode)


def call_signal(row: Signal | None) -> CallSignal | None:
    if row is None:
        return None
    value = row.value
    return CallSignal(
        call_type=value["call_type"],
        caller_known=value["caller_known"],
        duration_min=value["duration_min"],
        ended_at=value.get("ended_at"),
        observed_at=row.observed_at,
    )
