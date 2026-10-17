"""Synthetic customers and history (FR-01, T-022). Deterministic: random.Random(seed) only.

Scenario customers come from sim/scenarios/*.yaml; the rest of the 50 are background customers.
Each customer's routine debits are built so that the baseline median equals the intended value.
"""

import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sim.names import FIRST_NAMES, INITIALS, PAYEE_NAMES, fictional
from sim.scenarios.schema import (
    GOLDEN_SEED,
    AccountSpec,
    ContactSpec,
    CustomerSpec,
    PayeeHistorySpec,
    Scenario,
)

IST = timezone(timedelta(hours=5, minutes=30))
DAY1 = date(2026, 10, 1)
BASE = datetime(2026, 10, 1, 9, 0, tzinfo=IST)  # demo clock after reset: day 1, 09:00 IST
BRANCH = "CHN001"
# History avoids the 150–200 day band, so the 180-day baseline window holds the same items for
# any assessment made within ~20 simulated days of BASE.
QUALIFYING_WINDOW_DAYS = 150
EXCLUDED_BAND_DAYS = (150, 200)


@dataclass(frozen=True)
class Params:
    amount_scale: float
    gap_scale: float
    history_days: int


def scenario_params(scenario: Scenario, seed: int) -> Params:
    """Seed 42 replays exactly (golden); other seeds randomise per AI_DESIGN §7.2."""
    if seed == GOLDEN_SEED:
        return Params(1.0, 1.0, scenario.customer.history_days)
    rng = random.Random(f"{seed}:{scenario.id}:params")
    r = scenario.randomise
    return Params(
        amount_scale=round(rng.uniform(*r.amount_scale), 3),
        gap_scale=round(rng.uniform(*r.gap_scale), 3),
        history_days=rng.randint(*r.history_days),
    )


@dataclass
class HistoryItem:
    at: datetime
    kind: str  # ROUTINE_DEBIT | ROUTINE_CREDIT | FD_CLOSED | PAYEE_TRANSFER
    amount_paise: int
    account: str
    payee_ref: str | None = None
    maturity: date | None = None


@dataclass
class GeneratedCustomer:
    spec: CustomerSpec
    history: list[HistoryItem] = field(default_factory=list)


def _scaled_accounts(spec: CustomerSpec, scale: float) -> list[AccountSpec]:
    if scale == 1.0:
        return spec.accounts
    return [
        a.model_copy(update={"balance_rupees": round(a.balance_rupees * scale)})
        for a in spec.accounts
    ]


