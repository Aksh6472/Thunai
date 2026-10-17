"""Demo control (API_SPEC §11). ADMIN only, and only when THUNAI_DEMO_MODE=true (else 403)."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, require_staff_or_service
from app.core.security import Principal
from app.domain.enums import Role
from app.schemas.demo import (
    ClockIn,
    ClockOut,
    ConsoleMessageOut,
    FriIn,
    FriOut,
    ResetOut,
    RunIn,
    RunOut,
    ScenarioOut,
)
from app.services import demo_service


def demo_guard(request: Request) -> None:
    demo_service.ensure_demo(request.app.state.settings)


router = APIRouter(prefix="/demo", tags=["demo"], dependencies=[Depends(demo_guard)])
admin = require_roles(Role.ADMIN)
admin_or_service = require_staff_or_service(Role.ADMIN)
admin_or_staff = require_roles(Role.ADMIN, Role.OFFICER, Role.TELLER)


@router.get("/scenarios", response_model=list[ScenarioOut])
def scenarios(request: Request, _: Principal = Depends(admin)) -> list[ScenarioOut]:
    return demo_service.list_scenarios(request.app.state)


@router.post("/reset", response_model=ResetOut)
def reset(
    request: Request, _: Principal = Depends(admin), session: Session = Depends(get_db)
) -> ResetOut:
    return demo_service.reset(session, request.app.state)


@router.post("/scenarios/{scenario_id}/run", response_model=RunOut, status_code=202)
async def run(
    scenario_id: str, request: Request, body: RunIn | None = None, _: Principal = Depends(admin)
) -> RunOut:
    speed = body.speed if body else request.app.state.settings.sim_default_speed
    return demo_service.run(request.app.state, request.app, scenario_id, speed)


@router.get("/runs", response_model=list[RunOut])
def runs(
    request: Request, limit: int = Query(10, ge=1, le=50), _: Principal = Depends(admin)
) -> list[RunOut]:
    return demo_service.runs(request.app.state, limit)


@router.get("/clock", response_model=ClockOut)
def get_clock(request: Request, _: Principal = Depends(admin_or_staff)) -> ClockOut:
    return demo_service.clock(request.app.state)


@router.post("/clock", response_model=ClockOut)
def set_clock(
    body: ClockIn, request: Request, _: Principal = Depends(admin_or_service)
) -> ClockOut:
    return demo_service.set_clock(request.app.state, body)


@router.post("/fri", response_model=FriOut)
def set_fri(
    body: FriIn,
    request: Request,
    principal: Principal = Depends(admin),
    session: Session = Depends(get_db),
) -> FriOut:
    return demo_service.set_fri(session, request.app.state.settings, body, principal.id)


@router.get("/console-messages", response_model=list[ConsoleMessageOut])
def console_messages(
    request: Request, limit: int = Query(20, ge=1, le=50), _: Principal = Depends(admin)
) -> list[ConsoleMessageOut]:
    return demo_service.console_messages(request.app.state, limit)
