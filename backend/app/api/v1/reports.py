"""Report drafts (API_SPEC §8)."""

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_ctx, get_db, require_roles
from app.core.security import Principal
from app.domain.enums import Role
from app.schemas.reports import MarkFiledIn, ReportCreateIn, ReportOut, ReportPatchIn
from app.services import report_service
from app.services.context import Ctx

router = APIRouter(tags=["reports"])
editors = require_roles(Role.TELLER, Role.OFFICER)
readers = require_roles(Role.TELLER, Role.OFFICER, Role.ADMIN)
officer_only = require_roles(Role.OFFICER)


@router.post("/holds/{hold_id}/report", response_model=ReportOut, status_code=201)
def create_report(
    hold_id: uuid.UUID,
    response: Response,
    body: ReportCreateIn | None = None,
    principal: Principal = Depends(editors),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> ReportOut:
    use_llm = body.use_llm if body else False
    report, created, fallback = report_service.create_or_get(
        session, ctx, principal, hold_id, use_llm
    )
    if not created:
        response.status_code = 200
    if fallback:
        response.headers["X-Thunai-LLM-Fallback"] = fallback
    return report


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(
    report_id: uuid.UUID,
    principal: Principal = Depends(readers),
    session: Session = Depends(get_db),
) -> ReportOut:
    return report_service.get(session, principal, report_id)


@router.patch("/reports/{report_id}", response_model=ReportOut)
def patch_report(
    report_id: uuid.UUID,
    body: ReportPatchIn,
    principal: Principal = Depends(editors),
    session: Session = Depends(get_db),
) -> ReportOut:
    return report_service.patch(session, principal, report_id, body)


@router.post("/reports/{report_id}/mark-filed", response_model=ReportOut)
def mark_filed(
    report_id: uuid.UUID,
    body: MarkFiledIn,
    principal: Principal = Depends(officer_only),
    session: Session = Depends(get_db),
) -> ReportOut:
    return report_service.mark_filed(session, principal, report_id, body)
