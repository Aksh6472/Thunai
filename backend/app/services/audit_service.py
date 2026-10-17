"""Append-only audit writer (FR-20, SECURITY §9).

Rows are added in the caller's transaction. There is deliberately no update or delete function.
"""

import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import current_request_id, mask_text
from app.domain.enums import ActorType
from app.models import AuditLog

_DENY_KEYS = re.compile(r"(?i)(token|password|secret|phone|msisdn|api_key|authorization)")


def scrub(details: Any) -> Any:
    """Drop secret-looking keys and mask phone-like numbers in values."""
    if isinstance(details, dict):
        return {str(k): scrub(v) for k, v in details.items() if not _DENY_KEYS.search(str(k))}
    if isinstance(details, list | tuple):
        return [scrub(v) for v in details]
    if isinstance(details, str):
        return mask_text(details)
    return details


def audit(
    session: Session,
    action: str,
    *,
    entity_type: str,
    entity_id: object,
    actor_type: ActorType,
    actor_id: object | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    row = AuditLog(
        actor_type=actor_type,
        actor_id=str(actor_id) if actor_id is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        request_id=current_request_id(),
        details=scrub(details or {}),
    )
    session.add(row)
    return row
