"""Transfer assessment (API_SPEC §4). Service key; GET also for staff."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_ctx, get_db, require_service_key, require_staff_or_service
from app.core.errors import ValidationFailed
from app.core.security import Principal
from app.domain.enums import Role
from app.schemas.transfers import (
    AssessmentResult,
    TransferAssessIn,
    TransferStatusOut,
    WarningResponseIn,
)
from app.services import assessment_service, customer_service
from app.services.assessment_service import TransferRequest, to_result
from app.services.context import Ctx

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("/assess", response_model=AssessmentResult)
def assess(
    body: TransferAssessIn,
    response: Response,
    _: Principal = Depends(require_service_key),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> AssessmentResult:
    if body.scenario_label is not None and not ctx.settings.demo_mode:
        raise ValidationFailed("scenario_label is accepted only in demo mode.")
    digest = assessment_service.digest_of(body.model_dump(mode="json"))
    existing = assessment_service.existing_result(session, body.transfer_ref, digest)
    if existing is not None:
        response.headers["Idempotent-Replay"] = "true"
        return to_result(*existing)
    req = TransferRequest(
        transfer_ref=body.transfer_ref,
        from_account=body.from_account,
        payee_ref=body.payee_ref,
        amount_paise=body.amount_paise,
        rail=body.rail,
        channel=body.channel,
        initiated_at=body.initiated_at,
        scenario_label=body.scenario_label,
        digest=digest,
    )
    return to_result(
        *assessment_service.assess_new(session, ctx, body.customer_ref, req, check_balance=False)
    )


staff_or_service = require_staff_or_service(Role.TELLER, Role.OFFICER)


@router.get("/{transfer_ref}", response_model=AssessmentResult)
def get_transfer(
    transfer_ref: str,
    principal: Principal = Depends(staff_or_service),
    session: Session = Depends(get_db),
) -> AssessmentResult:
    return assessment_service.get_result(session, principal, transfer_ref)


@router.post("/{transfer_ref}/warning-response", response_model=TransferStatusOut)
def relay_warning_response(
    transfer_ref: str,
    body: WarningResponseIn,
    _: Principal = Depends(require_service_key),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> TransferStatusOut:
    """Core banking relays the customer's choice on a WARN made in its own app."""
    return customer_service.relay_warning_response(session, ctx, transfer_ref, body)