def build_history(spec: CustomerSpec, rng: random.Random, history_days: int) -> list[HistoryItem]:
    opened = BASE - timedelta(days=history_days)
    main = next(
        (a.masked for a in spec.accounts if a.type in ("SAVINGS", "CURRENT")),
        spec.accounts[0].masked,
    )
    items: list[HistoryItem] = []
    median = spec.median_outbound_rupees * 100

    for payee in spec.payees:
        span = min(payee.age_days, history_days)
        for i in range(payee.transfers):
            days_ago = span * (i + 1) / (payee.transfers + 1)
            low, high = EXCLUDED_BAND_DAYS
            if low <= days_ago <= high:
                days_ago = low - 1 if days_ago - low < high - days_ago else high + 1
            at = BASE - timedelta(days=days_ago)
            items.append(
                HistoryItem(at, "PAYEE_TRANSFER", payee.amount_rupees * 100, main, payee.ref)
            )

    window_start = BASE - timedelta(days=min(QUALIFYING_WINDOW_DAYS, history_days))
    in_window = [
        i.amount_paise for i in items if i.at >= window_start and i.amount_paise >= 100_000
    ]
    below = sum(a < median for a in in_window)
    above = sum(a > median for a in in_window)
    equal = sum(a == median for a in in_window)
    target_count = max(5, min(24, history_days // 7))
    x = max(0, (target_count - 1 + above - below) // 2)  # debits below the median
    y = x + below - above  # debits above, so that below == above around one exact median value
    if y < 0:
        x, y = above - below, 0
    amounts = [median] if equal == 0 else []
    low_floor = max(100_000 / median, 0.15)
    amounts += [round(median * rng.uniform(low_floor, 0.95)) for _ in range(x)]
    amounts += [round(median * rng.uniform(1.05, 4.0)) for _ in range(y)]
    span_days = (BASE - window_start).total_seconds() / 86400
    for amount in amounts:
        at = BASE - timedelta(days=rng.uniform(0.5, max(0.6, span_days - 0.5)))
        items.append(HistoryItem(at, "ROUTINE_DEBIT", amount, main))

    for month in range(1, max(1, history_days // 30) + 1):
        at = BASE - timedelta(days=30 * month - 1)
        if at > opened and not EXCLUDED_BAND_DAYS[0] <= 30 * month - 1 <= EXCLUDED_BAND_DAYS[1]:
            items.append(HistoryItem(at, "ROUTINE_CREDIT", median * 2, main))
    for _ in range(spec.premature_fd_closures):
        at = BASE - timedelta(days=rng.uniform(30, min(330, max(31, history_days - 1))))
        items.append(
            HistoryItem(
                at, "FD_CLOSED", median * 5, main, maturity=(at + timedelta(days=200)).date()
            )
        )
    return sorted(items, key=lambda i: i.at)


def background_spec(index: int, rng: random.Random) -> CustomerSpec:
    name = f"{rng.choice(INITIALS)}. {rng.choice(FIRST_NAMES)}"
    median = int(round(math.exp(rng.uniform(math.log(4_000), math.log(90_000))), -2))
    n = index
    accounts = [
        AccountSpec(
            masked=f"XXXXXX{n:02d}{11:02d}",
            type="SAVINGS",
            balance_rupees=median * rng.randint(3, 30),
        )
    ]
    if rng.random() < 0.4:
        accounts.append(
            AccountSpec(
                masked=f"XXXXXX{n:02d}{19:02d}",
                type="FD",
                balance_rupees=median * rng.randint(10, 60),
                maturity=DAY1 + timedelta(days=rng.randint(60, 700)),
            )
        )
    if rng.random() < 0.1:
        accounts.append(
            AccountSpec(masked=f"XXXXXX{n:02d}{13:02d}", type="CURRENT", balance_rupees=median * 20)
        )
    payees = [
        PayeeHistorySpec(
            ref=f"PAY-{n:04d}-{p + 1:02d}",
            name=fictional(rng.choice(PAYEE_NAMES)),
            age_days=rng.randint(30, 1500),
            transfers=rng.randint(0, 6),
            amount_rupees=int(median * rng.uniform(0.2, 1.5)),
            masked_account=f"XXXXXX8{n:02d}{p}",
        )
        for p in range(rng.randint(2, 12))
    ]
    contact = None
    if rng.random() < 0.7:
        contact = ContactSpec(
            name=rng.choice(FIRST_NAMES),
            relationship=rng.choice(["son", "daughter", "spouse", "sibling", "friend"]),
            language=rng.choice(["en", "ta"]),
            phone=f"+9198000{n:05d}",
        )
    return CustomerSpec(
        ref=f"CUST-{n:04d}",
        display_name=fictional(name),
        language=rng.choice(["en", "ta"]),
        median_outbound_rupees=median,
        history_days=rng.randint(20, 365),
        premature_fd_closures=1 if rng.random() < 0.05 else 0,
        accounts=accounts,
        payees=payees,
        trusted_contact=contact,
        consents=[c for c in ("CALL_SIGNAL", "TRUSTED_CONTACT_SHARING") if rng.random() < 0.6],
    )


def generate(
    seed: int, scenarios: dict[str, Scenario], *, n_customers: int = 50
) -> list[GeneratedCustomer]:
    rng = random.Random(seed)
    taken = {s.customer.ref for s in scenarios.values()}
    generated: list[GeneratedCustomer] = []
    for scenario in sorted(scenarios.values(), key=lambda s: s.customer.ref):
        params = scenario_params(scenario, seed)
        spec = scenario.customer.model_copy(
            update={
                "accounts": _scaled_accounts(scenario.customer, params.amount_scale),
                "history_days": params.history_days,
            }
        )
        crng = random.Random(f"{seed}:{spec.ref}")
        generated.append(GeneratedCustomer(spec, build_history(spec, crng, params.history_days)))
    index = 1
    while len(generated) < n_customers:
        ref = f"CUST-{index:04d}"
        if ref not in taken:
            spec = background_spec(index, rng)
            crng = random.Random(f"{seed}:{spec.ref}")
            generated.append(GeneratedCustomer(spec, build_history(spec, crng, spec.history_days)))
        index += 1
    return sorted(generated, key=lambda g: g.spec.ref)
