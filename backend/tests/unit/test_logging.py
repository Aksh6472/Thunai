"""T-005: log masking (SECURITY.md §6) and JSON format."""

import json
import logging

from app.core.logging import JsonFormatter, MaskingFilter, mask_text, set_request_id


def _render(record: logging.LogRecord) -> dict[str, object]:
    MaskingFilter().filter(record)
    parsed: dict[str, object] = json.loads(JsonFormatter().format(record))
    return parsed


def _record(msg: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("t", logging.INFO, __file__, 1, msg, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_phone_numbers_are_masked() -> None:
    assert mask_text("call +919800000193 now") == "call *********0193 now"
    assert mask_text("acct 123456789012") == "acct ********9012"


def test_contact_tokens_in_paths_are_masked() -> None:
    assert (
        mask_text("GET /trusted/AbCdEf123456_-xyz/response") == "GET /trusted/[REDACTED]/response"
    )
    assert mask_text("http://x/t/AbCdEf123456_-xyz") == "http://x/t/[REDACTED]"


def test_bearer_tokens_are_masked() -> None:
    assert "eyJhbGci" not in mask_text("Authorization: Bearer eyJhbGciOi.payload.sig")


def test_sensitive_extra_keys_are_redacted() -> None:
    out = _render(_record("x", token="abc", phone_e164="+919800000193", note="+919800000193"))
    assert out["token"] == "[REDACTED]"
    assert out["phone_e164"] == "[REDACTED]"
    assert out["note"] == "*********0193"


def test_json_line_carries_request_id() -> None:
    set_request_id("req_test123456")
    out = _render(_record("assessment.created", tier="VERY_HIGH"))
    assert out["request_id"] == "req_test123456"
    assert out["message"] == "assessment.created"
    assert out["tier"] == "VERY_HIGH"
