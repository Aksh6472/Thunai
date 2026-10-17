"""Request context middleware: request id, access log, body-size limit, last-resort 500.

Pure ASGI (not BaseHTTPMiddleware) so it wraps every response, including errors.
"""

import json
import logging
import re
import time
import uuid
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_body
from app.core.logging import reset_request_id, set_request_id

logger = logging.getLogger("app.request")

MAX_BODY_BYTES = 64 * 1024
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")


class _BodyTooLarge(Exception):
    pass


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope) or f"req_{uuid.uuid4().hex}"
        token = set_request_id(request_id)
        started = time.perf_counter()
        state: dict[str, Any] = {"status": 500, "started": False}

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                state["status"] = message["status"]
                state["started"] = True
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise _BodyTooLarge
            return message

        try:
            if _declared_length(scope) > self.max_body_bytes:
                await _send_error(
                    send_with_id, 413, "PAYLOAD_TOO_LARGE", "The request body is too large."
                )
            else:
                await self.app(scope, limited_receive, send_with_id)
        except _BodyTooLarge:
            if not state["started"]:
                await _send_error(
                    send_with_id, 413, "PAYLOAD_TOO_LARGE", "The request body is too large."
                )
        except Exception:
            logger.exception("request.unhandled_exception")
            if not state["started"]:
                await _send_error(send_with_id, 500, "INTERNAL_ERROR", "Something went wrong.")
        finally:
            logger.info(
                "request",
                extra={
                    "method": scope.get("method"),
                    "route": _route_template(scope),
                    "status": state["status"],
                    "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            reset_request_id(token)


def _incoming_request_id(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            return candidate if _SAFE_REQUEST_ID.match(candidate) else None
    return None


def _declared_length(scope: Scope) -> int:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return 0
    return 0


def _route_template(scope: Scope) -> str:
    # The matched template (e.g. /trusted/{token}) never contains the token itself.
    route = scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path else "unmatched"


async def _send_error(send: Send, status: int, code: str, message: str) -> None:
    body = json.dumps(error_body(code, message)).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
