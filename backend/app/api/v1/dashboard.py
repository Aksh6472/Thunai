"""Ops dashboard reads (API_SPEC §10)."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_ctx, get_db, require_roles
from app.core.security import Principal
from app.domain.enums import Role, Tier
from app.schemas.dashboard import AlertItem, CustomerListItem, CustomerRisk, Summary, TimelineItem
from app.schemas.transfers import Page
from app.services import dashboard_service
from app.services.context import Ctx

router = APIRouter(tags=["dashboard"])
ops = require_roles(Role.OFFICER, Role.ADMIN)
ops_and_teller = require_roles(Role.TELLER, Role.OFFICER, Role.ADMIN)


@router.get("/dashboard/summary", response_model=Summary)
def summary(
    principal: Principal = Depends(ops),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> Summary:
    return dashboard_service.summary(session, ctx, principal)


@router.get("/alerts", response_model=Page[AlertItem])
def alerts(
    kind: Literal["HOLD", "WARN", "WATCH"] | None = None,
    tier: Tier | None = None,
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None, max_length=512),
    principal: Principal = Depends(ops_and_teller),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> Page[AlertItem]:
    return dashboard_service.alerts(
        session, ctx, principal, kind=kind, tier=tier, limit=limit, cursor=cursor
    )


@router.get("/customers", response_model=Page[CustomerListItem])
def customers(
    search: str | None = Query(None, max_length=64),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None, max_length=512),
    principal: Principal = Depends(ops),
    session: Session = Depends(get_db),
) -> Page[CustomerListItem]:
    return dashboard_service.search_customers(
        session, principal, search=search, limit=limit, cursor=cursor
    )


@router.get("/customers/{customer_id}/risk", response_model=CustomerRisk)
def customer_risk(
    customer_id: uuid.UUID,
    principal: Principal = Depends(ops_and_teller),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> CustomerRisk:
    return dashboard_service.customer_risk(session, ctx, principal, customer_id)


@router.get("/customers/{customer_id}/timeline", response_model=list[TimelineItem])
def customer_timeline(
    customer_id: uuid.UUID,
    days: int = Query(14, ge=1, le=90),
    principal: Principal = Depends(ops),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> list[TimelineItem]:
    return dashboard_service.timeline(session, ctx, principal, customer_id, days)
