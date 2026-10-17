"""API-level helpers for integration tests: auth headers, HIGH-hold world, console links."""

import re
from datetime import UTC, date, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.core.settings import Settings
from app.domain.enums import AccountType, Language, Role, TransferStatus
from app.models import Customer, Payee, StaffUser, Transfer
from tests.db_factories import (
    LONG_AGO,
    hero_world,
    make_account,
    make_baseline,
    make_contact,
    make_customer,
    make_payee,
    make_staff,
)
from tests.hero_api import HERO_TRANSFER, replay_hero_until_transfer

TEST_NOW = datetime(2026, 10, 3, 5, 50, tzinfo=UTC)  # matches conftest (11:20 IST, hero day 3)


def bearer(settings: Settings, user_id: str, role: Role, branch: str = "CHN001") -> dict[str, str]:
    token, _ = create_access_token(
        user_id=user_id, role=role, branch_code=branch, settings=settings, now=datetime.now(UTC)
    )
    return {"Authorization": f"Bearer {token}"}


def staff_headers(
    db: Session, settings: Settings, username: str, role: Role, branch: str = "CHN001"
) -> dict[str, str]:
    user: StaffUser = make_staff(db, username, role, branch=branch)
    return bearer(settings, str(user.id), role, branch)


def customer_headers(settings: Settings, customer: Customer) -> dict[str, str]:
    return bearer(settings, str(customer.id), Role.CUSTOMER, customer.branch_code)


