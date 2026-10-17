"""Staff, customers, accounts, payees, trusted contacts and consents (DATABASE_SCHEMA §3.1–3.6)."""

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import (
    AccountStatus,
    AccountType,
    Channel,
    ConsentType,
    Language,
    Role,
    TrustedContactStatus,
)
from app.models.base import Base, StrEnumType, created_at_column, enum_check, uuid_pk


class StaffUser(Base):
    __tablename__ = "staff_users"
    __table_args__ = (
        CheckConstraint("role IN ('TELLER', 'OFFICER', 'ADMIN')", name="role_valid"),
        CheckConstraint("username ~ '^[a-z0-9_.]{3,32}$'", name="username_format"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str]
    role: Mapped[Role] = mapped_column(StrEnumType(Role, 16))
    display_name: Mapped[str]
    branch_code: Mapped[str]
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime] = created_at_column()


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (enum_check("preferred_language", Language),)

    id: Mapped[uuid.UUID] = uuid_pk()
    external_ref: Mapped[str] = mapped_column(unique=True)
    display_name: Mapped[str]
    preferred_language: Mapped[Language] = mapped_column(
        StrEnumType(Language, 2), server_default="en"
    )
    branch_code: Mapped[str]
    login_username: Mapped[str | None] = mapped_column(unique=True)
    login_password_hash: Mapped[str | None]
    is_synthetic: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime]

    accounts: Mapped[list["Account"]] = relationship(back_populates="customer", lazy="raise")
    payees: Mapped[list["Payee"]] = relationship(back_populates="customer", lazy="raise")


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        enum_check("account_type", AccountType),
        enum_check("status", AccountStatus),
        CheckConstraint("balance_paise >= 0", name="balance_non_negative"),
        CheckConstraint(
            "account_type NOT IN ('FD', 'RD') OR maturity_date IS NOT NULL",
            name="maturity_for_deposits",
        ),
        UniqueConstraint("customer_id", "masked_number"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    account_type: Mapped[AccountType] = mapped_column(StrEnumType(AccountType, 8))
    masked_number: Mapped[str]
    balance_paise: Mapped[int]
    opened_at: Mapped[datetime]
    maturity_date: Mapped[date | None]
    status: Mapped[AccountStatus] = mapped_column(StrEnumType(AccountStatus, 8))

    customer: Mapped[Customer] = relationship(back_populates="accounts", lazy="raise")


class Payee(Base):
    __tablename__ = "payees"
    __table_args__ = (
        UniqueConstraint("customer_id", "payee_ref"),
        CheckConstraint("ifsc ~ '^[A-Z]{4}0[A-Z0-9]{6}$'", name="ifsc_format"),
        enum_check("added_channel", Channel),
        Index("ix_payees_customer_added_at", "customer_id", text("added_at DESC")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"))
    payee_ref: Mapped[str]
    display_name: Mapped[str]
    bank_name: Mapped[str]
    ifsc: Mapped[str] = mapped_column(String(11))
    masked_account: Mapped[str]
    linked_msisdn_hmac: Mapped[str | None]
    linked_msisdn_last4: Mapped[str | None] = mapped_column(String(4))
    added_at: Mapped[datetime]
    added_channel: Mapped[Channel] = mapped_column(StrEnumType(Channel, 16))

    customer: Mapped[Customer] = relationship(back_populates="payees", lazy="raise")


class TrustedContact(Base):
    __tablename__ = "trusted_contacts"
    __table_args__ = (
        enum_check("preferred_language", Language),
        enum_check("status", TrustedContactStatus),
        CheckConstraint("char_length(relationship) <= 40", name="relationship_length"),
        Index(
            "uq_trusted_contacts_one_active",
            "customer_id",
            unique=True,
            postgresql_where=text("status <> 'REVOKED'"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"))
    display_name: Mapped[str]
    relationship: Mapped[str]
    phone_ciphertext: Mapped[str]
    phone_last4: Mapped[str] = mapped_column(String(4))
    telegram_chat_id_ciphertext: Mapped[str | None]
    preferred_language: Mapped[Language] = mapped_column(StrEnumType(Language, 2))
    registered_at: Mapped[datetime]
    effective_from: Mapped[datetime]
    status: Mapped[TrustedContactStatus] = mapped_column(StrEnumType(TrustedContactStatus, 24))


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (
        enum_check("consent_type", ConsentType),
        Index("ix_consents_latest", "customer_id", "consent_type", text("recorded_at DESC")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"))
    consent_type: Mapped[ConsentType] = mapped_column(StrEnumType(ConsentType, 32))
    granted: Mapped[bool]
    text_version: Mapped[str]
    recorded_at: Mapped[datetime]
