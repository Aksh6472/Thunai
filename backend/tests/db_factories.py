"""DB row builders for integration tests. All data fictional."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domain.enums import Language, Role
from app.models import Customer, StaffUser

PASSWORD = "correct-horse-battery"
_HASH = hash_password(PASSWORD)  # hashing is slow by design; reuse one hash


def make_staff(
    db: Session,
    username: str,
    role: Role = Role.TELLER,
    *,
    branch: str = "CHN001",
    active: bool = True,
) -> StaffUser:
    user = StaffUser(
        username=username,
        password_hash=_HASH,
        role=role,
        display_name=f"{username.split('.')[-1].title()} (fictional)",
        branch_code=branch,
        is_active=active,
    )
    db.add(user)
    db.flush()
    return user


def make_customer(
    db: Session,
    ref: str | None = None,
    *,
    login: str | None = None,
    language: Language = Language.EN,
    branch: str = "CHN001",
) -> Customer:
    customer = Customer(
        external_ref=ref or f"CUST-{uuid.uuid4().hex[:6].upper()}",
        display_name="Test Customer (fictional)",
        preferred_language=language,
        branch_code=branch,
        login_username=login,
        login_password_hash=_HASH if login else None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    db.add(customer)
    db.flush()
    return customer
