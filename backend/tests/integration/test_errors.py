"""T-005: error envelope (API_SPEC §2.1), request id, body limit, readiness."""

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from app.core.errors import NotFound

pytestmark = pytest.mark.anyio


def _assert_envelope(response: httpx.Response, status: int, code: str) -> dict[str, object]:
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert error["code"] == code
    assert isinstance(error["message"], str)
    assert error["request_id"] == response.headers["x-request-id"]
    return error  # type: ignore[no-any-return]


async def test_unknown_route_returns_envelope(client: httpx.AsyncClient) -> None:
    _assert_envelope(await client.get("/api/v1/nope"), 404, "NOT_FOUND")


async def test_every_response_has_request_id(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/healthz")
    assert response.headers["x-request-id"].startswith("req_")


async def test_safe_incoming_request_id_is_kept(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/healthz", headers={"X-Request-ID": "abc12345-trace"})
    assert response.headers["x-request-id"] == "abc12345-trace"


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str


@pytest.fixture
def app_with_test_routes(app: FastAPI) -> FastAPI:
    @app.get("/test/typed-error")
    def typed_error() -> None:
        raise NotFound("hold")

    @app.get("/test/crash")
    def crash() -> None:
        raise RuntimeError("SELECT secret FROM table -- must not leak")

    @app.post("/test/echo")
    def echo(body: _Body) -> dict[str, str]:
        return {"name": body.name}

    return app


@pytest.fixture
async def test_client(app_with_test_routes: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app_with_test_routes, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_typed_error_maps_to_envelope(test_client: httpx.AsyncClient) -> None:
    error = _assert_envelope(await test_client.get("/test/typed-error"), 404, "HOLD_NOT_FOUND")
    assert error["message"] == "No hold with that id."


async def test_unhandled_exception_never_leaks(test_client: httpx.AsyncClient) -> None:
    response = await test_client.get("/test/crash")
    _assert_envelope(response, 500, "INTERNAL_ERROR")
    assert "SELECT" not in response.text
    assert "Traceback" not in response.text


async def test_validation_error_lists_fields_without_echoing_input(
    test_client: httpx.AsyncClient,
) -> None:
    response = await test_client.post("/test/echo", json={"name": "ok", "status": "+919800000193"})
    error = _assert_envelope(response, 422, "VALIDATION_ERROR")
    assert error["details"]["fields"][0]["loc"] == ["body", "status"]  # type: ignore[index]
    assert "919800000193" not in response.text


async def test_body_over_64kb_is_rejected(test_client: httpx.AsyncClient) -> None:
    response = await test_client.post("/test/echo", content=b"x" * (65 * 1024))
    _assert_envelope(response, 413, "PAYLOAD_TOO_LARGE")


async def test_readyz_reports_components(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/readyz")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "db": "ok",
        "scoring_config": "scoring_v1@2026-10-17",
        "notifier": "console",
    }


async def test_readyz_503_when_db_down(app: FastAPI) -> None:
    from app.db import make_engine

    app.state.engine = make_engine("postgresql+psycopg://nobody:x@127.0.0.1:1/none")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/api/v1/readyz")
    error = _assert_envelope(response, 503, "DEPENDENCY_UNAVAILABLE")
    assert error["details"]["db"] == "error"  # type: ignore[index]
