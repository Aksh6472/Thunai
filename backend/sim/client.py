"""HTTP client for the simulator (CLAUDE.md §6: sim talks to the app only over HTTP)."""

import asyncio
from datetime import datetime
from typing import Any

import httpx

SERVICE_HEADER = "X-Thunai-Service-Key"


class SimClient:
    def __init__(self, http: httpx.AsyncClient, service_key: str) -> None:
        self.http = http
        self.service = {SERVICE_HEADER: service_key}
        self._teller_token: str | None = None

    async def call(
        self, method: str, path: str, *, json: Any = None, headers: dict[str, str] | None = None
    ) -> httpx.Response:
        """Retries network errors up to 3 times; the API is idempotent by event_id/transfer_ref."""
        for attempt in range(3):
            try:
                return await self.http.request(method, path, json=json, headers=headers)
            except httpx.TransportError:
                if attempt == 2:
                    raise
                await asyncio.sleep(0.2 * (attempt + 1))
        raise RuntimeError("unreachable")

    async def set_clock(self, at: datetime, speed: float, scenario: str | None) -> None:
        r = await self.call(
            "POST",
            "/demo/clock",
            json={"sim_now": at.isoformat(), "speed": speed, "running_scenario": scenario},
            headers=self.service,
        )
        r.raise_for_status()

    async def post(self, path: str, body: dict[str, Any]) -> httpx.Response:
        return await self.call("POST", path, json=body, headers=self.service)

    async def teller_post(
        self, path: str, body: dict[str, Any], username: str, password: str
    ) -> httpx.Response:
        if self._teller_token is None:
            r = await self.call(
                "POST", "/auth/login", json={"username": username, "password": password}
            )
            r.raise_for_status()
            self._teller_token = r.json()["access_token"]
        return await self.call(
            "POST", path, json=body, headers={"Authorization": f"Bearer {self._teller_token}"}
        )
