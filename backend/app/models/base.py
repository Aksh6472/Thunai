"""Declarative base and column helpers (DATABASE_SCHEMA §1)."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, TypeVar

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Dialect,
    MetaData,
    String,
    TypeDecorator,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        datetime: DateTime(timezone=True),
        dict[str, Any]: JSONB,
        list[Any]: JSONB,
        uuid.UUID: Uuid,
    }


E = TypeVar("E", bound=StrEnum)


class StrEnumType(TypeDecorator[E]):
    """Stored as TEXT (with a CHECK), loaded back as the StrEnum member."""

    impl = String
    cache_ok = True

    def __init__(self, enum_cls: type[E], length: int = 32) -> None:
        super().__init__(length)
        self.enum_cls = enum_cls

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        return None if value is None else self.enum_cls(value).value

    def process_result_value(self, value: Any, dialect: Dialect) -> E | None:
        return None if value is None else self.enum_cls(value)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def created_at_column() -> Mapped[datetime]:
    """Wall-clock creation time (ARCHITECTURE §4.7)."""
    return mapped_column(server_default=func.now())


def enum_check(column: str, enum: type[StrEnum], *, nullable: bool = False) -> CheckConstraint:
    values = ", ".join(f"'{member.value}'" for member in enum)
    condition = f"{column} IN ({values})"
    if nullable:
        condition = f"{column} IS NULL OR {condition}"
    return CheckConstraint(condition, name=f"{column}_valid")
