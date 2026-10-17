"""Baselines, episodes and assessments."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import EpisodeStatus
from app.models import CustomerBaseline, RiskAssessment, RiskEpisode


def baseline_for(session: Session, customer_id: uuid.UUID) -> CustomerBaseline | None:
    return session.get(CustomerBaseline, customer_id)


def open_episode(
    session: Session, customer_id: uuid.UUID, *, for_update: bool = False
) -> RiskEpisode | None:
    stmt = select(RiskEpisode).where(
        RiskEpisode.customer_id == customer_id, RiskEpisode.status == EpisodeStatus.OPEN
    )
    if for_update:
        stmt = stmt.with_for_update()
    return session.scalar(stmt)


def latest_episode(session: Session, customer_id: uuid.UUID) -> RiskEpisode | None:
    return session.scalar(
        select(RiskEpisode)
        .where(RiskEpisode.customer_id == customer_id)
        .order_by(RiskEpisode.opened_at.desc())
        .limit(1)
    )


def latest_assessment(session: Session, transfer_id: uuid.UUID) -> RiskAssessment | None:
    return session.scalar(
        select(RiskAssessment)
        .where(RiskAssessment.transfer_id == transfer_id)
        .order_by(RiskAssessment.assessed_at.desc(), RiskAssessment.id)
        .limit(1)
    )


def assessments_for_transfer(session: Session, transfer_id: uuid.UUID) -> list[RiskAssessment]:
    return list(
        session.scalars(
            select(RiskAssessment)
            .where(RiskAssessment.transfer_id == transfer_id)
            .order_by(RiskAssessment.assessed_at)
        )
    )