async def hero_hold(
    client: httpx.AsyncClient, db: Session, settings: Settings, headers: dict[str, str]
) -> dict:  # type: ignore[type-arg]
    hero_world(db, settings)
    await replay_hero_until_transfer(client, headers)
    r = await client.post("/api/v1/transfers/assess", json=HERO_TRANSFER, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def wedding_world(
    db: Session, settings: Settings, *, contact_registered_at: datetime = LONG_AGO
) -> Customer:
    """N4-like: a HIGH (60) case. FD broken, funds pooled, new jeweller payee, ₹8 L."""
    customer = make_customer(db, "CUST-0021", login="cust.meena", language=Language.EN)
    customer.display_name = "Meena (fictional)"
    make_account(db, customer, "XXXXXX5501", 5_00_000)
    make_account(db, customer, "XXXXXX5502", 4_00_000)
    make_account(db, customer, "XXXXXX5509", 6_00_000, AccountType.FD, date(2027, 6, 1))
    make_baseline(db, customer, 60_000)
    make_contact(db, customer, settings, registered_at=contact_registered_at)
    return customer


WEDDING_EVENTS = [
    {
        "event_id": "EVT-N4-FD",
        "customer_ref": "CUST-0021",
        "event_type": "FD_CLOSED",
        "occurred_at": "2026-10-01T10:00:00+05:30",
        "account_ref": "XXXXXX5509",
        "amount_paise": 60000000,
        "payload": {"maturity_date": "2027-06-01", "proceeds_to_account": "XXXXXX5501"},
    },
    {
        "event_id": "EVT-N4-POOL",
        "customer_ref": "CUST-0021",
        "event_type": "INTERNAL_TRANSFER_IN",
        "occurred_at": "2026-10-02T10:00:00+05:30",
        "account_ref": "XXXXXX5501",
        "amount_paise": 40000000,
        "payload": {"from_account": "XXXXXX5502", "to_account": "XXXXXX5501"},
    },
    {
        "event_id": "EVT-N4-PAYEE",
        "customer_ref": "CUST-0021",
        "event_type": "PAYEE_ADDED",
        "occurred_at": "2026-10-02T15:20:00+05:30",
        "payload": {
            "payee_ref": "PAY-0021-05",
            "display_name": "Jeweller (fictional)",
            "bank_name": "Example Bank",
            "ifsc": "EXMP0004321",
            "masked_account": "XXXXXX7788",
            "channel": "APP",
        },
    },
]
WEDDING_TRANSFER = {
    "transfer_ref": "TRF-N4-0001",
    "customer_ref": "CUST-0021",
    "from_account": "XXXXXX5501",
    "payee_ref": "PAY-0021-05",
    "amount_paise": 80000000,
    "rail": "NEFT",
    "channel": "APP",
    "initiated_at": "2026-10-03T11:20:00+05:30",
}


async def wedding_hold(
    client: httpx.AsyncClient,
    db: Session,
    settings: Settings,
    headers: dict[str, str],
    *,
    contact_registered_at: datetime = LONG_AGO,
) -> dict:  # type: ignore[type-arg]
    wedding_world(db, settings, contact_registered_at=contact_registered_at)
    for event in WEDDING_EVENTS:
        r = await client.post("/api/v1/events", json=event, headers=headers)
        assert r.status_code == 202, r.text
    r = await client.post("/api/v1/transfers/assess", json=WEDDING_TRANSFER, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def latest_link_token(app: FastAPI) -> str:
    messages = app.state.console_notifier.messages(1)
    assert messages, "no console message was sent"
    match = re.search(r"/t/([A-Za-z0-9_\-]+)", messages[0].link)
    assert match
    return match.group(1)


def executed_transfer(
    db: Session,
    customer: Customer,
    payee: Payee,
    account_masked: str,
    amount_rupees: int,
    at: datetime,
) -> Transfer:
    from app.repositories import customers

    account = customers.account_by_masked(db, customer.id, account_masked)
    assert account is not None
    transfer = Transfer(
        transfer_ref=f"HIST-{payee.payee_ref}-{at:%Y%m%d}",
        customer_id=customer.id,
        from_account_id=account.id,
        payee_id=payee.id,
        amount_paise=amount_rupees * 100,
        rail="RTGS",
        channel="NETBANKING",
        status=TransferStatus.EXECUTED,
        initiated_at=at,
        decided_at=at,
        executed_at=at,
        request_hash="seed",
    )
    db.add(transfer)
    db.flush()
    return transfer


def iqbal_world(db: Session) -> Customer:
    """N1: Mr. Iqbal (fictional), builder paid ₹5 L quarterly for 2 years."""
    customer = make_customer(db, "CUST-0012", login="cust.iqbal")
    customer.display_name = "Mr. Iqbal (fictional)"
    make_account(db, customer, "XXXXXX1201", 5_00_000)
    make_account(db, customer, "XXXXXX1202", 5_00_000)
    make_account(db, customer, "XXXXXX1209", 30_00_000, AccountType.FD, date(2027, 2, 1))
    make_baseline(db, customer, 5_00_000)
    builder = make_payee(db, customer, "PAY-0012-01", TEST_NOW - timedelta(days=730))
    for quarter in range(8):
        executed_transfer(
            db,
            customer,
            builder,
            "XXXXXX1201",
            5_00_000,
            TEST_NOW - timedelta(days=90 * (quarter + 1)),
        )
    return customer


IQBAL_EVENTS = [
    {
        "event_id": "EVT-N1-FD",
        "customer_ref": "CUST-0012",
        "event_type": "FD_CLOSED",
        "occurred_at": "2026-10-01T10:00:00+05:30",
        "account_ref": "XXXXXX1209",
        "amount_paise": 300000000,
        "payload": {"maturity_date": "2027-02-01", "proceeds_to_account": "XXXXXX1201"},
    },
    {
        "event_id": "EVT-N1-POOL",
        "customer_ref": "CUST-0012",
        "event_type": "INTERNAL_TRANSFER_IN",
        "occurred_at": "2026-10-02T10:00:00+05:30",
        "account_ref": "XXXXXX1201",
        "amount_paise": 50000000,
        "payload": {"from_account": "XXXXXX1202", "to_account": "XXXXXX1201"},
    },
]
IQBAL_TRANSFER = {
    "transfer_ref": "TRF-N1-0001",
    "customer_ref": "CUST-0012",
    "from_account": "XXXXXX1201",
    "payee_ref": "PAY-0012-01",
    "amount_paise": 400000000,
    "rail": "RTGS",
    "channel": "NETBANKING",
    "initiated_at": "2026-10-03T11:20:00+05:30",
    "scenario_label": "N1",
}
