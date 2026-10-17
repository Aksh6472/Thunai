"""T-020: audit rows are written, scrubbed, and never updated or deleted (FR-20)."""

import ast
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import set_request_id
from app.domain.enums import ActorType
from app.models import AuditLog
from app.services.audit_service import audit, scrub

APP = Path(__file__).resolve().parents[2] / "app"


def test_audit_writes_one_row_with_request_id(db: Session) -> None:
    set_request_id("req_audit_test_1")
    audit(
        db,
        "HOLD_RELEASED",
        entity_type="hold",
        entity_id="h1",
        actor_type=ActorType.STAFF,
        actor_id="officer-1",
        details={"note_length": 42},
    )
    db.flush()
    row = db.scalars(select(AuditLog).where(AuditLog.entity_id == "h1")).one()
    assert (row.action, row.request_id, row.details) == (
        "HOLD_RELEASED",
        "req_audit_test_1",
        {"note_length": 42},
    )


def test_scrub_drops_secrets_and_masks_numbers() -> None:
    cleaned = scrub(
        {
            "token": "abc",
            "phone_e164": "+919800000193",
            "nested": {"password": "x", "note": "call +919800000193"},
            "items": ["ok"],
        }
    )
    assert cleaned == {"nested": {"note": "call *********0193"}, "items": ["ok"]}


def test_no_update_or_delete_path_for_audit_log() -> None:
    """Append-only: no code updates or deletes AuditLog rows."""
    for path in APP.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "AuditLog" not in source and "audit_log" not in source:
            continue
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                args = ast.dump(node)
                if name in {"update", "delete"} and "AuditLog" in args:
                    raise AssertionError(f"{path.name} updates/deletes AuditLog")
        lowered = source.lower()
        assert "update audit_log" not in lowered and "delete from audit_log" not in lowered, (
            path.name
        )
