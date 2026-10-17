"""Teller console (API_SPEC §7). TELLER and OFFICER."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_ctx, get_db, require_roles
from app.core.security import Principal
from app.domain.enums import Role
from app.schemas.teller import ChecklistIn, ScriptOut
from app.schemas.transfers import AssessmentResult, HoldListItem, Page
from app.services import teller_service
from app.services.context import Ctx

router = APIRouter(prefix="/teller", tags=["teller"])
branch_staff = require_roles(Role.TELLER, Role.OFFICER)


@router.get("/queue", response_model=Page[HoldListItem])
def queue(
    principal: Principal = Depends(branch_staff),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> Page[HoldListItem]:
    return teller_service.queue(session, ctx, principal)


@router.post("/transfers/{transfer_ref}/checklist", response_model=AssessmentResult)
def checklist(
    transfer_ref: str,
    body: ChecklistIn,
    principal: Principal = Depends(branch_staff),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> AssessmentResult:
    return teller_service.apply_checklist(session, ctx, principal, transfer_ref, body)


@router.get("/holds/{hold_id}/script", response_model=ScriptOut)
def script(
    hold_id: uuid.UUID,
    request: Request,
    lang: Literal["en", "ta"] = Query("en"),
    principal: Principal = Depends(branch_staff),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> ScriptOut:
    return teller_service.script(session, ctx, principal, request.app.state.scripts, hold_id, lang)
