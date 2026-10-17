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


# ---------- Hero world ----------

from dataclasses import dataclass  # noqa: E402
from datetime import date, timedelta  # noqa: E402

from app.core.security import encrypt_pii, hmac_msisdn  # noqa: E402
from app.core.settings import Settings  # noqa: E402
from app.domain.enums import (  # noqa: E402
    AccountStatus,
    AccountType,
    BaselineConfidence,
    Channel,
    ConsentType,
    FriRating,
    TrustedContactStatus,
)
from app.models import (  # noqa: E402
    Account,
    Consent,
    CustomerBaseline,
    FriMockRating,
    Payee,
    TrustedContact,
)

LONG_AGO = datetime(2026, 3, 1, tzinfo=UTC)


def make_account(
    db: Session,
    customer: Customer,
    masked: str,
    balance_rupees: int,
    kind: AccountType = AccountType.SAVINGS,
    maturity: date | None = None,
) -> Account:
    account = Account(
        customer_id=customer.id,
        account_type=kind,
        masked_number=masked,
        balance_paise=balance_rupees * 100,
        opened_at=LONG_AGO,
        maturity_date=maturity,
        status=AccountStatus.ACTIVE,
    )
    db.add(account)
    db.flush()
    return account


def make_payee(
    db: Session,
    customer: Customer,
    ref: str,
    added_at: datetime = LONG_AGO,
    *,
    msisdn_hmac: str | None = None,
    last4: str | None = None,
) -> Payee:
    payee = Payee(
        customer_id=customer.id,
        payee_ref=ref,
        display_name=f"{ref} (fictional)",
        bank_name="Example Bank",
        ifsc="EXMP0001234",
        masked_account="XXXXXX4821",
        linked_msisdn_hmac=msisdn_hmac,
        linked_msisdn_last4=last4,
        added_at=added_at,
        added_channel=Channel.APP,
    )
    db.add(payee)
    db.flush()
    return payee


def make_baseline(db: Session, customer: Customer, median_rupees: int) -> CustomerBaseline:
    row = CustomerBaseline(
        customer_id=customer.id,
        computed_at=LONG_AGO,
        history_days=180,
        median_outbound_paise=median_rupees * 100,
        p95_outbound_paise=median_rupees * 300,
        qualifying_transfer_count=24,
        premature_fd_closures_365d=0,
        confidence=BaselineConfidence.OK,
        algorithm_version="baseline_v1",
    )
    db.add(row)
    db.flush()
    return row


def grant_consent(db: Session, customer: Customer, kind: ConsentType, granted: bool = True) -> None:
    db.add(
        Consent(
            customer_id=customer.id,
            consent_type=kind,
            granted=granted,
            text_version=f"{kind.value.lower()}_v1",
            recorded_at=LONG_AGO,
        )
    )
    db.flush()


def make_contact(
    db: Session,
    customer: Customer,
    settings: Settings,
    *,
    registered_at: datetime = LONG_AGO,
    activation_hours: int = 72,
    phone: str = "+919800000101",
) -> TrustedContact:
    contact = TrustedContact(
        customer_id=customer.id,
        display_name="Arun",
        relationship="son",
        phone_ciphertext=encrypt_pii(phone, settings),
        phone_last4=phone[-4:],
        preferred_language=Language.TA,
        registered_at=registered_at,
        effective_from=registered_at + timedelta(hours=activation_hours),
        status=TrustedContactStatus.PENDING_ACTIVATION,
    )
    db.add(contact)
    db.flush()
    return contact


def set_fri(db: Session, settings: Settings, msisdn: str, rating: FriRating) -> None:
    db.merge(
        FriMockRating(msisdn_hmac=hmac_msisdn(msisdn, settings), rating=rating, updated_at=LONG_AGO)
    )
    db.flush()


@dataclass
class HeroWorld:
    customer: Customer
    savings: Account
    fd: Account
    contact: TrustedContact


def hero_world(db: Session, settings: Settings, *, with_contact: bool = True) -> HeroWorld:
    """R. Kamala (fictional), CUST-0007: the P1 starting state."""
    customer = make_customer(db, "CUST-0007", login="cust.kamala", language=Language.TA)
    customer.display_name = "R. Kamala (fictional)"
    savings = make_account(db, customer, "XXXXXX2201", 1_00_000)
    fd = make_account(db, customer, "XXXXXX7710", 35_00_000, AccountType.FD, date(2027, 4, 1))
    make_account(db, customer, "XXXXXX3302", 6_00_000)
    make_account(db, customer, "XXXXXX4403", 5_00_000)
    make_baseline(db, customer, 40_000)
    grant_consent(db, customer, ConsentType.CALL_SIGNAL)
    grant_consent(db, customer, ConsentType.TRUSTED_CONTACT_SHARING)
    contact = make_contact(db, customer, settings) if with_contact else None
    set_fri(db, settings, "+919800000193", FriRating.HIGH)
    return HeroWorld(customer, savings, fd, contact)  # type: ignore[arg-type]
