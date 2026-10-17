"""Structured JSON logging with a request id and a PII-masking filter (SECURITY.md §6, §9).

The masking filter is a backstop. Code must still never log tokens, phones or account numbers.
"""

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

_PHONE = re.compile(r"\+?\d{10,}")
_TRUSTED_PATH = re.compile(r"(/(?:t|trusted)/)[A-Za-z0-9_\-]{8,}")
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+")
_SENSITIVE_KEYS = re.compile(r"(?i)(token|password|secret|api_key|authorization|phone|msisdn)")

_STD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()) | {
    "message",
    "asctime",
}


def current_request_id() -> str | None:
    return _request_id.get()


def set_request_id(value: str | None) -> Any:
    return _request_id.set(value)


def reset_request_id(token: Any) -> None:
    _request_id.reset(token)


def mask_text(text: str) -> str:
    text = _TRUSTED_PATH.sub(r"\1[REDACTED]", text)
    text = _BEARER.sub(r"\1[REDACTED]", text)
    return _PHONE.sub(_mask_digits, text)


def _mask_digits(match: re.Match[str]) -> str:
    value = match.group(0)
    return "*" * (len(value) - 4) + value[-4:]


def mask_value(key: str, value: Any) -> Any:
    if _SENSITIVE_KEYS.search(key) and value is not None:
        return "[REDACTED]"
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, dict):
        return {k: mask_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [mask_value(key, v) for v in value]
    return value


class MaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_text(record.getMessage())
        record.args = None
        for key, value in list(record.__dict__.items()):
            if key not in _STD_ATTRS:
                record.__dict__[key] = mask_value(key, value)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": current_request_id(),
        }
        for key, value in record.__dict__.items():
            if key not in _STD_ATTRS and key not in entry:
                entry[key] = value
        if record.exc_info:
            entry["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            entry["exc"] = mask_text(self.formatException(record.exc_info))
        return json.dumps(entry, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(MaskingFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    logging.getLogger("uvicorn.access").disabled = True  # replaced by our request log
