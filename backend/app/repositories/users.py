"""Staff and customer-login lookups."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, StaffUser


def staff_by_username(session: Session, username: str) -> StaffUser | None:
    return session.scalar(
        select(StaffUser).where(func.lower(StaffUser.username) == username.lower())
    )


def customer_by_login(session: Session, username: str) -> Customer | None:
    return session.scalar(
        select(Customer).where(func.lower(Customer.login_username) == username.lower())
    )


def staff_by_id(session: Session, user_id: uuid.UUID) -> StaffUser | None:
    return session.get(StaffUser, user_id)


def customer_by_id(session: Session, customer_id: uuid.UUID) -> Customer | None:
    return session.get(Customer, customer_id)
