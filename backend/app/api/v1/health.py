from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process is up. Readiness (DB, config) is /readyz, added in T-005."""
    return {"status": "ok"}
