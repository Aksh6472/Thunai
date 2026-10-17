"""Customer app endpoints (API_SPEC §5). CUSTOMER role, own resources only."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_ctx, get_db, require_roles
from app.core.security import Principal
from app.domain.enums import Role
from app.schemas.customer import (
    ConsentIn,
    ConsentOut,
    CustomerOverview,
    TrustedContactIn,
    TrustedContactOut,
)
from app.schemas.transfers import (
    CustomerTransferIn,
    CustomerTransferOut,
    TransferStatusOut,
    WarningResponseIn,
)
from app.services import customer_service
from app.services.context import Ctx

router = APIRouter(prefix="/customer", tags=["customer"])
customer_only = require_roles(Role.CUSTOMER)


@router.get("/overview", response_model=CustomerOverview)
def overview(
    principal: Principal = Depends(customer_only),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> CustomerOverview:
    return customer_service.overview(session, ctx, principal)


@router.post("/transfers", response_model=CustomerTransferOut)
def create_transfer(
    body: CustomerTransferIn,
    response: Response,
    principal: Principal = Depends(customer_only),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> CustomerTransferOut:
    result, replayed = customer_service.create_transfer(session, ctx, principal, body)
    if replayed:
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.get("/transfers/{transfer_ref}", response_model=CustomerTransferOut)
def transfer_status(
    transfer_ref: str,
    principal: Principal = Depends(customer_only),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> CustomerTransferOut:
    return customer_service.transfer_status(session, ctx, principal, transfer_ref)


@router.post("/transfers/{transfer_ref}/warning-response", response_model=TransferStatusOut)
def warning_response(
    transfer_ref: str,
    body: WarningResponseIn,
    principal: Principal = Depends(customer_only),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> TransferStatusOut:
    return customer_service.warning_response(session, ctx, principal, transfer_ref, body)


@router.post("/transfers/{transfer_ref}/cancel", response_model=TransferStatusOut)
def cancel(
    transfer_ref: str,
    principal: Principal = Depends(customer_only),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> TransferStatusOut:
    return customer_service.cancel(session, ctx, principal, transfer_ref)


@router.post("/consents", response_model=ConsentOut, status_code=201)
def record_consent(
    body: ConsentIn,
    principal: Principal = Depends(customer_only),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> ConsentOut:
    return customer_service.record_consent(session, ctx, principal, body)


@router.post("/trusted-contact", response_model=TrustedContactOut, status_code=201)
def register_contact(
    body: TrustedContactIn,
    principal: Principal = Depends(customer_only),
    session: Session = Depends(get_db),
    ctx: Ctx = Depends(get_ctx),
) -> TrustedContactOut:
    return customer_service.register_contact(session, ctx, principal, body)
