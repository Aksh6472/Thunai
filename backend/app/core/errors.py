"""Typed errors and the API_SPEC §2.1 error envelope. Stack traces and SQL never reach clients."""

import logging
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import current_request_id

logger = logging.getLogger(__name__)


class ThunaiError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    message = "Something went wrong."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        self.headers = headers or {}
        super().__init__(self.message)


class BadRequest(ThunaiError):
    status_code, code, message = 400, "BAD_REQUEST", "The request could not be processed."


class Unauthenticated(ThunaiError):
    status_code, code, message = 401, "UNAUTHENTICATED", "Authentication is required."


class InvalidCredentials(ThunaiError):
    status_code, code, message = 401, "INVALID_CREDENTIALS", "Username or password is incorrect."


class TokenExpired(ThunaiError):
    status_code, code, message = 401, "TOKEN_EXPIRED", "Your session has expired."


class Forbidden(ThunaiError):
    status_code, code, message = 403, "FORBIDDEN", "You don't have access to this action."


class ConsentRequired(ThunaiError):
    status_code, code, message = 403, "CONSENT_REQUIRED", "The customer has not granted consent."


class DemoModeDisabled(ThunaiError):
    status_code, code, message = 403, "DEMO_MODE_DISABLED", "Demo mode is disabled."


class NotFound(ThunaiError):
    status_code, code, message = 404, "NOT_FOUND", "Not found."

    def __init__(self, entity: str = "", message: str | None = None, **kwargs: Any) -> None:
        code = f"{entity.upper()}_NOT_FOUND" if entity else None
        default = f"No {entity.lower().replace('_', ' ')} with that id." if entity else None
        super().__init__(message or default, code=code, **kwargs)


class InvalidStateTransition(ThunaiError):
    status_code, code = 409, "INVALID_STATE_TRANSITION"
    message = "This action is not allowed in the current state."


class IdempotencyConflict(ThunaiError):
    status_code, code = 409, "IDEMPOTENCY_CONFLICT"
    message = "The same key was used with a different request body."


class Conflict(ThunaiError):
    status_code, code, message = 409, "CONFLICT", "The request conflicts with the current state."


class ContactLinkExpired(ThunaiError):
    status_code, code = 410, "CONTACT_LINK_EXPIRED"
    message = "This link has expired or was already used."


class PayloadTooLarge(ThunaiError):
    status_code, code, message = 413, "PAYLOAD_TOO_LARGE", "The request body is too large."


class ValidationFailed(ThunaiError):
    status_code, code, message = 422, "VALIDATION_ERROR", "The request is invalid."


class InsufficientBalance(ThunaiError):
    status_code, code = 422, "INSUFFICIENT_BALANCE"
    message = "The amount is more than the available balance."


class NoteRequired(ThunaiError):
    status_code, code, message = 422, "NOTE_REQUIRED", "A note of 10–1000 characters is required."


class RateLimited(ThunaiError):
    status_code, code, message = 429, "RATE_LIMITED", "Too many requests. Try again later."

    def __init__(self, retry_after_seconds: int, **kwargs: Any) -> None:
        super().__init__(headers={"Retry-After": str(max(1, retry_after_seconds))}, **kwargs)


class AssessmentUnavailable(ThunaiError):
    status_code, code = 503, "ASSESSMENT_UNAVAILABLE"
    message = "The risk assessment could not be completed. Do not execute the transfer."


class DependencyUnavailable(ThunaiError):
    status_code, code = 503, "DEPENDENCY_UNAVAILABLE"
    message = "A required service is unavailable."


_HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    429: "RATE_LIMITED",
}


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": current_request_id(),
        }
    }


def error_response(
    status: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(error_body(code, message, details), status_code=status, headers=headers)


async def _thunai_error(_: Request, exc: Exception) -> JSONResponse:
    exc = cast(ThunaiError, exc)
    if exc.status_code >= 500:
        logger.warning("request.failed", extra={"code": exc.code, "status": exc.status_code})
    return error_response(exc.status_code, exc.code, exc.message, exc.details, exc.headers)


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    exc = cast(RequestValidationError, exc)
    # Never echo the submitted input back (it may hold personal data).
    fields = [
        {"loc": [str(p) for p in err.get("loc", ())], "msg": str(err.get("msg", "invalid"))}
        for err in exc.errors()
    ]
    return error_response(422, "VALIDATION_ERROR", "The request is invalid.", {"fields": fields})


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    exc = cast(StarletteHTTPException, exc)
    code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
    message = "Not found." if exc.status_code == 404 else str(exc.detail)
    return error_response(exc.status_code, code, message, headers=dict(exc.headers or {}))


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ThunaiError, _thunai_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
