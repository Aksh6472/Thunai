"""Holds and officer review (API_SPEC §6)."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_ctx, get_db, require_roles
from app.core.security import Principal
from app.domain.enums import HoldStatus, Role, Tier
from app.schemas.transfers import HoldDetail, HoldListItem, OfficerDecisionIn, Page
from app.services import contact_service, hold_read_service, hold_service
from app.services.context import Ctx

router = APIRouter(prefix="/holds", tags=["holds"])
staff_read = require_roles(Role.TELLER, Role.OFFICER, Role.ADMIN)
officer_only = require_roles(Role.OFFICER)
branch_staff = require_roles(Role.TELLER, Role.OFFICER)


@router.get("", response_model=Page[HoldListItem])
def list_holds(
    status: HoldStatus | None = None,
    tier: Tier | None = None,
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None, max_length=512),
    principal: Principal = Depends(staff_read),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> Page[HoldListItem]:
    return hold_read_service.list_holds(
        session, ctx, principal, status=status, tier=tier, limit=limit, cursor=cursor
    )


@router.get("/{hold_id}", response_model=HoldDetail)
def get_hold(
    hold_id: uuid.UUID,
    principal: Principal = Depends(staff_read),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> HoldDetail:
    return hold_read_service.hold_detail(session, ctx, principal, hold_id)


@router.post("/{hold_id}/officer-decision", response_model=HoldDetail)
def officer_decision(
    hold_id: uuid.UUID,
    body: OfficerDecisionIn,
    principal: Principal = Depends(officer_only),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> HoldDetail:
    hold_service.officer_decision(session, ctx, hold_id, body.decision, body.note, principal)
    return hold_read_service.hold_detail(session, ctx, principal, hold_id)


@router.post("/{hold_id}/resend-contact", status_code=202)
def resend_contact(
    hold_id: uuid.UUID,
    principal: Principal = Depends(branch_staff),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> dict[str, str]:
    hold_service.load_for_staff(session, hold_id, principal)  # branch scoping (404)
    request = contact_service.resend(session, ctx, hold_id, principal.id)
    return {"contact_request_id": str(request.id), "status": "QUEUED"}
