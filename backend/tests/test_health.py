import httpx
import pytest

pytestmark = pytest.mark.anyio


async def test_healthz_returns_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_unknown_route_is_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
