"""Seed the DB with synthetic, fictional data (T-009, T-022). Idempotent: truncate, then insert.

    uv run python -m sim.seed --seed 42

May import app.models, app.core.settings, app.core.security and app.db (CLAUDE.md §6): direct
inserts are much faster than replaying history through the API.
"""

import argparse
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import encrypt_pii, hash_password, hmac_msisdn
from app.core.settings import Settings, get_settings
from app.db import make_engine, make_session_factory
from app.models import (
    Account,
    AccountEvent,
    Base,
    Consent,
    Customer,
    FriMockRating,
    Payee,
    SimState,
    StaffUser,
    Transfer,
    TrustedContact,
)
from sim.generator import BASE, BRANCH, GeneratedCustomer, generate
from sim.scenarios.schema import GOLDEN_SEED, Scenario, load_all

logger = logging.getLogger(__name__)

STAFF = [
    ("teller.priya", "TELLER", "Priya (fictional)"),
    ("officer.rao", "OFFICER", "Mr. Rao (fictional)"),
    ("admin.demo", "ADMIN", "Demo Admin (fictional)"),
]
HERO_REF = "CUST-0007"


@dataclass(frozen=True)
class SeedSummary:
    seed: int
    customers: int
    events: int
    transfers: int
    seconds: float


def truncate_all(session: Session) -> None:
    tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


def seed(
    session: Session,
    settings: Settings,
    seed_value: int = GOLDEN_SEED,
    *,
    scenarios: dict[str, Scenario] | None = None,
    n_customers: int = 50,
) -> SeedSummary:
    started = time.perf_counter()
    if not settings.seed_password:
        raise RuntimeError("THUNAI_SEED_PASSWORD is required to seed demo logins")
    scenarios = scenarios or load_all()
    truncate_all(session)
    password_hash = hash_password(settings.seed_password)  # one hash, reused (argon2 is slow)
    for username, role, name in STAFF:
        session.add(
            StaffUser(
                username=username,
                password_hash=password_hash,
                role=role,
                display_name=name,
                branch_code=BRANCH,
            )
        )
    population = generate(seed_value, scenarios, n_customers=n_customers)
    events = transfers = 0
    for generated in population:
        e, t = _insert_customer(session, settings, generated, password_hash)
        events, transfers = events + e, transfers + t
    for scenario in scenarios.values():
        for fri in scenario.fri:
            session.merge(
                FriMockRating(
                    msisdn_hmac=hmac_msisdn(fri.msisdn, settings),
                    rating=fri.rating,
                    updated_at=BASE,
                )
            )
    session.add(SimState(id=1, sim_now=BASE, speed=0.0, running_scenario=None, updated_at=BASE))
    session.commit()
    summary = SeedSummary(
        seed=seed_value,
        customers=len(population),
        events=events,
        transfers=transfers,
        seconds=round(time.perf_counter() - started, 2),
    )
    logger.info("seed.done", extra=summary.__dict__)
    return summary


def _insert_customer(
    session: Session, settings: Settings, generated: GeneratedCustomer, password_hash: str
) -> tuple[int, int]:
    spec = generated.spec
    opened = BASE - timedelta(days=spec.history_days)
    customer = Customer(
        external_ref=spec.ref,
        display_name=spec.display_name,
        preferred_language=spec.language,
        branch_code=BRANCH,
        login_username=spec.login,
        login_password_hash=password_hash if spec.login else None,
        created_at=opened,
    )
    session.add(customer)
    session.flush()
    accounts: dict[str, Account] = {}
    for a in spec.accounts:
        account = Account(
            customer_id=customer.id,
            account_type=a.type,
            masked_number=a.masked,
            balance_paise=a.balance_rupees * 100,
            opened_at=opened,
            maturity_date=a.maturity,
            status="ACTIVE",
        )
        session.add(account)
        accounts[a.masked] = account
    payees: dict[str, Payee] = {}
    for p in spec.payees:
        payee = Payee(
            customer_id=customer.id,
            payee_ref=p.ref,
            display_name=p.name,
            bank_name="Example Bank",
            ifsc=p.ifsc,
            masked_account=p.masked_account,
            added_at=BASE - timedelta(days=p.age_days),
            added_channel="NETBANKING",
        )
        session.add(payee)
        payees[p.ref] = payee
    session.flush()
    _insert_contact(session, settings, customer, spec)
    for consent in spec.consents:
        session.add(
            Consent(
                customer_id=customer.id,
                consent_type=consent,
                granted=True,
                text_version=f"{consent.lower()}_v1",
                recorded_at=BASE - timedelta(days=300),
            )
        )
    events = transfers = 0
    for i, item in enumerate(generated.history):
        account = accounts[item.account]
        ref = f"HIST-{spec.ref}-{i:04d}"
        if item.kind == "PAYEE_TRANSFER":
            session.add(
                Transfer(
                    transfer_ref=ref,
                    customer_id=customer.id,
                    from_account_id=account.id,
                    payee_id=payees[item.payee_ref or ""].id,
                    amount_paise=item.amount_paise,
                    rail="NEFT",
                    channel="NETBANKING",
                    status="EXECUTED",
                    initiated_at=item.at,
                    decided_at=item.at,
                    executed_at=item.at,
                    request_hash="seed",
                )
            )
            transfers += 1
            continue
        payload: dict[str, object] = {"counterparty": "Routine (fictional)"}
        if item.kind == "FD_CLOSED":
            payload = {
                "maturity_date": item.maturity.isoformat() if item.maturity else None,
                "proceeds_to_account": item.account,
            }
        session.add(
            AccountEvent(
                event_id=ref,
                customer_id=customer.id,
                account_id=account.id,
                event_type=item.kind,
                amount_paise=item.amount_paise,
                occurred_at=item.at,
                payload=payload,
                request_hash="seed",
            )
        )
        events += 1
    return events, transfers


def _insert_contact(session: Session, settings: Settings, customer: Customer, spec: object) -> None:
    contact = getattr(spec, "trusted_contact", None)
    if contact is None:
        return
    phone, chat = contact.phone, None
    if customer.external_ref == HERO_REF:
        # Demo only: the teammate playing "Arun" (local .env; never committed).
        phone = settings.demo_contact_phone_e164 or phone
        chat = settings.demo_contact_telegram_chat_id
    registered: datetime = BASE - timedelta(days=contact.age_days)
    effective = registered + timedelta(hours=settings.trusted_contact_activation_hours)
    session.add(
        TrustedContact(
            customer_id=customer.id,
            display_name=contact.name,
            relationship=contact.relationship,
            phone_ciphertext=encrypt_pii(phone, settings),
            phone_last4=phone[-4:],
            telegram_chat_id_ciphertext=encrypt_pii(chat, settings) if chat else None,
            preferred_language=contact.language,
            registered_at=registered,
            effective_from=effective,
            status="ACTIVE" if effective <= BASE else "PENDING_ACTIVATION",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic demo data (truncates first).")
    parser.add_argument("--seed", type=int, default=GOLDEN_SEED)
    parser.add_argument("--customers", type=int, default=50)
    args = parser.parse_args()
    settings = get_settings()
    engine = make_engine(settings.database_url)
    with make_session_factory(engine)() as session:
        summary = seed(session, settings, args.seed, n_customers=args.customers)
    print(  # noqa: T201 (CLI output)
        f"Seeded {summary.customers} synthetic customers, {summary.events} events, "
        f"{summary.transfers} historical transfers (seed {summary.seed}) in {summary.seconds}s"
    )


if __name__ == "__main__":
    main()
